"""
The agent loop — this is the heart of the project.

Flow of one question:

  1. Tool definitions   — Python functions in tools.py
  2. Tool schemas       — JSON contracts in schemas.py, sent to the model
  3. Function calling   — the model returns a tool name instead of prose
  4. Argument generation — the model fills start_date, category, etc.
  5. Tool execution     — executor.py runs the Python function against Postgres
  6. Tool responses     — JSON results are appended to the conversation
  7. Multiple tool calls — the loop repeats until the model writes a final answer

If OPENAI_API_KEY is missing, the same tools are driven by the rules planner.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.agent.executor import ToolError, execute_tool
from app.agent.planner import run_rules_agent
from app.agent.prompts import system_prompt
from app.agent.schemas import TOOL_SCHEMAS
from app.config import settings


def _llm_client() -> OpenAI:
    kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    return OpenAI(**kwargs)


def run_llm_agent(question: str, db: Session, today: date) -> dict[str, Any]:
    client = _llm_client()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt(today)},
        {"role": "user", "content": question},
    ]
    trace: list[dict[str, Any]] = []

    for _ in range(settings.max_agent_steps):
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        message = response.choices[0].message
        assistant: dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            assistant["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in message.tool_calls
            ]
        messages.append(assistant)

        if not message.tool_calls:
            answer = (message.content or "").strip() or "I could not produce an answer."
            return {"answer": answer, "trace": trace, "mode": "llm"}

        for call in message.tool_calls:
            name = call.function.name
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            trace.append({"type": "tool_call", "name": name, "arguments": arguments})
            try:
                result = execute_tool(name, arguments, db)
            except ToolError as exc:
                result = {"error": str(exc)}
            trace.append({"type": "tool_result", "name": name, "result": result})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str),
                }
            )

    return {
        "answer": "I reached the step limit before finishing. Try a more specific question.",
        "trace": trace,
        "mode": "llm",
    }


def run_agent(question: str, db: Session, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    if settings.llm_enabled:
        return run_llm_agent(question, db, today)
    return run_rules_agent(question, db, today)
