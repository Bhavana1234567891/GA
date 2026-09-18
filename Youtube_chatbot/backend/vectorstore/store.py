"""
Vector Store: ChromaDB (persistent) + BM25 (in-memory) for hybrid retrieval.
Uses free local HuggingFace embeddings (no OpenAI embedding API needed).
"""

import os
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
import numpy as np

CHROMA_DIR = str(Path(__file__).resolve().parent.parent.parent / "chroma_db")
COLLECTION_NAME = "yt_transcripts"

# Lazy-loaded to avoid slow import at startup
_embeddings = None

def get_embeddings() -> HuggingFaceEmbeddings:
    """Free local embeddings via sentence-transformers. ~80MB download on first use."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )
    return _embeddings


def get_vectorstore() -> Chroma:
    """Return a handle to the persistent ChromaDB collection."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )


def index_documents(chunks: list[Document]) -> Chroma:
    """Embed and upsert chunks into ChromaDB. Returns the vectorstore handle."""
    embeddings = get_embeddings()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
    )
    return vectorstore


def is_video_indexed(video_id: str) -> bool:
    """Check if a video is already in ChromaDB."""
    vs = get_vectorstore()
    results = vs.get(where={"video_id": video_id}, limit=1)
    return len(results["ids"]) > 0


def get_chunks_for_video(video_id: str) -> list[Document]:
    """Retrieve all stored chunks for a given video_id from ChromaDB."""
    vs = get_vectorstore()
    results = vs.get(
        where={"video_id": video_id},
        include=["documents", "metadatas"],
    )
    docs = []
    for text, meta in zip(results["documents"], results["metadatas"]):
        docs.append(Document(page_content=text, metadata=meta))
    return docs


# ---------------------------------------------------------------------------
# BM25 index (in-memory, rebuilt per video on demand)
# ---------------------------------------------------------------------------

class BM25Index:
    """Thin wrapper around BM25Okapi tied to a list of Documents."""

    def __init__(self, documents: list[Document]):
        self.documents = documents
        tokenized = [doc.page_content.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized)

    def search(self, query: str, k: int = 10) -> list[Document]:
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:k]
        return [self.documents[i] for i in top_indices if scores[i] > 0]
