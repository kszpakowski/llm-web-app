from sqlalchemy.orm import Session

from . import models, schemas


def get_document(db: Session, document_id: int):
    return db.query(models.Document).filter(models.Document.id == document_id).first()


def get_document_by_body_id(db: Session, document_body_id: int):
    return (
        db.query(models.Document)
        .filter(models.Document.body_id == document_body_id)
        .first()
    )


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
        status="Initial",
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


def update_document(db: Session, document: schemas.DocumentUpdate):
    doc = db.query(models.Document).filter(models.Document.id == document.id).first()
    if document.path:
        doc.path = document.path

    if document.status:
        doc.status = document.status

    db.commit()
    db.refresh(doc)
    return doc


def get_questions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Question).offset(skip).limit(limit).all()


def get_question(db: Session, id: int):
    return db.query(models.Question).filter(models.Question.id == id).first()


def get_question_by_doc_id_and_question(db: Session, doc_id: int, question: str):
    return (
        db.query(models.Question)
        .filter(models.Question.doc_id == doc_id, models.Question.question == question)
        .first()
    )


def create_question(db: Session, question: schemas.QuestionCreate):
    db_question = models.Question(
        doc_id=question.doc_id, question=question.question, status="Initial"
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


def update_question(db: Session, update: schemas.QuestionUpdate):
    question = db.query(models.Question).filter(models.Question.id == update.id).first()
    if update.status:
        question.status = update.status
    if update.answer:
        question.answer = update.answer

    db.commit()
    db.refresh(question)
    return question
