from app.config import settings


def build_context(chunks: list[dict], budget: int | None = None) -> str:
    budget = budget if budget is not None else settings.context_char_budget
    if not chunks:
        return ""

    blocks: list[str] = []
    used = 0
    for index, chunk in enumerate(chunks, start=1):
        score = chunk.get("rerank_score")
        if score is None:
            score = chunk.get("similarity")
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0
        header = (
            f"[{index}] {chunk.get('source', 'unknown')} | "
            f"page {chunk.get('page') or '-'} | "
            f"section: {chunk.get('section') or 'General'} | "
            f"type: {chunk.get('doc_type', 'unknown')} | "
            f"score {score:.3f}"
        )
        block = f"{header}\n{chunk['content'].strip()}"
        extra = len(block) + (2 if blocks else 0)
        if blocks and used + extra > budget:
            break
        blocks.append(block)
        used += extra
    return "\n\n".join(blocks)
