"""LangChain tool-calling loop. Falls back to the rules planner when no API key is set."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app import memory as store
from app.agent.planner import run_rules_agent
from app.agent.prompts import system_prompt
from app.agent.tools import build_tools
from app.config import settings


def _llm() -> ChatOpenAI:
    kwargs: dict[str, Any] = {
        "model": settings.llm_model,
        "api_key": settings.openai_api_key,
        "temperature": 0,
    }
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    return ChatOpenAI(**kwargs)


def _history_messages(db: Session, user_id: str) -> list:
    rows = store.history(db, user_id)
    out: list = []
    for row in rows:
        if row["role"] == "user":
            out.append(HumanMessage(content=row["content"]))
        elif row["role"] == "assistant":
            out.append(AIMessage(content=row["content"]))
    return out


def run_llm_agent(message: str, db: Session, user_id: str) -> dict[str, Any]:
    tools = build_tools(db, user_id)
    by_name = {tool.name: tool for tool in tools}
    model = _llm().bind_tools(tools)
    snap = store.snapshot(db, user_id)
    messages: list = [
        SystemMessage(content=system_prompt(snap)),
        *_history_messages(db, user_id),
        HumanMessage(content=message),
    ]
    trace: list[dict[str, Any]] = []

    for _ in range(settings.max_agent_steps):
        ai: AIMessage = model.invoke(messages)
        messages.append(ai)
        tool_calls = getattr(ai, "tool_calls", None) or []
        if not tool_calls:
            answer = (ai.content or "").strip() or "I could not produce an answer."
            return {"answer": answer, "trace": trace, "mode": "llm"}

        for call in tool_calls:
            name = call["name"]
            arguments = call.get("args") or {}
            trace.append({"type": "tool_call", "name": name, "arguments": arguments})
            tool = by_name.get(name)
            if tool is None:
                result = {"error": f"Unknown tool '{name}'"}
            else:
                try:
                    raw = tool.invoke(arguments)
                    result = json.loads(raw) if isinstance(raw, str) else raw
                except Exception as exc:  # noqa: BLE001 — surface tool failures to the model
                    result = {"error": str(exc)}
            trace.append({"type": "tool_result", "name": name, "result": result})
            messages.append(
                ToolMessage(
                    content=json.dumps(result, ensure_ascii=False, default=str),
                    tool_call_id=call["id"],
                )
            )

    return {
        "answer": "I reached the step limit before finishing. Try a shorter request.",
        "trace": trace,
        "mode": "llm",
    }


def run_agent(message: str, db: Session, user_id: str) -> dict[str, Any]:
    store.ensure_user(db, user_id)
    if settings.llm_enabled:
        return run_llm_agent(message, db, user_id)
    return run_rules_agent(message, db, user_id)
