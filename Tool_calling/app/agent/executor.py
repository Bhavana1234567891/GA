"""Look up a tool by name, validate its arguments, and run it."""

from __future__ import annotations

import inspect
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agent import tools as tool_module

# The registry is the bridge between a string name from the model
# and a real Python function.
REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "get_transactions": tool_module.get_transactions,
    "filter_transactions": tool_module.filter_transactions,
    "calculate_total": tool_module.calculate_total,
    "get_categories": tool_module.get_categories,
}


class ToolError(Exception):
    pass


def execute_tool(name: str, arguments: dict[str, Any], db: Session) -> dict[str, Any]:
    fn = REGISTRY.get(name)
    if fn is None:
        raise ToolError(f"Unknown tool '{name}'. Valid tools: {sorted(REGISTRY)}")

    signature = inspect.signature(fn)
    allowed = {key for key in signature.parameters if key != "db"}
    cleaned = {key: value for key, value in arguments.items() if key in allowed and value is not None}

    try:
        return fn(db, **cleaned)
    except Exception as exc:  # noqa: BLE001 — surface any tool failure to the agent
        raise ToolError(f"{name} failed: {exc}") from exc
