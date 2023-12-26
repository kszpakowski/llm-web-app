from sqlalchemy.orm import Session

from . import models, schemas


def get_document(db: Session, document_id: int):
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def get_document_by_body_id(db: Session, document_body_id: int):
    return db.query(models.Document).filter(models.Document.body_id == document_body_id).first()


def get_document_by_path(db: Session, path: str):
    return db.query(models.Document).filter(models.Document.path == path).first()


def get_documents(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Document).offset(skip).limit(limit).all()


def create_document(db: Session, document: schemas.DocumentCreate):
    db_document = models.Document(
        body_id=document.body_id,
        doc_name=document.doc_name,
        prod_code=document.prod_code,
        doc_title=document.doc_title,
        type_name=document.type_name,
        status = 'Initial'
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


# def get_items(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.Item).offset(skip).limit(limit).all()


# def create_user_item(db: Session, item: schemas.ItemCreate, user_id: int):
#     db_item = models.Item(**item.dict(), owner_id=user_id)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#     return db_item
