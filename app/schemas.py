from typing import Union
from pydantic import BaseModel


class QuestionBase(BaseModel):
    pass


class QuestionCreate(QuestionBase):
    question: str
    doc_id: int


class QuestionUpdate(QuestionBase):
    id: int
    answer: Union[str, None] = None
    status: Union[str, None] = None


class Question(QuestionBase):
    id: int
    question: str
    doc_id: int
    answer: Union[str, None] = None
    status: str

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    path: Union[str, None] = None
    status: str


class DocumentCreate(DocumentBase):
    body_id: int
    doc_name: str
    prod_code: str
    doc_title: str
    type_name: str


class DocumentUpdate(DocumentBase):
    id: int


class Document(DocumentBase):
    id: int
    body_id: int
    doc_name: str
    prod_code: str
    doc_title: str
    type_name: str
    questions: list[Question] = []

    class Config:
        from_attributes = True
