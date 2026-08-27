"""Turn casual HR questions into policy-search text."""

from __future__ import annotations


def expand_query(question: str) -> tuple[str, list[str]]:
    text = question.strip()
    low = text.lower()
    extra: list[str] = []
    keywords: list[str] = []

    if any(word in low for word in ("sick", "illness", "ill ", "medical", "hospital", "unwell")):
        extra.append(
            "half pay leave Rule 29 credited ten days January July "
            "leave on medical certificate commuted leave hospital leave"
        )
        keywords.extend(
            [
                "half pay leave",
                "commuted leave",
                "medical certificate",
                "hospital leave",
            ]
        )

    if any(word in low for word in ("how many", "total", "entitled", "do i have", "quota", "credit", "balance")):
        extra.append(
            "earned leave Rule 26 Departments other than Vacation "
            "credited in two instalments of 15 days each January July "
            "half pay leave Rule 29 two instalments of ten days"
        )
        keywords.extend(
            [
                "instalments of 15 days",
                "earned leave for Government servants serving in Departments other than Vacation",
                "half pay leave",
            ]
        )

    if "casual" in low:
        extra.append("casual leave not recognized as leave under these rules")
        keywords.append("casual leave")

    if "earned" in low or "privilege" in low or "el " in low:
        keywords.append("earned leave")

    # unique, keep order
    seen: set[str] = set()
    unique_keywords: list[str] = []
    for term in keywords:
        if term not in seen:
            seen.add(term)
            unique_keywords.append(term)

    search = text if not extra else f"{text} {' '.join(extra)}"
    return search, unique_keywords
