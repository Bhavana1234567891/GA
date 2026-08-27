"""LCEL chains: load | split | store  and  retrieve | prompt | llm."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough

from app.chunking import PolicySectionSplitter, finalize_chunks, get_recursive_splitter
from app.config import settings
from app.context import build_context
from app.generate import EMPTY_ANSWER, SYSTEM_PROMPT, extractive_answer
from app.loading import load_pdf_documents
from app.query import expand_query
from app.retrievers import get_base_retriever
from app.store import (
    attach_rerank_scores,
    delete_source_vectors,
    docs_to_hits,
    get_llm,
    get_reranker,
    get_vectorstore,
)


def _section_split(documents: list[Document]) -> list[Document]:
    return PolicySectionSplitter().split_documents(documents)


def _recursive_split(documents: list[Document]) -> list[Document]:
    return get_recursive_splitter().split_documents(documents)


def _store_documents(documents: list[Document]) -> list[Document]:
    if not documents:
        raise ValueError("No chunks produced from PDF.")
    source = str(documents[0].metadata.get("source") or "")
    delete_source_vectors(source)
    ids = [f"{source}:{doc.metadata['chunk_index']}" for doc in documents]
    get_vectorstore().add_documents(documents, ids=ids)
    return documents


load = RunnableLambda(load_pdf_documents).with_config(run_name="load")
section_split = RunnableLambda(_section_split).with_config(run_name="section_split")
chunk = RunnableLambda(_recursive_split).with_config(run_name="chunk")
annotate = RunnableLambda(finalize_chunks).with_config(run_name="annotate")
store = RunnableLambda(_store_documents).with_config(run_name="store")

ingest_chain: Runnable = load | section_split | chunk | annotate | store

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT + "\n\nContext:\n{context}"),
        ("human", "{question}"),
    ]
)


def _retrieve_and_rerank(payload: dict) -> dict:
    question = payload["question"]
    rerank = payload.get("rerank", True)
    doc_type = payload.get("doc_type")
    base = get_base_retriever(doc_type)
    retrieved = base.invoke(question)
    search_query, _ = expand_query(question)
    if retrieved and rerank:
        rerank_step = RunnableLambda(
            lambda docs: get_reranker().compress_documents(docs, search_query)
        ).with_config(run_name="rerank")
        used = rerank_step.invoke(retrieved)
        attach_rerank_scores(used, search_query)
    else:
        used = retrieved[:3]
    context = build_context(docs_to_hits(used)) if used else ""
    return {
        "question": question,
        "rerank": rerank,
        "retrieved": retrieved,
        "used": used,
        "context": context,
    }


def _empty_or_extractive(payload: dict) -> str:
    context = payload.get("context") or ""
    if not context.strip():
        return EMPTY_ANSWER
    return extractive_answer(context)


def _answer_chain() -> Runnable:
    llm = get_llm()
    if llm is None:
        return RunnableLambda(_empty_or_extractive).with_config(run_name="extractive")
    generate = (prompt | llm | StrOutputParser()).with_config(run_name="prompt|llm")

    def generate_or_empty(payload: dict) -> str:
        if not (payload.get("context") or "").strip():
            return EMPTY_ANSWER
        return generate.invoke(
            {"question": payload["question"], "context": payload["context"]}
        )

    return RunnableLambda(generate_or_empty)


retrieve = RunnableLambda(_retrieve_and_rerank).with_config(run_name="retrieve|rerank")


def get_ask_chain() -> Runnable:
    return retrieve | RunnablePassthrough.assign(answer=_answer_chain())


def answer_mode(payload: dict) -> str:
    if not (payload.get("context") or "").strip():
        return "empty"
    return "llm" if settings.llm_enabled else "extractive"
