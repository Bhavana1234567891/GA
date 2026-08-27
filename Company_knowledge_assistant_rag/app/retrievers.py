"""LangChain retrievers: expanded similarity search + cross-encoder compression."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from app.config import settings
from app.query import expand_query
from app.store import get_reranker, get_vectorstore

try:
    from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
except ImportError:  # pragma: no cover
    from langchain_classic.retrievers.contextual_compression import (
        ContextualCompressionRetriever,
    )


class ExpandedQueryRetriever(BaseRetriever):
    """Vector-store retriever with HR query expansion (still a LangChain retriever)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    k: int = Field(default_factory=lambda: settings.retrieve_k)
    keyword_k: int = 4
    doc_type: str | None = None

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        store = get_vectorstore()
        search_query, keywords = expand_query(query)
        docs = self._search(store, search_query, self.k)
        seen = {self._key(doc) for doc in docs}
        keyword_retriever = store.as_retriever(search_kwargs={"k": self.keyword_k})
        for term in keywords[:4]:
            for extra in keyword_retriever.invoke(term):
                key = self._key(extra)
                if key not in seen:
                    docs.append(extra)
                    seen.add(key)
        if self.doc_type:
            docs = [doc for doc in docs if doc.metadata.get("doc_type") == self.doc_type]
        return docs

    def _search(self, store: Any, query: str, k: int) -> list[Document]:
        retriever = store.as_retriever(search_kwargs={"k": k})
        try:
            pairs = store.similarity_search_with_score(query, k=k)
        except Exception:
            return retriever.invoke(query)
        docs: list[Document] = []
        for doc, score in pairs:
            doc.metadata = dict(doc.metadata or {})
            doc.metadata["similarity"] = float(score)
            docs.append(doc)
        return docs

    @staticmethod
    def _key(doc: Document) -> tuple:
        return (
            doc.metadata.get("source"),
            doc.metadata.get("chunk_index"),
            doc.page_content[:80],
        )


def get_base_retriever(doc_type: str | None = None) -> ExpandedQueryRetriever:
    return ExpandedQueryRetriever(doc_type=doc_type)


def get_rerank_retriever(doc_type: str | None = None) -> ContextualCompressionRetriever:
    return ContextualCompressionRetriever(
        base_retriever=get_base_retriever(doc_type),
        base_compressor=get_reranker(),
    )
