"""Research agent: tool loop, then a structured LLM answer from retrieved text.

Follow-ups use slot memory + an LLM rewrite (not the full chat transcript).
Same-topic pronouns reuse last PDF chunks; new company/year/metric searches again.
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from conversation_memory import (
    FollowupPlan,
    SlotMemory,
    empty_memory,
    load_memory,
    plan_followup,
    update_memory,
)
from report_tools import TOOLS, list_filings, search_reports

load_dotenv()

MAX_STEPS = 4
REFUSE = (
    "I cannot support that from the indexed annual reports. "
    "I only answer from retrieved evidence."
)

SYSTEM = """You are an annual-report research agent. You answer ONLY from tool results.

The filings cover financials, operations, sustainability, packaging, CSR, and similar topics.
If a retrieved chunk discusses the question, answer from it. Do not refuse just because
the question is not a revenue or profit figure.

Rules:
- Call search_reports first. Pass company and fiscal_year only when the user named them
  or they appear in the standalone question.
- Do not invent a year or company filter. If unsure, search with query alone.
- At most one get_page call, and only for a source+page that search_reports already returned.
- Call list_filings only if search_reports returned nothing.
- After you have chunks, stop calling tools. Do not page through the PDF.
- Never use training knowledge, estimates, or the live web.
- If tools do not contain the fact, set grounded=false and refuse.
- When grounded=true you MUST copy evidence_span verbatim from a tool's text field.
- Cite the same source filename and page as that tool result.
"""

TOOLS_BY_NAME = {t.name: t for t in TOOLS}


class FinalAnswer(BaseModel):
    grounded: bool = Field(description="True only if the answer is copied from tool text")
    answer: str = Field(description="Short answer, or a refuse sentence")
    source: str = Field(default="", description="PDF filename from a tool result")
    page: int | None = Field(default=None, description="1-based page from a tool result")
    evidence_span: str = Field(
        default="",
        description="Exact substring copied from the cited chunk's text",
    )
    refuse_reason: str = Field(default="", description="Why the question is unsupported")


def llm_ready() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _chat(**extra: Any) -> ChatOpenAI:
    kwargs: dict[str, Any] = {
        "api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "temperature": 0,
        **extra,
    }
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def _parse_hits(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict) and row.get("text")]
    if isinstance(data, dict) and data.get("text") and not data.get("error"):
        return [data]
    return []


def _followup_payload(plan: FollowupPlan, reused: bool) -> dict:
    return {
        "is_followup": plan.is_followup,
        "same_evidence": plan.same_evidence,
        "intent_changed": plan.intent_changed,
        "rewrite": plan.rewrite,
        "reused_evidence": reused,
    }


def _refuse(
    reason: str,
    evidence: list[dict] | None = None,
    trace: list | None = None,
    memory: SlotMemory | None = None,
    followup: dict | None = None,
) -> dict:
    return {
        "grounded": False,
        "answer": REFUSE,
        "refuse_reason": reason,
        "source": "",
        "page": None,
        "evidence_span": "",
        "evidence": evidence or [],
        "trace": trace or [],
        "memory": (memory or empty_memory()).model_dump(),
        "followup": followup or {},
    }


def ask(question: str, memory: dict | SlotMemory | None = None) -> dict:
    prior = load_memory(memory)
    if not llm_ready():
        return _refuse(
            "Set OPENAI_API_KEY in .env (chat only). Embeddings stay local.",
            memory=prior,
        )
    question = (question or "").strip()
    if not question:
        return _refuse("Empty question.", memory=prior)

    chat = _chat()
    plan = plan_followup(question, prior, chat)
    standalone = plan.rewrite or question
    reused = bool(plan.same_evidence and prior.last_evidence)
    followup = _followup_payload(plan, reused)

    evidence: list[dict] = []
    trace: list[dict] = []
    last: Any = None

    if reused:
        evidence = list(prior.last_evidence)
        trace.append(
            {
                "tool": "reuse_last_evidence",
                "args": {
                    "pages": [h.get("page") for h in evidence],
                    "topic": prior.topic,
                },
                "hits": len(evidence),
            }
        )
    else:
        model = chat.bind_tools(TOOLS)
        messages: list = [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=(
                    f"User question:\n{question}\n\n"
                    f"Standalone question to retrieve and answer:\n{standalone}"
                )
            ),
        ]
        for _ in range(MAX_STEPS):
            last = model.invoke(messages)
            messages.append(last)
            calls = getattr(last, "tool_calls", None) or []
            if not calls:
                break
            for call in calls:
                name = call["name"]
                args = call.get("args") or {}
                trace.append({"tool": name, "args": args})
                tool = TOOLS_BY_NAME.get(name)
                if tool is None:
                    payload = json.dumps({"error": f"Unknown tool {name}"})
                else:
                    payload = tool.invoke(args)
                    if not isinstance(payload, str):
                        payload = json.dumps(payload, default=str)
                hits = _parse_hits(payload)
                evidence.extend(hits)
                trace[-1]["hits"] = len(hits)
                messages.append(
                    ToolMessage(content=payload, tool_call_id=call["id"])
                )

        if not evidence:
            fallback = search_reports.invoke({"query": standalone})
            hits = _parse_hits(
                fallback if isinstance(fallback, str) else json.dumps(fallback)
            )
            evidence.extend(hits)
            trace.append(
                {
                    "tool": "search_reports",
                    "args": {"query": standalone},
                    "hits": len(hits),
                    "fallback": True,
                }
            )

    if not evidence:
        filings = list_filings.invoke({})
        result = _refuse(
            "No report chunks were retrieved. Indexed filings: " + str(filings)[:500],
            evidence=evidence,
            trace=trace,
            followup=followup,
        )
        result["memory"] = update_memory(prior, plan, result).model_dump()
        return result

    draft: FinalAnswer = chat.with_structured_output(FinalAnswer).invoke(
        [
            SystemMessage(
                content=(
                    "Produce the final JSON from the tool evidence only. "
                    "Answer financial, sustainability, packaging, CSR, and operations questions "
                    "when the chunks discuss them. "
                    "Set grounded=true if the evidence is about the question. "
                    "evidence_span must be copied from a tool text field. "
                    "Refuse only if the chunks are about a different company, year, or topic."
                )
            ),
            HumanMessage(
                content=(
                    f"Original question:\n{question}\n\n"
                    f"Standalone question:\n{standalone}\n\n"
                    f"Tool evidence JSON:\n{json.dumps(evidence, ensure_ascii=False)[:12000]}\n\n"
                    f"Last model text:\n{(getattr(last, 'content', None) or '')[:2000]}"
                )
            ),
        ]
    )

    result = {
        "grounded": bool(draft.grounded),
        "answer": draft.answer or REFUSE,
        "source": draft.source if draft.grounded else "",
        "page": draft.page if draft.grounded else None,
        "evidence_span": draft.evidence_span if draft.grounded else "",
        "refuse_reason": "" if draft.grounded else (draft.refuse_reason or REFUSE),
        "evidence": evidence,
        "trace": trace,
        "followup": followup,
    }
    result["memory"] = update_memory(prior, plan, result).model_dump()
    return result


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "What was Nestlé India's sales in 2018?"
    result = ask(q)
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("grounded", "answer", "source", "page", "followup")
                if k in result
            },
            indent=2,
            default=str,
            ensure_ascii=False,
        )
    )
