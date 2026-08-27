"""
Rules planner — used when no LLM API key is set.

It still goes through the same tools as the LLM path. The only difference is
how arguments are generated: regex + heuristics instead of a language model.
That makes the project runnable on day one, and keeps the tool-calling flow
visible in the UI.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.agent.dates import resolve_period
from app.agent.executor import execute_tool

CATEGORY_ALIASES = {
    "food": "Food & Dining",
    "dining": "Food & Dining",
    "restaurant": "Food & Dining",
    "restaurants": "Food & Dining",
    "eat": "Food & Dining",
    "eating": "Food & Dining",
    "grocery": "Groceries",
    "groceries": "Groceries",
    "transport": "Transport",
    "transportation": "Transport",
    "gas": "Transport",
    "shopping": "Shopping",
    "amazon": "Shopping",
    "entertainment": "Entertainment",
    "bills": "Bills & Utilities",
    "utilities": "Bills & Utilities",
    "rent": "Bills & Utilities",
    "health": "Healthcare",
    "healthcare": "Healthcare",
    "medical": "Healthcare",
    "travel": "Travel",
    "subscription": "Subscriptions",
    "subscriptions": "Subscriptions",
    "netflix": "Subscriptions",
}

MERCHANT_ALIASES = {
    "starbucks": "Starbucks",
    "chipotle": "Chipotle",
    "mcdonald's": "McDonald's",
    "mcdonalds": "McDonald's",
    "sweetgreen": "Sweetgreen",
    "uber eats": "Uber Eats",
    "whole foods": "Whole Foods",
    "trader joe's": "Trader Joe's",
    "walmart": "Walmart",
    "costco": "Costco",
    "amazon": "Amazon",
    "target": "Target",
    "nike": "Nike",
    "netflix": "Netflix",
    "spotify": "Spotify",
    "airbnb": "Airbnb",
    "lyft": "Lyft",
    "uber": "Uber",
}


def _match_category(question: str) -> str | None:
    q = question.lower()
    for alias, name in sorted(CATEGORY_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(alias)}\b", q):
            return name
    return None


def _match_merchant(question: str) -> str | None:
    q = question.lower()
    for alias, name in sorted(MERCHANT_ALIASES.items(), key=lambda item: -len(item[0])):
        if alias in q:
            return name
    return None


def _wants_total(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in ("how much", "spend", "spent", "total", "sum", "cost"))


def _wants_categories(question: str) -> bool:
    q = question.lower()
    return "categor" in q or "what do i spend" in q or "breakdown" in q


def _wants_largest(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in ("largest", "biggest", "most expensive", "top"))


def _money(amount: float) -> str:
    return f"${amount:,.2f}"


def run_rules_agent(question: str, db: Session, today: date) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    start, end = resolve_period(question, today)
    category = _match_category(question)
    merchant = _match_merchant(question)

    def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        trace.append({"type": "tool_call", "name": name, "arguments": arguments})
        result = execute_tool(name, arguments, db)
        trace.append({"type": "tool_result", "name": name, "result": result})
        return result

    if _wants_categories(question) and not category:
        data = call("get_categories", {})
        lines = [
            f"{row['name']}: {_money(row['total'])} ({row['transaction_count']} txns)"
            for row in data["categories"]
        ]
        answer = "Here is your spending by category:\n" + "\n".join(lines)
        return {"answer": answer, "trace": trace, "mode": "rules"}

    if _wants_total(question) and not _wants_largest(question):
        arguments: dict[str, Any] = {}
        target = "all categories"
        if merchant:
            arguments["merchant"] = merchant
            target = merchant
        elif category:
            catalog = call("get_categories", {})
            names = {row["name"].lower(): row["name"] for row in catalog["categories"]}
            resolved = names.get(category.lower(), category)
            arguments["category"] = resolved
            target = resolved
        if start:
            arguments["start_date"] = start.isoformat()
        if end:
            arguments["end_date"] = end.isoformat()
        data = call("calculate_total", arguments)
        window = ""
        if start and end:
            window = f" from {start.isoformat()} to {end.isoformat()}"
        answer = (
            f"You spent {_money(data['total'])} on {target}{window} "
            f"across {data['count']} transactions."
        )
        return {"answer": answer, "trace": trace, "mode": "rules"}

    arguments = {}
    if category:
        arguments["category"] = category
    if merchant:
        arguments["merchant"] = merchant
    if start:
        arguments["start_date"] = start.isoformat()
    if end:
        arguments["end_date"] = end.isoformat()
    if _wants_largest(question):
        arguments["sort_by"] = "amount"
        arguments["sort_order"] = "desc"
        arguments["limit"] = 5

    if arguments:
        data = call("filter_transactions", arguments)
        rows = data["transactions"]
        if not rows:
            return {
                "answer": "I could not find any transactions matching that question.",
                "trace": trace,
                "mode": "rules",
            }
        preview = "\n".join(
            f"- {row['date']}  {row['merchant']}  {_money(row['amount'])}  ({row['category']})"
            for row in rows[:8]
        )
        extra = f" Showing {len(rows)} of {data['matched']}." if data["matched"] > len(rows) else ""
        answer = f"Here are the matching transactions.{extra}\n{preview}"
        return {"answer": answer, "trace": trace, "mode": "rules"}

    data = call("get_transactions", {"limit": 8})
    preview = "\n".join(
        f"- {row['date']}  {row['merchant']}  {_money(row['amount'])}  ({row['category']})"
        for row in data["transactions"]
    )
    answer = f"Here are your latest transactions:\n{preview}"
    return {"answer": answer, "trace": trace, "mode": "rules"}
