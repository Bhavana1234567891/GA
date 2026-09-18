"""
FastAPI backend for the YouTube RAG Chatbot.

Endpoints:
    POST /index   – ingest a video transcript into ChromaDB
    POST /chat    – ask a question about an indexed video
    GET  /health  – liveness check
"""

import os, sys
from pathlib import Path

# Ensure the project root is on sys.path so `backend.*` imports work
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(Path(PROJECT_ROOT) / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.indexing.ingest import ingest_video
from backend.vectorstore.store import index_documents, is_video_indexed
from backend.chain.rag_chain import chat

app = FastAPI(title="YouTube RAG Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extension will call from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────

class IndexRequest(BaseModel):
    video_id: str
    title: str = ""
    languages: list[str] = ["en"]

class IndexResponse(BaseModel):
    video_id: str
    chunks_count: int
    message: str

class ChatRequest(BaseModel):
    video_id: str
    question: str
    session_id: str = "default"

class SourceInfo(BaseModel):
    text: str
    t_start: float
    t_end: float
    t_start_display: str
    t_end_display: str

class ChatResponse(BaseModel):
    answer: str
    intent: str
    is_grounded: bool
    sources: list[SourceInfo]


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/index", response_model=IndexResponse)
def index_video(req: IndexRequest):
    """Fetch transcript, chunk by 30s, embed, store in ChromaDB."""
    if is_video_indexed(req.video_id):
        return IndexResponse(
            video_id=req.video_id,
            chunks_count=0,
            message="Video already indexed.",
        )

    try:
        chunks = ingest_video(
            video_id=req.video_id,
            title=req.title,
            languages=req.languages,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    index_documents(chunks)

    return IndexResponse(
        video_id=req.video_id,
        chunks_count=len(chunks),
        message=f"Indexed {len(chunks)} chunks successfully.",
    )


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Ask a question about an indexed video."""
    if not is_video_indexed(req.video_id):
        raise HTTPException(
            status_code=400,
            detail=f"Video {req.video_id} is not indexed. Call /index first.",
        )

    result = chat(req.question, req.video_id, req.session_id)

    sources = []
    for doc in result.get("sources", []):
        sources.append(SourceInfo(
            text=doc.page_content[:500],
            t_start=doc.metadata.get("t_start", 0),
            t_end=doc.metadata.get("t_end", 0),
            t_start_display=doc.metadata.get("t_start_display", "?"),
            t_end_display=doc.metadata.get("t_end_display", "?"),
        ))

    return ChatResponse(
        answer=result["answer"],
        intent=result.get("intent", "qa"),
        is_grounded=result.get("is_grounded", True),
        sources=sources,
    )
