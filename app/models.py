# https://fastapi.tiangolo.com/tutorial/sql-databases/#create-model-attributescolumns

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    body_id = Column(Integer, unique=True, index=True)
    doc_name = Column(String, index=True)
    prod_code = Column(String, index=True)
    doc_title = Column(String, index=True)
    type_name = Column(String, index=True)
    type_name = Column(String, index=True)
    path = Column(String, unique=True, index=True)
    status =  Column(String, index=True)
