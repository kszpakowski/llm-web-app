from typing import Union
import os
import zeep
from pathlib import Path

from fastapi import FastAPI, Request, Response

from llama_index.readers.file.docs_reader import PDFReader
from llama_index import VectorStoreIndex, StorageContext, load_index_from_storage


import sqlite3


class GtcClient:
    def __init__(self):
        wsdl = "https://gtc.nn.pl/gtc/services/GtcServiceHttpPort?wsdl"
        self.client = zeep.Client(wsdl=wsdl)

    def get_all_documents_metadata(self):
        return self.client.service.getAllGtcDocuments().body["return"]

    def get_doc_body(self, doc_id):
        return self.client.service.getGtcDocumentBody(doc_id).body["return"]


class Database:
    def __init__(self):
        con = sqlite3.connect("/db/main.db")
        self.con = con
        try:
            cur = con.cursor()
            cur.execute(
                "CREATE TABLE document_metadata(body_id, doc_name, prod_code, doc_title, type_name, path)"
            )
        except sqlite3.OperationalError:
            print("Unable to create table")

    def list_docs(self):
        cur = self.con.cursor()
        data = cur.execute(f"SELECT * FROM document_metadata").fetchall()
        return [self._map_row(row) for row in data]

    def get_doc(self, id):
        cur = self.con.cursor()
        row = cur.execute(
            f"SELECT * FROM document_metadata WHERE body_id = '{id}'"
        ).fetchone()
        return self._map_row(row)

    def _map_row(self, row):
        return {
            "id": row[0],
            "name": row[1],
            "prodCode": row[2],
            "title": row[3],
            "type": row[4],
            "path": row[5],
        }

    def save_doc(self, doc):
        cur = self.con.cursor()
        cur.execute(
            f"INSERT INTO document_metadata VALUES ('{str(doc.idBodyDoc)}','{doc.docName}','{doc.prodCode.strip()}','{doc.docTitle.strip()}','{doc.typeName.strip()}','')"
        )
        self.con.commit()

    def update_doc_path(self, doc_id, path):
        cur = self.con.cursor()
        cur.execute(
            f"UPDATE document_metadata SET path = '{path}' WHERE body_id = '{doc_id}'"
        )
        self.con.commit()


db = Database()
gtc = GtcClient()

app = FastAPI()

api = FastAPI(openapi_prefix="/api")
app.mount("/api", api)

API_KEY = os.environ["API_KEY"]


@app.middleware("http")
async def check_api_key(request: Request, call_next):
    req_api_key = request.headers.get("x-api-key", None)
    if not req_api_key == API_KEY:
        return Response(status_code=401)
    return await call_next(request)


@api.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@api.get("/load_docs")
async def load_docs():
    docs = gtc.get_all_documents_metadata()
    for doc in docs:
        db.save_doc(doc)


@api.get("/list_docs")
async def list_docs():
    return db.list_docs()


@api.get("/prompt")
async def handle_prompt(prompt):
    print(prompt)


@api.get("/ask")
async def ask(doc_id, prompt):
    return ask_doc(doc_id, prompt)

def download_doc(doc_id):
    doc = db.get_doc(doc_id)

    if not doc["path"]:
        print(f'Document content not present, downloading {doc["title"]}')
        body_id = doc["id"]
        path = Path(f"/documents/{body_id}")
        path.mkdir(parents=True, exist_ok=True)

        doc_body = gtc.get_doc_body(body_id)
        file_name = doc_body.fileName
        file_path = f"{path}/{file_name}"

        with open(file_path, "wb") as f:
            f.write(doc_body["document"])

        db.update_doc_path(body_id, file_path)
        print(f'Doc {doc["id"]} content downloaded')
        return db.get_doc(doc_id)
    else:
        print(f"Document {doc['id']} has been already downloaded")
        return doc

def get_query_engine(doc):
    vsp = Path(doc["path"]).parent / "vs"
    if vsp.exists():
        print("Using existing Vector store")
        # load the existing index
        storage_context = StorageContext.from_defaults(persist_dir=vsp)
        index = load_index_from_storage(storage_context)
    else:
        print("Creating and persisting vector store")
        reader = PDFReader()
        docs = reader.load_data(doc["path"], extra_info=doc)
        index = VectorStoreIndex.from_documents(docs)
        index.storage_context.persist(persist_dir=vsp)

    return index.as_query_engine()

def ask_doc(doc_id, prompt):
    doc = download_doc(doc_id)
    query_engine = get_query_engine(doc)
    response = query_engine.query(prompt)
    return response

