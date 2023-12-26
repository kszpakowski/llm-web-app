# from pathlib import Path
# from llama_index.readers.file.docs_reader import PDFReader
# from llama_index import VectorStoreIndex, StorageContext, load_index_from_storage


import os
from fastapi import Depends, FastAPI, HTTPException, Request, Response
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


# @timed
# @api.get("/ask")
# def ask(doc_id, prompt):
#     # doc = GtcDocument(doc_id)
#     return ask_doc(doc_id, prompt)


# @timed
# def download_doc(doc_id):
#     db = Database()
#     doc = db.get_doc(doc_id)

#     if not doc["path"]:
#         print(f'Document content not present, downloading {doc["title"]}')
#         body_id = doc["id"]
#         path = Path(f"/documents/{body_id}")
#         path.mkdir(parents=True, exist_ok=True)

#         doc_body = gtc.get_doc_body(body_id)
#         file_name = doc_body.fileName
#         file_path = f"{path}/{file_name}"

#         with open(file_path, "wb") as f:
#             f.write(doc_body["document"])

#         db.update_doc_path(body_id, file_path)
#         print(f'Doc {doc["id"]} content downloaded')
#         return db.get_doc(doc_id)
#     else:
#         print(f"Document {doc['id']} has been already downloaded")
#         return doc


# @timed
# def get_query_engine(doc):
#     vsp = Path(doc["path"]).parent / "vs"
#     if vsp.exists():
#         print("Using existing Vector store")
#         # load the existing index
#         storage_context = StorageContext.from_defaults(persist_dir=vsp)
#         index = load_index_from_storage(storage_context)
#     else:
#         print("Creating and persisting vector store")
#         reader = PDFReader()
#         docs = reader.load_data(doc["path"], extra_info=doc)
#         index = VectorStoreIndex.from_documents(docs)
#         index.storage_context.persist(persist_dir=vsp)

#     return index.as_query_engine()


# @timed
# def ask_doc(doc_id, prompt):
#     doc = download_doc(doc_id)
#     query_engine = get_query_engine(doc)
#     response = query_engine.query(prompt)
#     return response
