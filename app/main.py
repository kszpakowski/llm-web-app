from llama_index.readers.file.docs_reader import PDFReader

import os
from pathlib import Path
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from llama_index import StorageContext, VectorStoreIndex, load_index_from_storage

from sqlalchemy.orm import Session

from app.gtc_client import GtcClient
from app.timed import timed

from . import crud, models, schemas
from .database import SessionLocal, engine

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


# https://fastapi.tiangolo.com/tutorial/background-tasks/
@timed
@app.post("/documents/refresh")
def load_docs(db: Session = Depends(get_db)):
    print("Getting gtc documents")
    gtc = GtcClient()
    print("Getting gtc documents done")
    docs = gtc.get_all_documents_metadata()
    for doc in docs:
        doc_body_id = str(doc.idBodyDoc)

        db_doc = crud.get_document_by_body_id(db, document_body_id=doc_body_id)
        if db_doc:
            print(f"Document {doc_body_id} already present in db")
        else:
            print(f"Saving doc {doc_body_id}")
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
@app.post("/documents/{id}/ask")
def ask(
    id: int, prompt, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    background_tasks.add_task(handle_question, db, id, prompt)
    return Response(status_code=202)


def handle_question(db, doc_id, prompt):
    print(f'generating answer for {doc_id}, question "{prompt}"')
    doc = crud.get_document_by_body_id(db, doc_id)
    if doc.status == "Initial":
        crud.update_document(
            db, schemas.DocumentUpdate(id=doc.id, status="Downloading")
        )
        (_, file_path) = download_doc(doc.body_id)
        crud.update_document(
            db, schemas.DocumentUpdate(id=doc.id, status="Downloaded", path=file_path)
        )

    if not doc.status == "Indexed":
        crud.update_document(db, schemas.DocumentUpdate(id=doc.id, status="Indexing"))
        index_document(doc.path)
        crud.update_document(db, schemas.DocumentUpdate(id=doc.id, status="Indexed"))

    get_query_engine()


@timed
def download_doc(doc_body_id):
    print(f"Downloading {doc_body_id} document body")
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
    print(f"Indexing {path}")
    vsp = Path(path).parent / "vs"
    print(f"Creating and persisting vector store at {vsp}")
    reader = PDFReader()
    print("Created reader")
    docs = reader.load_data(path, extra_info={})  # TODO add extra info
    print("Loaded data")
    index = VectorStoreIndex.from_documents(docs)
    print("Created index")
    index.storage_context.persist(persist_dir=vsp)
    print("persisted index")


@timed
def get_query_engine(path):
    print("Getting query engine")
    vsp = Path(path).parent / "vs"
    storage_context = StorageContext.from_defaults(persist_dir=vsp)
    index = load_index_from_storage(storage_context)


# @timed
# def ask_doc(doc_id, prompt):
#     doc = download_doc(doc_id)
#     query_engine = get_query_engine(doc)
#     response = query_engine.query(prompt)
#     return response
