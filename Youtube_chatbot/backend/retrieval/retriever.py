"""
Retrieval pipeline: hybrid (vector MMR + BM25), reciprocal rank fusion,
cross-encoder reranking, and contextual compression.
"""

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from backend.vectorstore.store import get_vectorstore, BM25Index, get_chunks_for_video
from backend.retrieval.query_transform import generate_multi_queries

import tiktoken

# Lazy-loaded to avoid slow torch import at server startup
_cross_encoder = None

def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


# ── Hybrid Retrieval ───────────────────────────────────────────────────────

def _vector_retrieve(query: str, video_id: str, k: int = 10) -> list[Document]:
    """MMR retrieval from ChromaDB for diversity."""
    vs = get_vectorstore()
    retriever = vs.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": k * 3,
            "filter": {"video_id": video_id},
        },
    )
    return retriever.invoke(query)


def _bm25_retrieve(query: str, video_id: str, k: int = 10) -> list[Document]:
    """Keyword retrieval via BM25."""
    all_chunks = get_chunks_for_video(video_id)
    if not all_chunks:
        return []
    bm25 = BM25Index(all_chunks)
    return bm25.search(query, k=k)


def _reciprocal_rank_fusion(
    ranked_lists: list[list[Document]], k: int = 60
) -> list[Document]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.
    Higher fused score = more consistently ranked across lists.
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked):
            doc_key = doc.page_content[:200]  # dedupe key
            if doc_key not in doc_map:
                doc_map[doc_key] = doc
                scores[doc_key] = 0.0
            scores[doc_key] += 1.0 / (k + rank + 1)

    sorted_keys = sorted(scores, key=scores.get, reverse=True)
    return [doc_map[key] for key in sorted_keys]


# ── Reranking (free, local cross-encoder) ──────────────────────────────────

def _rerank(query: str, docs: list[Document], top_n: int = 5) -> list[Document]:
    """Rescore documents with a cross-encoder and return top_n."""
    if not docs:
        return []
    encoder = _get_cross_encoder()
    pairs = [(query, doc.page_content) for doc in docs]
    scores = encoder.predict(pairs)
    ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_n]]


# ── Contextual Compression (LLM-based) ────────────────────────────────────

_compress_llm = None

def _get_compress_llm():
    global _compress_llm
    if _compress_llm is None:
        _compress_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _compress_llm


def _compress_doc(query: str, doc: Document) -> Document:
    """Strip filler from a chunk, keeping only sentences relevant to the query."""
    llm = _get_compress_llm()
    prompt = (
        f"Extract ONLY the sentences from the following transcript excerpt "
        f"that are relevant to the question: \"{query}\"\n\n"
        f"Transcript:\n{doc.page_content}\n\n"
        f"Return only the relevant sentences. If nothing is relevant, return "
        f"the single word NONE."
    )
    result = llm.invoke(prompt).content.strip()
    if result.upper() == "NONE":
        return None
    return Document(page_content=result, metadata=doc.metadata)


def _compress_docs(query: str, docs: list[Document]) -> list[Document]:
    """Compress all docs, dropping empty ones."""
    compressed = []
    for doc in docs:
        result = _compress_doc(query, doc)
        if result is not None:
            compressed.append(result)
    return compressed


# ── Context Window Optimization ────────────────────────────────────────────

def _trim_to_token_budget(
    docs: list[Document], max_tokens: int = 3000
) -> list[Document]:
    """
    Keep docs (already sorted by relevance) until the token budget runs out.
    Docs beyond the budget are dropped from the bottom.
    """
    enc = tiktoken.encoding_for_model("gpt-4o-mini")
    total = 0
    kept: list[Document] = []
    for doc in docs:
        count = len(enc.encode(doc.page_content))
        if total + count > max_tokens:
            break
        total += count
        kept.append(doc)
    return kept if kept else docs[:1]  # always keep at least one


# ── Full Retrieval Pipeline ────────────────────────────────────────────────

def retrieve(
    question: str,
    video_id: str,
    use_multi_query: bool = True,
    use_compression: bool = True,
    top_n: int = 5,
    token_budget: int = 3000,
) -> list[Document]:
    """
    End-to-end retrieval:
      1. Multi-query generation (3 rephrasings + original)
      2. Hybrid retrieval (MMR vector + BM25) per query
      3. Reciprocal rank fusion across all results
      4. Cross-encoder reranking -> top_n
      5. Contextual compression (LLM strips filler)
      6. Token budget trimming (most relevant first)
    """
    # 1. Generate queries
    if use_multi_query:
        queries = generate_multi_queries(question)
    else:
        queries = [question]

    # 2. Hybrid retrieve for each query
    all_vector_results: list[list[Document]] = []
    all_bm25_results: list[list[Document]] = []

    for q in queries:
        all_vector_results.append(_vector_retrieve(q, video_id, k=10))
        all_bm25_results.append(_bm25_retrieve(q, video_id, k=10))

    # Flatten into two big ranked lists, then fuse
    vector_fused = _reciprocal_rank_fusion(all_vector_results)
    bm25_fused = _reciprocal_rank_fusion(all_bm25_results)
    fused = _reciprocal_rank_fusion([vector_fused, bm25_fused])

    # 3. Rerank
    reranked = _rerank(question, fused, top_n=top_n)

    # 4. Contextual compression (keep originals as fallback)
    if use_compression:
        compressed = _compress_docs(question, reranked)
        if compressed:
            reranked = compressed
        # else: keep the original reranked docs

    # 5. Token budget
    trimmed = _trim_to_token_budget(reranked, max_tokens=token_budget)

    return trimmed
