"""Build a Chroma index from annual-report PDFs.

Chunking: page-aware RecursiveCharacterTextSplitter (no LLM).
Embeddings: local MiniLM (no embedding API).
Metadata: one chat-LLM call on the first pages (company, year, ticker, type).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pymupdf
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

load_dotenv()

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "data" / "annual_reports"
INDEX_DIR = ROOT / "data" / "vector_index"
COLLECTION = "annual_reports"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
METADATA_PAGES = 4
METADATA_CHARS = 8000


class ReportMetadata(BaseModel):
    """Facts taken only from the front of the filing — not invented."""

    company: str = Field(description="Legal or trading name of the reporting company")
    ticker: str = Field(default="", description="Stock ticker if stated, else empty")
    fiscal_year: int = Field(description="Reporting year of THIS document, e.g. 2018")
    document_type: str = Field(
        default="annual_report",
        description="annual_report, 10-K, or similar",
    )
    aliases: str = Field(
        default="",
        description="Comma-separated other names (short name, group parent)",
    )


def _company_from_filename(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[-_]+", " ", stem)
    stem = re.sub(r"\b(annual|report|final|limited|ltd|inc)\b", "", stem, flags=re.I)
    stem = re.sub(r"\b(19|20)\d{2}\b", "", stem)
    return re.sub(r"\s+", " ", stem).strip().title() or Path(name).stem


class MiniLMEmbeddings(Embeddings):
    """all-MiniLM-L6-v2 via ONNX — free, local, no API key."""

    def __init__(self) -> None:
        self._fn = DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in row] for row in self._fn(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in self._fn([text])[0]]


def embeddings() -> Embeddings:
    return MiniLMEmbeddings()


def _chat() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is required for metadata extraction (chat only, not embeddings)."
        )
    kwargs: dict = {
        "api_key": api_key,
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "temperature": 0,
    }
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def extract_metadata(pdf_path: Path, pages: list[Document]) -> dict:
    """One LLM call on the cover pages. Embeddings are not used here."""
    sample = "\n\n".join(p.page_content for p in pages[:METADATA_PAGES])[:METADATA_CHARS]
    prompt = (
        "Extract filing metadata from this annual-report front matter. "
        "Use only what the text supports. fiscal_year is the year of THIS report, "
        "not a comparative prior year.\n\n"
        f"Filename: {pdf_path.name}\n\n{sample}"
    )
    extracted: ReportMetadata = (
        _chat().with_structured_output(ReportMetadata).invoke(prompt)
    )
    meta = {
        "company": extracted.company.strip(),
        "ticker": (extracted.ticker or "").strip(),
        "fiscal_year": int(extracted.fiscal_year),
        "document_type": (extracted.document_type or "annual_report").strip(),
        "aliases": (extracted.aliases or "").strip(),
    }
    if not meta["company"]:
        meta["company"] = _company_from_filename(pdf_path.name)
    return meta


def load_pages(pdf_path: Path) -> list[Document]:
    pages: list[Document] = []
    with pymupdf.open(pdf_path) as pdf:
        for i, page in enumerate(pdf):
            text = (page.get_text("text") or "").strip()
            if not text:
                continue
            pages.append(
                Document(
                    page_content=text,
                    metadata={"source": pdf_path.name, "page": i + 1},
                )
            )
    return pages


def apply_doc_metadata(pages: list[Document], doc_meta: dict) -> None:
    for page in pages:
        page.metadata.update(doc_meta)


def chunk_pages(pages: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks: list[Document] = []
    for page in pages:
        pieces = splitter.split_documents([page])
        for i, piece in enumerate(pieces):
            piece.metadata = {**page.metadata, "chunk_index": i}
            chunks.append(piece)
    return chunks


def ingest() -> Chroma:
    pdfs = sorted(REPORTS_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {REPORTS_DIR}")

    all_chunks: list[Document] = []
    for pdf in pdfs:
        pages = load_pages(pdf)
        doc_meta = extract_metadata(pdf, pages)
        apply_doc_metadata(pages, doc_meta)
        chunks = chunk_pages(pages)
        all_chunks.extend(chunks)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings(),
        persist_directory=str(INDEX_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    if store._collection.count() > 0:
        store.reset_collection()

    ids = [
        f"{c.metadata['source']}::p{c.metadata['page']}::{c.metadata['chunk_index']}"
        for c in all_chunks
    ]
    store.add_documents(documents=all_chunks, ids=ids)
    print(f"Stored {len(all_chunks)} chunks in {INDEX_DIR}")
    return store


if __name__ == "__main__":
    ingest()
