"""Persist and query chunks in a local ChromaDB collection."""

from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb

DB_DIR = Path(__file__).resolve().parent / "chroma_db"
COLLECTION_NAME = "documents"
# L2 distances above this are treated as unrelated (MiniLM).
MAX_DISTANCE = 1.2

_client = None


def get_client():
    global _client
    if _client is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(DB_DIR))
    return _client


def get_collection():
    return get_client().get_or_create_collection(name=COLLECTION_NAME)


def chunk_id(source: str, chunk_index: int) -> str:
    return hashlib.sha256(f"{source}:{chunk_index}".encode("utf-8")).hexdigest()


def sanitize_metadata(metadata: dict) -> dict:
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def chunk_count() -> int:
    return get_collection().count()


def replace_file_chunks(source: str, chunks: list[dict]) -> int:
    collection = get_collection()
    if chunk_count() > 0:
        collection.delete(where={"source": source})

    if not chunks:
        return 0

    ids = []
    documents = []
    metadatas = []
    for chunk in chunks:
        meta = sanitize_metadata(chunk["metadata"])
        ids.append(chunk_id(source, meta["chunk_index"]))
        documents.append(chunk["text"])
        metadatas.append(meta)

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def list_sources() -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    data = collection.get(include=["metadatas"])
    counts: dict[str, int] = {}
    for meta in data.get("metadatas") or []:
        source = meta.get("source", "unknown")
        counts[source] = counts.get(source, 0) + 1
    return [{"source": name, "chunks": count} for name, count in sorted(counts.items())]


def clear_all() -> None:
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    client.get_or_create_collection(name=COLLECTION_NAME)


def query_chunks(text: str, n_results: int = 5, max_distance: float = MAX_DISTANCE) -> dict:
    collection = get_collection()
    total = collection.count()
    empty = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    if total == 0:
        return empty

    raw = collection.query(query_texts=[text], n_results=min(n_results, total))
    ids, docs, metas, distances = [], [], [], []
    for i, distance in enumerate((raw.get("distances") or [[]])[0]):
        if distance is not None and distance > max_distance:
            continue
        ids.append((raw.get("ids") or [[]])[0][i])
        docs.append((raw.get("documents") or [[]])[0][i])
        metas.append((raw.get("metadatas") or [[]])[0][i])
        distances.append(distance)
    return {"ids": [ids], "documents": [docs], "metadatas": [metas], "distances": [distances]}
