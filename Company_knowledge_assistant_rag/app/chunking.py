"""LangChain heading-aware split, then RecursiveCharacterTextSplitter (800/200)."""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, TextSplitter

from app.config import settings

SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

HEADING_RE = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*[.)]\s+\S.+"
    r"|CHAPTER\s+[IVXLC]+\b.*"
    r"|[A-Z][A-Z0-9 ,/&'\-]{7,}"
    r"|#{1,3}\s+\S.+"
    r")$"
)
RULE_NUMBER_RE = re.compile(r"^(\d+)\.\s*$")
RULE_INLINE_RE = re.compile(r"^(\d+)\.\s+(\S.+)$")

HR_HINTS = (
    "leave",
    "holiday",
    "payroll",
    "attendance",
    "maternity",
    "wfh",
    "work from home",
    "human resource",
    "hr policy",
)
TECH_HINTS = (
    "vpn",
    "laptop",
    "password",
    "wifi",
    "software",
    "git",
    "email",
    "access",
    "onboarding",
)
FAQ_HINTS = ("faq", "frequently asked", "q:", "question")
COMPANY_HINTS = ("conduct", "travel", "ethics", "code of", "security policy")


def infer_doc_type(section: str, source: str = "") -> str:
    blob = f"{section} {source}".lower()
    if any(hint in blob for hint in FAQ_HINTS):
        return "faq"
    if any(hint in blob for hint in TECH_HINTS):
        return "technical"
    if any(hint in blob for hint in HR_HINTS):
        return "hr_policy"
    if any(hint in blob for hint in COMPANY_HINTS):
        return "company_policy"
    return "hr_policy"


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    return bool(HEADING_RE.match(stripped))


def _rule_title_lines(lines: list[str], start: int) -> tuple[str, int]:
    """CCS PDFs put '29.' on one line and the rule title on the next."""
    title_parts: list[str] = []
    index = start
    while index < len(lines):
        candidate = lines[index].strip()
        if not candidate:
            index += 1
            continue
        if RULE_NUMBER_RE.match(candidate) or RULE_INLINE_RE.match(candidate):
            break
        if candidate.startswith("(") or candidate.lower().startswith("provided"):
            break
        title_parts.append(candidate)
        index += 1
        joined = " ".join(title_parts)
        if len(joined) >= 24 or len(title_parts) >= 3:
            break
    return " ".join(title_parts), index


def split_into_sections(text: str, page: int | None = None) -> list[dict]:
    lines = text.splitlines()
    sections: list[dict] = []
    current_heading = "General"
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            sections.append({"section": current_heading, "text": body, "page": page})

    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        numbered = RULE_NUMBER_RE.match(stripped)
        inline = RULE_INLINE_RE.match(stripped)
        if numbered:
            flush()
            title, next_index = _rule_title_lines(lines, index + 1)
            current_heading = f"{numbered.group(1)}. {title}".strip()
            buffer = []
            index = next_index
            continue
        if inline or _is_heading(stripped):
            flush()
            current_heading = stripped.lstrip("#").strip()
            buffer = []
            index += 1
            continue
        buffer.append(lines[index])
        index += 1
    flush()
    return sections or [{"section": "General", "text": text.strip(), "page": page}]


class PolicySectionSplitter(TextSplitter):
    """LangChain splitter that attaches CCS/HR section titles as metadata."""

    def __init__(self) -> None:
        super().__init__(chunk_size=10**9, chunk_overlap=0)

    def split_text(self, text: str) -> list[str]:
        return [section["text"] for section in split_into_sections(text) if section["text"].strip()]

    def split_documents(self, documents: list[Document]) -> list[Document]:
        splits: list[Document] = []
        for doc in documents:
            source = Path(str(doc.metadata.get("source") or "")).name
            page = doc.metadata.get("page")
            page = page if isinstance(page, int) else None
            for section in split_into_sections(doc.page_content, page):
                if not section["text"].strip():
                    continue
                metadata = dict(doc.metadata or {})
                metadata["source"] = source or metadata.get("source")
                metadata["page"] = section.get("page") or page
                metadata["section"] = section["section"]
                metadata["doc_type"] = infer_doc_type(section["section"], source)
                splits.append(Document(page_content=section["text"], metadata=metadata))
        return splits


def get_recursive_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=SEPARATORS,
        length_function=len,
    )


def finalize_chunks(documents: list[Document]) -> list[Document]:
    for index, doc in enumerate(documents):
        section = doc.metadata.get("section") or "General"
        doc.metadata["chunk_index"] = index
        if not doc.page_content.startswith("Section:"):
            doc.page_content = f"Section: {section}\n{doc.page_content}"
    return documents
