"""Normalize extracted text before chunking."""

import re
import unicodedata

HEADER_FOOTER = re.compile(r"(?im)^page\s+\d+(\s+of\s+\d+)?$")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = HEADER_FOOTER.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_doc(doc: dict) -> dict:
    return {"text": clean_text(doc["text"]), "metadata": dict(doc["metadata"])}
