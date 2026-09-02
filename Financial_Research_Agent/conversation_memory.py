"""Slot memory + LLM follow-up rewrite.

Not full chat history. Streamlit keeps this dict in session_state; ask()
reads it, rewrites the question, optionally reuses last PDF chunks, then
returns an updated dict.
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field

from report_tools import _fold

REWRITE_SYSTEM = """You rewrite annual-report questions so they stand alone.

Use the memory slots when the new question is a follow-up (pronouns, 'it',
'that', 'how much', 'was it helpful', 'what about PAT', 'the previous year').
Do not invent a company or year that is not in the question or the slots.

same_evidence=true ONLY if the user is still asking about the SAME programme
or figure already in last_topic / last pages (e.g. 'was it helpful?').
same_evidence=false if they switch metric, company, or year (PAT, Tesla, 2025).

intent_changed=true if company, fiscal_year, or topic is no longer the slots
(including a new company that will likely be refused).
"""


class SlotMemory(BaseModel):
    """What the agent needs for the next turn — not the chat transcript."""

    model_config = ConfigDict(extra="ignore")

    company: str = ""
    fiscal_year: int | None = None
    topic: str = ""
    source: str = ""
    page: int | None = None
    last_span: str = ""
    last_evidence: list[dict] = Field(default_factory=list)
    summary: str = ""


class FollowupPlan(BaseModel):
    """LLM decision: follow-up?, reuse chunks?, standalone question."""

    is_followup: bool = Field(
        description="True if this question continues the previous topic/company/year"
    )
    same_evidence: bool = Field(
        description="True only if last_evidence still answers this question"
    )
    rewrite: str = Field(
        description="Standalone question for search and answering"
    )
    company: str = Field(default="", description="Company this question is about")
    fiscal_year: int | None = Field(
        default=None, description="Year this question is about, if any"
    )
    topic: str = Field(default="", description="Short topic label")
    intent_changed: bool = Field(
        default=False,
        description="True if company, year, or topic switched vs memory slots",
    )


def empty_memory() -> SlotMemory:
    return SlotMemory()


def load_memory(raw: dict | SlotMemory | None) -> SlotMemory:
    if raw is None:
        return empty_memory()
    if isinstance(raw, SlotMemory):
        return raw
    return SlotMemory.model_validate(raw)


def memory_is_empty(memory: SlotMemory) -> bool:
    return not (memory.company or memory.topic or memory.last_evidence)


def years_in(text: str) -> list[int]:
    return [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", text or "")]


def _topic_overlap(left: str, right: str) -> bool:
    a = set(_fold(left).split())
    b = set(_fold(right).split())
    a.discard("the")
    b.discard("the")
    return bool(a and b and a & b)


def apply_safety(question: str, memory: SlotMemory, plan: FollowupPlan) -> FollowupPlan:
    """LLM is primary; Python only blocks unsafe chunk reuse."""
    rewrite = (plan.rewrite or "").strip() or question
    plan.rewrite = rewrite

    if memory_is_empty(memory):
        plan.is_followup = False
        plan.same_evidence = False
        plan.intent_changed = False
        if not (plan.rewrite or "").strip():
            plan.rewrite = question
        return plan

    if not memory.last_evidence:
        plan.same_evidence = False

    mem_co = _fold(memory.company)
    plan_co = _fold(plan.company)
    if plan_co and mem_co and not all(tok in mem_co for tok in plan_co.split() if len(tok) > 2):
        plan.same_evidence = False
        plan.intent_changed = True

    q_years = years_in(question)
    if memory.fiscal_year and q_years and memory.fiscal_year not in q_years:
        plan.same_evidence = False
        plan.intent_changed = True

    if (
        plan.fiscal_year
        and memory.fiscal_year
        and plan.fiscal_year != memory.fiscal_year
    ):
        plan.same_evidence = False
        plan.intent_changed = True

    if plan.topic and memory.topic and not _topic_overlap(plan.topic, memory.topic):
        plan.same_evidence = False
        if plan.is_followup:
            plan.intent_changed = True

    return plan


def plan_followup(question: str, memory: SlotMemory, chat: Any) -> FollowupPlan:
    """One structured LLM call: detect follow-up and rewrite."""
    slots = {
        "company": memory.company,
        "fiscal_year": memory.fiscal_year,
        "topic": memory.topic,
        "source": memory.source,
        "page": memory.page,
        "last_span": (memory.last_span or "")[:400],
        "summary": memory.summary,
        "evidence_pages": [
            h.get("page") for h in memory.last_evidence if isinstance(h, dict)
        ],
        "empty": memory_is_empty(memory),
    }
    raw: FollowupPlan = chat.with_structured_output(FollowupPlan).invoke(
        [
            SystemMessage(content=REWRITE_SYSTEM),
            HumanMessage(
                content=(
                    f"Memory slots:\n{slots}\n\n"
                    f"New question:\n{question}\n\n"
                    "If memory is empty this is the first turn: is_followup=false, "
                    "same_evidence=false, still fill company, fiscal_year, and topic "
                    "from the question when they are stated or implied."
                )
            ),
        ]
    )
    return apply_safety(question, memory, raw)


def update_memory(
    memory: SlotMemory,
    plan: FollowupPlan,
    result: dict,
) -> SlotMemory:
    """Grounded → fill from filing. New-intent refuse → slots from question, no chunks."""
    if result.get("grounded"):
        evidence = result.get("evidence") or []
        hit = evidence[0] if evidence else {}
        company = str(hit.get("company") or plan.company or memory.company)
        year = hit.get("fiscal_year")
        if year is None:
            year = plan.fiscal_year if plan.fiscal_year is not None else memory.fiscal_year
        topic = plan.topic or memory.topic
        source = str(result.get("source") or hit.get("source") or "")
        page = result.get("page") if result.get("page") is not None else hit.get("page")
        return SlotMemory(
            company=company,
            fiscal_year=int(year) if year is not None else None,
            topic=topic,
            source=source,
            page=int(page) if page is not None else None,
            last_span=str(result.get("evidence_span") or ""),
            last_evidence=list(evidence),
            summary=(
                f"{company} {year or ''}: {topic}. "
                f"Cited {source} page {page}."
            ).strip(),
        )

    switched = plan.intent_changed or (
        not plan.is_followup
        and not memory_is_empty(memory)
        and (
            (plan.company and _fold(plan.company) != _fold(memory.company))
            or (
                plan.fiscal_year is not None
                and plan.fiscal_year != memory.fiscal_year
            )
            or (
                plan.topic
                and memory.topic
                and not _topic_overlap(plan.topic, memory.topic)
            )
        )
    )
    if switched:
        return SlotMemory(
            company=plan.company or "",
            fiscal_year=plan.fiscal_year,
            topic=plan.topic or "",
            source="",
            page=None,
            last_span="",
            last_evidence=[],
            summary=(
                f"Asked about {plan.company or 'unknown company'} "
                f"{plan.fiscal_year or ''} {plan.topic or ''}; "
                "not supported by indexed filings."
            ).strip(),
        )

    return memory
