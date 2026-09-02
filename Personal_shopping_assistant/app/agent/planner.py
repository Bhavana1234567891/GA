"""Rules-mode agent: same tools as LangChain, no paid API required."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app import memory as store
from app.agent.extract import extract_preferences


def _inr(amount: int) -> str:
    return f"₹{amount:,}"


def _format_products(products: list[dict[str, Any]]) -> str:
    lines = []
    for item in products:
        sizes = ", ".join(str(s) for s in item.get("sizes") or [])
        lines.append(
            f"- {item['name']} ({item['brand']}) — {item['colour']} {item['category']}, "
            f"{_inr(item['price'])}, sizes {sizes} [{item['id']}]"
        )
    return "\n".join(lines)


def run_rules_agent(message: str, db: Session, user_id: str) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    extracted = extract_preferences(message)

    def call(name: str, **arguments: Any) -> dict[str, Any]:
        cleaned = {key: value for key, value in arguments.items() if value is not None}
        trace.append({"type": "tool_call", "name": name, "arguments": cleaned})
        if name == "update_profile":
            result = store.update_profile(db, user_id, **cleaned)
        elif name == "search_products":
            result = store.search_products(db, user_id, **cleaned)
        else:
            result = store.snapshot(db, user_id)
        trace.append({"type": "tool_result", "name": name, "result": result})
        return result

    snap = store.snapshot(db, user_id)
    known_category = (snap["task"] or {}).get("category") or (
        (snap["profile"] or {}).get("categories") or [None]
    )[-1]

    if extracted.get("wants_profile") and not extracted.get("has_slots"):
        snap = call("get_memory")
        profile = snap["profile"]
        budget = (
            f"{_inr(profile['budget_min'])}–{_inr(profile['budget_max'])}"
            if profile.get("budget_min") is not None and profile.get("budget_max") is not None
            else (_inr(profile["budget_max"]) if profile.get("budget_max") is not None else "not set")
        )
        answer = (
            f"Saved memory for {profile['display_name']}: "
            f"categories {profile['categories'] or '—'}, "
            f"brands {profile['preferred_brands'] or '—'}, "
            f"colours {profile['colours'] or '—'}, "
            f"budget {budget}, sizes {profile['sizes'] or '—'}."
        )
        return {"answer": answer, "trace": trace, "mode": "rules"}

    if extracted.get("has_slots"):
        update_args = {
            "brands": extracted.get("brands"),
            "categories": extracted.get("categories"),
            "colours": extracted.get("colours"),
            "budget_min": extracted.get("budget_min"),
            "budget_max": extracted.get("budget_max"),
            "sizes": extracted.get("sizes"),
            "audience": extracted.get("audience"),
            "remove_brands": extracted.get("remove_brands"),
        }
        call("update_profile", **update_args)
        known_category = extracted.get("categories", [known_category])[-1] if extracted.get("categories") else known_category

    if not known_category and not extracted.get("categories"):
        return {
            "answer": "Tell me what you usually buy — category, budget, size, colour, or brand — and I will remember it.",
            "trace": trace,
            "mode": "rules",
        }

    search = call("search_products")
    products = search.get("products") or []
    filters = search.get("filters") or {}
    if not products:
        answer = search.get("note") or "I could not find matching products with the saved memory."
        return {"answer": answer, "trace": trace, "mode": "rules"}

    bits = []
    if filters.get("category"):
        bits.append(filters["category"])
    if filters.get("budget_max") is not None:
        if filters.get("budget_min") is not None:
            bits.append(f"{_inr(filters['budget_min'])}–{_inr(filters['budget_max'])}")
        else:
            bits.append(f"below {_inr(filters['budget_max'])}")
    if extracted.get("wants_new_options"):
        lead = "Here are some new options"
    else:
        lead = "Here are some options"
    constraint = f" for {' '.join(bits)}" if bits else ""
    answer = f"{lead}{constraint}, using your saved preferences:\n{_format_products(products)}"
    return {"answer": answer, "trace": trace, "mode": "rules"}
