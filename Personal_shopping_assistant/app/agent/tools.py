"""LangChain tools bound to one request's database session and user."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session

from app import memory as store


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def build_tools(db: Session, user_id: str) -> list[StructuredTool]:
    def get_memory() -> str:
        """Return this shopper's saved profile and current shopping task."""
        return _dumps(store.snapshot(db, user_id))

    def update_profile(
        brands: list[str] | None = None,
        categories: list[str] | None = None,
        colours: list[str] | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        sizes: dict[str, str] | None = None,
        audience: str | None = None,
        replace_brands: bool = False,
        replace_categories: bool = False,
        replace_colours: bool = False,
        remove_brands: list[str] | None = None,
        remove_colours: list[str] | None = None,
        remove_categories: list[str] | None = None,
        clear_budget: bool = False,
    ) -> str:
        """Save or overwrite long-term shopping preferences for this user.

        Pass only fields the user just stated. A new budget_max replaces the old one.
        Use remove_brands when they no longer want a brand. Set replace_* to replace
        a whole list instead of merging.
        """
        return _dumps(
            store.update_profile(
                db,
                user_id,
                brands=brands,
                categories=categories,
                colours=colours,
                budget_min=budget_min,
                budget_max=budget_max,
                sizes=sizes,
                audience=audience,
                replace_brands=replace_brands,
                replace_categories=replace_categories,
                replace_colours=replace_colours,
                remove_brands=remove_brands,
                remove_colours=remove_colours,
                remove_categories=remove_categories,
                clear_budget=clear_budget,
            )
        )

    def search_products(
        category: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        colour: str | None = None,
        brand: str | None = None,
        size: str | None = None,
        audience: str | None = None,
        limit: int | None = None,
    ) -> str:
        """Search the product catalog using saved memory plus any extra filters.

        Already-shown product ids are excluded automatically and the new results
        are recorded on the current shopping task.
        """
        return _dumps(
            store.search_products(
                db,
                user_id,
                category=category,
                budget_min=budget_min,
                budget_max=budget_max,
                colour=colour,
                brand=brand,
                size=size,
                audience=audience,
                limit=limit,
            )
        )

    return [
        StructuredTool.from_function(func=get_memory, name="get_memory"),
        StructuredTool.from_function(func=update_profile, name="update_profile"),
        StructuredTool.from_function(func=search_products, name="search_products"),
    ]
