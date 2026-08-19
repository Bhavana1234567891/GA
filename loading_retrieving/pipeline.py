"""Run parse → clean → chunk → Chroma for one uploaded file."""

from __future__ import annotations

from cleaning import clean_doc
from chunking import chunk_documents
from parsers import parse
from store import replace_file_chunks


def ingest_file(filename: str, data: bytes) -> dict:
    docs = parse(filename, data)
    cleaned = []
    for doc in docs:
        item = clean_doc(doc)
        if item["text"]:
            cleaned.append(item)
    if not cleaned:
        raise ValueError(f"No usable text after cleaning '{filename}'.")

    chunks = chunk_documents(cleaned)
    if not chunks:
        raise ValueError(f"No chunks produced from '{filename}'.")

    stored = replace_file_chunks(filename, chunks)
    return {
        "source": filename,
        "parsed_parts": len(cleaned),
        "chunks": stored,
    }
