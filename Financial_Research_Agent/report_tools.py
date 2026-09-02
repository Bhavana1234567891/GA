"""Tools the grounded agent may use: search, fetch a page, list filings.

No web search. If a fact is not in the vector index, the agent must not know it.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from unicodedata import combining, normalize

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.tools import tool

from build_vector_index import COLLECTION, INDEX_DIR, embeddings

CANDIDATE_K = 8
TOP_N = 4
MAX_DISTANCE = 0.75


@lru_cache(maxsize=1)
def get_store() -> Chroma:
    if not INDEX_DIR.exists():
        raise FileNotFoundError(
            f"No index at {INDEX_DIR}. Run: python build_vector_index.py"
        )
    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings(),
        persist_directory=str(INDEX_DIR),
    )
    if store._collection.count() == 0:
        raise RuntimeError(
            f"Collection {COLLECTION!r} is empty. Run: python build_vector_index.py"
        )
    return store


def _fold(text: str) -> str:
    """Lowercase, strip accents, treat hyphens as spaces — Nestle matches Nestlé."""
    stripped = "".join(ch for ch in normalize("NFKD", text or "") if not combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()


def _chunk_to_hit(doc: Document, distance: float | None = None) -> dict:
    meta = doc.metadata or {}
    hit = {
        "source": meta.get("source"),
        "page": meta.get("page"),
        "company": meta.get("company"),
        "fiscal_year": meta.get("fiscal_year"),
        "text": doc.page_content,
    }
    if distance is not None:
        hit["distance"] = round(float(distance), 4)
    return hit


def _company_matches(meta: dict, company: str) -> bool:
    needle = _fold(company)
    if not needle:
        return True
    hay = " ".join(
        _fold(str(meta.get(key) or ""))
        for key in ("company", "ticker", "aliases", "source")
    )
    return all(token in hay for token in needle.split())


@tool
def search_reports(
    query: str,
    company: str | None = None,
    fiscal_year: int | None = None,
) -> str:
    """Search indexed annual-report chunks.

    Uses the same MiniLM embeddings as ingest. Returns up to 4 chunks as JSON:
    source, page, company, fiscal_year, text, distance.

    Optional company / fiscal_year keep only matching filings.
    If a fiscal_year filter returns no hits, the query is retried without the year
    so a guessed year does not hide chunks from the indexed filing.
    """
    store = get_store()

    def _search(chroma_filter: dict | None) -> list[dict]:
        raw = store.similarity_search_with_score(
            query,
            k=CANDIDATE_K,
            filter=chroma_filter,
        )
        kept: list[dict] = []
        for doc, distance in raw:
            if distance > MAX_DISTANCE:
                continue
            if company and not _company_matches(doc.metadata or {}, company):
                continue
            kept.append(_chunk_to_hit(doc, distance))
            if len(kept) >= TOP_N:
                break
        return kept

    chroma_filter = None
    if fiscal_year is not None:
        chroma_filter = {"fiscal_year": int(fiscal_year)}

    kept = _search(chroma_filter)
    if not kept and chroma_filter:
        kept = _search(None)

    return json.dumps(kept, ensure_ascii=False, indent=2)


@tool
def get_page(source: str, page: int) -> str:
    """Return the full text of one PDF page from the index."""
    store = get_store()
    page_num = int(page)
    result = store.get(
        where={"$and": [{"source": source}, {"page": page_num}]},
        include=["metadatas", "documents"],
    )
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    if not documents:
        return json.dumps(
            {
                "source": source,
                "page": page_num,
                "text": "",
                "error": "Page not found in the index.",
            },
            ensure_ascii=False,
            indent=2,
        )

    pairs = list(zip(documents, metadatas))
    pairs.sort(key=lambda item: (item[1] or {}).get("chunk_index") or 0)
    text = "\n\n".join(piece for piece, _ in pairs if piece)
    meta = pairs[0][1] or {}
    return json.dumps(
        {
            "source": meta.get("source", source),
            "page": meta.get("page", page_num),
            "company": meta.get("company"),
            "fiscal_year": meta.get("fiscal_year"),
            "text": text,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def list_filings() -> str:
    """List which annual reports are in the index (filename, company, year)."""
    store = get_store()
    result = store.get(include=["metadatas"])
    metadatas = result.get("metadatas") or []

    filings: dict[str, dict] = {}
    for meta in metadatas:
        if not meta:
            continue
        source = meta.get("source")
        if not source or source in filings:
            continue
        filings[source] = {
            "source": source,
            "company": meta.get("company"),
            "ticker": meta.get("ticker"),
            "fiscal_year": meta.get("fiscal_year"),
        }

    return json.dumps(list(filings.values()), ensure_ascii=False, indent=2)


TOOLS = [search_reports, get_page, list_filings]


if __name__ == "__main__":
    import sys

    print("=== list_filings ===")
    print(list_filings.invoke({}))
    query = sys.argv[1] if len(sys.argv) > 1 else "revenue"
    print(f"\n=== search_reports({query!r}) ===")
    print(search_reports.invoke({"query": query}))
