"""LangChain embeddings, PGVector store, cross-encoder rerank, and LLM."""

from functools import lru_cache

from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.documents import Document as LCDocument
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_postgres import PGVector

from app.config import settings

try:
    from langchain.retrievers.document_compressors import CrossEncoderReranker
except ImportError:  # pragma: no cover
    from langchain_classic.retrievers.document_compressors import CrossEncoderReranker


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def get_vectorstore() -> PGVector:
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=settings.collection_name,
        connection=settings.database_url,
        use_jsonb=True,
    )


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoderReranker:
    model = HuggingFaceCrossEncoder(model_name=settings.rerank_model)
    return CrossEncoderReranker(model=model, top_n=settings.rerank_top_n)


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI | None:
    if not settings.llm_enabled:
        return None
    kwargs: dict = {
        "model": settings.llm_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.1,
    }
    if settings.llm_base_url.strip():
        kwargs["base_url"] = settings.llm_base_url.strip()
    return ChatOpenAI(**kwargs)


def delete_source_vectors(source: str) -> None:
    store = get_vectorstore()
    try:
        store.delete(filter={"source": source})
        return
    except TypeError:
        pass
    except Exception:
        pass

    from sqlalchemy import text

    from app.db import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM langchain_pg_embedding AS e
                USING langchain_pg_collection AS c
                WHERE e.collection_id = c.uuid
                  AND c.name = :collection
                  AND e.cmetadata->>'source' = :source
                """
            ),
            {"collection": settings.collection_name, "source": source},
        )


def attach_rerank_scores(docs: list[LCDocument], query: str) -> None:
    if not docs:
        return
    pairs = [[query, doc.page_content] for doc in docs]
    scores = get_reranker().model.score(pairs)
    for doc, score in zip(docs, scores):
        doc.metadata = dict(doc.metadata or {})
        doc.metadata["relevance_score"] = float(score)


def docs_to_hits(docs: list[LCDocument]) -> list[dict]:
    hits = []
    for doc in docs:
        meta = doc.metadata or {}
        text = doc.page_content
        rerank_score = meta.get("relevance_score", meta.get("rerank_score"))
        similarity = meta.get("similarity")
        hits.append(
            {
                "content": text,
                "source": meta.get("source"),
                "page": meta.get("page"),
                "section": meta.get("section"),
                "doc_type": meta.get("doc_type"),
                "chunk_index": meta.get("chunk_index"),
                "similarity": None if similarity is None else float(similarity),
                "rerank_score": None if rerank_score is None else float(rerank_score),
                "text": text if len(text) <= 240 else text[:240] + "…",
            }
        )
    return hits
