from typing import Union

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

api = FastAPI(openapi_prefix="/api")
app.mount("/api", api)

app.mount("/", StaticFiles(directory="static", html = True), name="static")

@api.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}