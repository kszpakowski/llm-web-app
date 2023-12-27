import uvicorn
from llama_index.readers.file.docs_reader import PDFReader

import os
from pathlib import Path
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from llama_index import StorageContext, VectorStoreIndex, load_index_from_storage

from sqlalchemy.orm import Session
from app.log_config import log_config


from app.gtc_client import GtcClient
from app.timed import timed

from . import crud, models, schemas
from .database import SessionLocal, engine

import logging
from logging.config import dictConfig

logger = logging.getLogger(__name__)

dictConfig(log_config)

models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()

API_KEY = os.environ["API_KEY"]


@app.middleware("http")
async def check_api_key(request: Request, call_next):
    req_api_key = request.headers.get("x-api-key", None)
    if not req_api_key == API_KEY:
        return Response(status_code=401)
    return await call_next(request)


@timed
@app.get("/documents", response_model=list[schemas.Document])
def read_documents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_documents(db, skip=skip, limit=limit)


@timed
@app.get("/documents/{id}", response_model=schemas.Document)
def read_documents(id: int, db: Session = Depends(get_db)):
    return crud.get_document(db, document_id=id)


@timed
@app.post("/documents/refresh")
def load_docs(db: Session = Depends(get_db)):
    logger.info("Getting gtc documents")
    gtc = GtcClient()
    logger.info("Getting gtc documents done")
    docs = gtc.get_all_documents_metadata()
    for doc in docs:
        doc_body_id = str(doc.idBodyDoc)

        db_doc = crud.get_document_by_body_id(db, document_body_id=doc_body_id)
        if db_doc:
            logger.info(f"Document {doc_body_id} already present in db")
        else:
            logger.info(f"Saving doc {doc_body_id}")
            doc_create = schemas.DocumentCreate(
                body_id=str(doc.idBodyDoc),
                doc_name=doc.docName,
                prod_code=doc.prodCode.strip(),
                doc_title=doc.docTitle.strip(),
                type_name=doc.typeName.strip(),
                status="Initial",
            )
            crud.create_document(db, doc_create)


@timed
@app.post("/documents/{id}/ask", response_model=schemas.Question)
def ask(
    id: int, prompt, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    question = crud.get_question_by_doc_id_and_question(db, doc_id=id, question=prompt)
    if question:
        logger.info(f"Question already exists. Id: {question.id}")
        return question
    else:
        logger.info(f"Creating new question")
        question = crud.create_question(
            db, schemas.QuestionCreate(doc_id=id, question=prompt)
        )
        background_tasks.add_task(handle_question, db, question, prompt)
        return question


@timed
@app.get("/questions", response_model=list[schemas.Question])
def read_questions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_questions(db, skip=skip, limit=limit)


@timed
def handle_question(db, question, prompt):
    try:
        logger.info(f"Generating answer for question {question.id}")
        crud.update_question(
            db, schemas.QuestionUpdate(id=question.id, status="Generating")
        )

        doc = crud.get_document(db, question.doc_id)
        logger.info(f"Document: {doc}")
        if doc.status == "Initial":
            logger.info(f"Downloading content of document {doc.id}")
            crud.update_document(
                db, schemas.DocumentUpdate(id=doc.id, status="Downloading")
            )
            (_, file_path) = download_doc(doc.body_id)
            crud.update_document(
                db,
                schemas.DocumentUpdate(
                    id=doc.id, status="Downloaded", path=file_path
                ),
            )

        if not doc.status == "Indexed":
            logger.info(f"Indexing document {doc.id}")
            crud.update_document(
                db, schemas.DocumentUpdate(id=doc.id, status="Indexing")
            )
            index_document(doc.path)
            crud.update_document(
                db, schemas.DocumentUpdate(id=doc.id, status="Indexed")
            )

        logger.info(f"Getting query engine for doc {doc.id}")
        query_engine = get_query_engine(doc.path)

        logger.info(f"Querying engine for doc {doc.id}")
        query = query_engine.query(prompt)

        logger.info(f"Question {question.id} answered")
        crud.update_question(
            db,
            schemas.QuestionUpdate(
                id=question.id, status="Answered", answer=query.response
            ),  # TODO save response and metadata
        )
    except Exception as e:
        logger.error(f"Error in processing question {e}")
        crud.update_question(db, schemas.QuestionUpdate(id=question.id, status="Error"))

@timed
def download_doc(doc_body_id):
    logger.info(f"Downloading {doc_body_id} document body")
    path = Path(f"/documents/{doc_body_id}")
    path.mkdir(parents=True, exist_ok=True)

    doc_body = GtcClient().get_doc_body(doc_body_id)
    file_name = doc_body.fileName
    file_path = f"{path}/{file_name}"

    with open(file_path, "wb") as f:
        f.write(doc_body["document"])

    return (file_name, file_path)


@timed
def index_document(path):
    logger.info(f"Indexing {path}")
    vsp = Path(path).parent / "vs"
    logger.info(f"Creating and persisting vector store at {vsp}")
    reader = PDFReader()
    logger.info("Created reader")
    docs = reader.load_data(path, extra_info={})  # TODO add extra info
    logger.info("Loaded data")
    index = VectorStoreIndex.from_documents(docs)
    logger.info("Created index")
    index.storage_context.persist(persist_dir=vsp)
    logger.info("Persisted index")


@timed
def get_query_engine(path):
    vsp = Path(path).parent / "vs"
    logger.info(f"Loading persisted query engine from {vsp}")

    storage_context = StorageContext.from_defaults(persist_dir=vsp)
    index = load_index_from_storage(storage_context)
    logger.info(f"Loaded persisted query engine from {vsp}")
    return index.as_query_engine()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
