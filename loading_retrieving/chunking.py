"""Split cleaned documents into overlapping chunks."""

from __future__ import annotations

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            window = text[start:end]
            break_at = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(" "))
            if break_at > chunk_size * 0.4:
                end = start + break_at
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_csv(text: str, header: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    prefix = f"{header}\n" if header else ""
    chunks: list[str] = []
    buffer: list[str] = []
    size = len(prefix)

    for line in lines:
        extra = len(line) + 1
        if buffer and size + extra > chunk_size:
            chunks.append(prefix + "\n".join(buffer))
            buffer = [line]
            size = len(prefix) + extra
        else:
            buffer.append(line)
            size += extra

    if buffer:
        chunks.append(prefix + "\n".join(buffer))
    return chunks


def chunk_documents(docs: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    index = 0
    for doc in docs:
        metadata = dict(doc["metadata"])
        if metadata.get("file_type") == "csv":
            pieces = chunk_csv(doc["text"], metadata.get("header", ""))
        else:
            pieces = split_text(doc["text"])

        for piece in pieces:
            chunk_meta = {key: value for key, value in metadata.items() if key != "header"}
            chunk_meta["chunk_index"] = index
            chunks.append({"text": piece, "metadata": chunk_meta})
            index += 1
    return chunks
