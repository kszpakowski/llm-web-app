from typing import Union
from pydantic import BaseModel


class DocumentBase(BaseModel):
    body_id: int
    doc_name: str
    prod_code: str
    doc_title: str
    type_name: str
    path: Union[str, None] = None
    status: str
    


class DocumentCreate(DocumentBase):
    body_id: int
    doc_name: str
    prod_code: str
    doc_title: str
    type_name: str

class Document(DocumentBase):
    id: int

    class Config:
        from_attributes = True


# class UserBase(BaseModel):
#     email: str


# class UserCreate(UserBase):
#     password: str


# class User(UserBase):
#     id: int
#     is_active: bool
#     items: list[Item] = []

#     class Config:
#         orm_mode = True