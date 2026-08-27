import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chains import answer_mode, get_ask_chain, ingest_chain
from app.config import settings
from app.models import Document
from app.store import docs_to_hits


def _hash_bytes(data: bytes) -> str:
    payload = data + f"|{settings.ingest_version}".encode()
    return hashlib.sha256(payload).hexdigest()


def ingest_pdf(db: Session, filename: str, data: bytes) -> dict:
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")
    if len(data) > settings.max_file_size_bytes:
        raise ValueError(f"PDF size should be less than {settings.max_file_size_mb} MB.")

    save_path = settings.pdf_dir / Path(filename).name
    save_path.write_bytes(data)
    digest = _hash_bytes(data)

    existing = db.scalar(select(Document).where(Document.source == save_path.name))
    if existing and existing.file_hash == digest:
        return {
            "source": existing.source,
            "document_id": str(existing.id),
            "pages": 0,
            "chunks": _count_source(save_path.name),
            "skipped": True,
        }

    documents = ingest_chain.invoke(str(save_path))
    pages = len({doc.metadata.get("page") for doc in documents})

    if existing:
        existing.file_hash = digest
    else:
        existing = Document(source=save_path.name, file_hash=digest)
        db.add(existing)
    db.commit()
    db.refresh(existing)

    return {
        "source": existing.source,
        "document_id": str(existing.id),
        "pages": pages,
        "chunks": len(documents),
        "skipped": False,
    }


def ask(
    question: str,
    rerank: bool = True,
    doc_type: str | None = None,
) -> dict:
    result = get_ask_chain().invoke(
        {"question": question, "rerank": rerank, "doc_type": doc_type}
    )
    used = docs_to_hits(result.get("used") or [])
    retrieved = docs_to_hits(result.get("retrieved") or [])
    citations = [
        {
            "source": item.get("source"),
            "page": item.get("page"),
            "section": item.get("section"),
            "doc_type": item.get("doc_type"),
            "score": item.get("rerank_score", item.get("similarity")),
        }
        for item in used
    ]
    return {
        "answer": result.get("answer") or "",
        "mode": answer_mode(result),
        "rerank": rerank,
        "context": result.get("context") or "",
        "citations": citations,
        "retrieved": retrieved,
        "used": used,
    }


def _count_source(source: str) -> int:
    from sqlalchemy import text

    from app.db import engine

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
