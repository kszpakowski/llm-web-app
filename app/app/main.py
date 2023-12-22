from typing import Union

from fastapi import FastAPI

app = FastAPI()

api = FastAPI(openapi_prefix="/api")
app.mount("/api", api)

@api.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}