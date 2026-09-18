"""
Main RAG chain: LCEL pipelines + agentic router + memory integration.
"""

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.documents import Document

from backend.chain.prompts import (
    QA_PROMPT,
    SUMMARIZE_PROMPT,
    TIMESTAMP_PROMPT,
    HISTORY_REWRITE_PROMPT,
)
from backend.chain.memory import memory
from backend.retrieval.retriever import retrieve
from backend.retrieval.query_transform import classify_intent, rewrite_query
from backend.vectorstore.store import get_chunks_for_video
from backend.guardrails.guards import check_input, check_output_grounding

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


# ── Formatting helpers ─────────────────────────────────────────────────────

def format_docs_with_timestamps(docs: list[Document]) -> str:
    """Format retrieved docs as numbered sources with timestamps."""
    lines = []
    for i, doc in enumerate(docs, 1):
        t_start = doc.metadata.get("t_start_display", "?")
        t_end = doc.metadata.get("t_end_display", "?")
        lines.append(f"[{i}] [{t_start} - {t_end}] {doc.page_content}")
    return "\n\n".join(lines)


def _format_all_chunks(docs: list[Document]) -> str:
    """Format all chunks for summarization (no numbering needed)."""
    return "\n\n".join(doc.page_content for doc in docs)


# ── History-aware rewrite ──────────────────────────────────────────────────

_rewrite_chain = HISTORY_REWRITE_PROMPT | llm | StrOutputParser()


def _rewrite_with_history(question: str, session_id: str) -> str:
    """If there is chat history, rewrite the question to be standalone."""
    history = memory.get_history(session_id)
    if history == "(no previous conversation)":
        return question
    return _rewrite_chain.invoke({"history": history, "question": question})


# ── QA Chain ───────────────────────────────────────────────────────────────

def _run_qa(question: str, video_id: str, session_id: str) -> dict:
    """Full QA pipeline: rewrite -> retrieve -> augment -> generate -> guard."""
    # Rewrite with history
    standalone_q = _rewrite_with_history(question, session_id)

    # Retrieve
    docs = retrieve(standalone_q, video_id)
    context = format_docs_with_timestamps(docs)
    history = memory.get_history(session_id)

    # Generate via LCEL
    qa_chain = QA_PROMPT | llm | StrOutputParser()
    answer = qa_chain.invoke({
        "context": context,
        "question": standalone_q,
        "history": history,
    })

    # Output grounding check
    is_grounded = check_output_grounding(context, answer)
    if not is_grounded:
        answer += ("\n\n⚠️ *Note: This answer may contain information "
                   "not fully supported by the video transcript.*")

    return {
        "answer": answer,
        "sources": docs,
        "context": context,
        "is_grounded": is_grounded,
    }


# ── Summarize Chain ────────────────────────────────────────────────────────

def _run_summarize(video_id: str) -> dict:
    """Summarize the entire video using all chunks."""
    all_chunks = get_chunks_for_video(video_id)
    if not all_chunks:
        return {"answer": "No transcript found for this video.", "sources": [], "context": ""}

    # For long videos, summarize in segments then combine
    context = _format_all_chunks(all_chunks)
    summarize_chain = SUMMARIZE_PROMPT | llm | StrOutputParser()
    answer = summarize_chain.invoke({"context": context})

    return {"answer": answer, "sources": all_chunks, "context": context}


# ── Timestamp Seek Chain ───────────────────────────────────────────────────

def _run_timestamp(question: str, video_id: str) -> dict:
    """Find specific moments in the video."""
    docs = retrieve(question, video_id, use_compression=False, top_n=5)
    context = format_docs_with_timestamps(docs)

    timestamp_chain = TIMESTAMP_PROMPT | llm | StrOutputParser()
    answer = timestamp_chain.invoke({"context": context, "question": question})

    return {"answer": answer, "sources": docs, "context": context}


# ── Agentic Dispatch ───────────────────────────────────────────────────────

REFUSAL_MESSAGE = (
    "I can only answer questions about the YouTube video. "
    "Please ask something related to the video content."
)


def chat(question: str, video_id: str, session_id: str = "default") -> dict:
    """
    Main entry point. Routes the user's question through:
      1. Input guard (LLM-based safety check)
      2. Intent classification (LLM-based router)
      3. Appropriate chain (qa / summarize / timestamp / refuse)
      4. Memory update
    Returns dict with: answer, sources, context, intent, is_grounded.
    """
    # Input guard
    if not check_input(question):
        return {
            "answer": REFUSAL_MESSAGE,
            "sources": [],
            "context": "",
            "intent": "refuse",
            "is_grounded": True,
        }

    # Route
    intent = classify_intent(question)

    if intent == "refuse":
        result = {"answer": REFUSAL_MESSAGE, "sources": [], "context": ""}
    elif intent == "summarize":
        result = _run_summarize(video_id)
    elif intent == "timestamp":
        result = _run_timestamp(question, video_id)
    else:  # qa
        result = _run_qa(question, video_id, session_id)

    # Update memory
    memory.add_turn(session_id, question, result["answer"])

    return {
        **result,
        "intent": intent,
        "is_grounded": result.get("is_grounded", True),
    }
