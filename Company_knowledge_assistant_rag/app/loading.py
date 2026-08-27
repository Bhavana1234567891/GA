"""LangChain PDF loading and document cleaning."""

from __future__ import annotations

import re
from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document

try:
    from langchain_core.documents import BaseDocumentTransformer
except ImportError:  # pragma: no cover
    from langchain_core.documents.transformers import BaseDocumentTransformer

from app.config import settings


def _clean_text(text: str) -> str:
    text = "".join(char for char in text if char.isprintable() or char == "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


class PrintableTextTransformer(BaseDocumentTransformer):
    """Drop non-printable characters and empty pages (leave-policy ingest rules)."""

    def transform_documents(
        self, documents: list[Document], **kwargs
    ) -> list[Document]:
        cleaned: list[Document] = []
        for doc in documents:
            text = _clean_text(doc.page_content)
            if not text:
                continue
            metadata = dict(doc.metadata or {})
            source = metadata.get("source") or metadata.get("file_path") or ""
            metadata["source"] = Path(str(source)).name or str(source)
            page = metadata.get("page")
            if isinstance(page, int):
                metadata["page"] = page + 1 if page >= 0 else page
            cleaned.append(Document(page_content=text, metadata=metadata))
        return cleaned

    async def atransform_documents(
        self, documents: list[Document], **kwargs
    ) -> list[Document]:
        return self.transform_documents(documents, **kwargs)


def load_pdf_documents(path: str | Path) -> list[Document]:
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")
    if pdf_path.stat().st_size > settings.max_file_size_bytes:
        raise ValueError(
            f"PDF size should be less than {settings.max_file_size_mb} MB."
        )

    loader = PyMuPDFLoader(str(pdf_path))
    documents = PrintableTextTransformer().transform_documents(loader.load())
    if not documents:
        raise ValueError("No readable text found in PDF.")
    return documents
