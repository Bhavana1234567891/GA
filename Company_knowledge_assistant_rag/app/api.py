from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import engine, get_db
from app.models import Document
from app.pipeline import ask, ingest_pdf
from app.schemas import AskRequest, RetrieveRequest

router = APIRouter(prefix="/api")
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta")
def meta(db: DbSession) -> dict[str, Any]:
    documents = db.scalar(select(func.count()).select_from(Document)) or 0
    names = db.scalars(select(Document.source).order_by(Document.source)).all()
    return {
        "documents": documents,
        "chunks": _embedding_count(),
        "sources": names,
        "embedding_model": settings.embedding_model,
        "rerank_model": settings.rerank_model,
        "answer_mode": "llm" if settings.llm_enabled else "extractive",
        "retrieve_k": settings.retrieve_k,
        "rerank_top_n": settings.rerank_top_n,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "stack": "langchain",
        "ingest_chain": "load | section_split | chunk | store",
        "ask_chain": "retrieve | rerank | prompt | llm",
    }


@router.get("/documents")
def list_documents(db: DbSession) -> list[dict[str, Any]]:
    rows = db.scalars(select(Document).order_by(Document.source)).all()
    return [
        {
            "id": str(row.id),
            "source": row.source,
            "chunks": _count_source(row.source),
        }
        for row in rows
    ]


@router.post("/ingest")
def ingest(db: DbSession, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    filename = file.filename or "upload.pdf"
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        return ingest_pdf(db, filename, data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/retrieve")
def retrieve(payload: RetrieveRequest) -> dict[str, Any]:
    try:
        result = ask(
            payload.question.strip(),
            rerank=payload.rerank,
            doc_type=payload.doc_type,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "retrieved": result["retrieved"],
        "used": result["used"],
        "rerank": result["rerank"],
    }


@router.post("/ask")
def ask_question(payload: AskRequest) -> dict[str, Any]:
    try:
        return ask(
            payload.question.strip(),
            rerank=payload.rerank,
            doc_type=payload.doc_type,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _embedding_count() -> int:
    try:
        with engine.connect() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding")).scalar() or 0)
    except Exception:
        return 0


def _count_source(source: str) -> int:
    try:
        with engine.connect() as conn:
            return int(
                conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM langchain_pg_embedding AS e
                        JOIN langchain_pg_collection AS c ON e.collection_id = c.uuid
                        WHERE c.name = :collection
                          AND e.cmetadata->>'source' = :source
                        """
                    ),
                    {"collection": settings.collection_name, "source": source},
                ).scalar()
                or 0
            )
    except Exception:
        return 0
