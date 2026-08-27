"""
The four tools the agent is allowed to call.

Each function is an ordinary Python callable. The LLM never talks to Postgres
directly — it only emits a tool name + arguments. `executor.py` looks the
function up here and runs it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Transaction


def _serialize(row: Transaction) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": row.posted_on.isoformat(),
        "merchant": row.merchant,
        "category": row.category,
        "amount": float(row.amount),
        "description": row.description,
        "payment_method": row.payment_method,
    }


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def get_transactions(db: Session, limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """Return the most recent transactions, newest first."""
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    total = db.scalar(select(func.count()).select_from(Transaction)) or 0
    rows = db.scalars(
        select(Transaction)
        .order_by(Transaction.posted_on.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {"count": total, "returned": len(rows), "transactions": [_serialize(r) for r in rows]}


def filter_transactions(
    db: Session,
    category: str | None = None,
    merchant: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    limit: int = 50,
) -> dict[str, Any]:
    """Return transactions matching optional filters."""
    query = select(Transaction)
    count_query = select(func.count()).select_from(Transaction)

    def apply_filters(q):
        if category:
            q = q.where(Transaction.category.ilike(f"%{category}%"))
        if merchant:
            q = q.where(Transaction.merchant.ilike(f"%{merchant}%"))
        start = _parse_date(start_date)
        end = _parse_date(end_date)
        if start:
            q = q.where(Transaction.posted_on >= start)
        if end:
            q = q.where(Transaction.posted_on <= end)
        if min_amount is not None:
            q = q.where(Transaction.amount >= Decimal(str(min_amount)))
        if max_amount is not None:
            q = q.where(Transaction.amount <= Decimal(str(max_amount)))
        return q

    query = apply_filters(query)
    count_query = apply_filters(count_query)
    total = db.scalar(count_query) or 0

    sort_column = Transaction.amount if sort_by == "amount" else Transaction.posted_on
    order = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    limit = max(1, min(int(limit), 100))
    rows = db.scalars(query.order_by(order, Transaction.id.desc()).limit(limit)).all()
    return {
        "matched": total,
        "returned": len(rows),
        "transactions": [_serialize(r) for r in rows],
    }


def calculate_total(
    db: Session,
    category: str | None = None,
    merchant: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Sum amounts for the given filters. This is the tool for 'how much' questions."""
    query = select(func.coalesce(func.sum(Transaction.amount), 0), func.
                   count()).select_from(
        Transaction
    )
    if category:
        query = query.where(Transaction.category.ilike(f"%{category}%"))
    if merchant:
        query = query.where(Transaction.merchant.ilike(f"%{merchant}%"))
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start:
        query = query.where(Transaction.posted_on >= start)
    if end:
        query = query.where(Transaction.posted_on <= end)

    total, count = db.execute(query).one()
    return {
        "total": float(total),
        "count": int(count),
        "currency": "USD",
        "filters": {
            "category": category,
            "merchant": merchant,
            "start_date": start_date,
            "end_date": end_date,
        },
    }


def get_categories(db: Session) -> dict[str, Any]:
    """List spending categories with counts and totals. Use this to resolve names like 'food'."""
    rows = db.execute(
        select(
            Transaction.category,
            func.count(),
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()
    return {
        "categories": [
            {
                "name": name,
                "transaction_count": int(count),
                "total": float(total),
            }
            for name, count, total in rows
        ]
    }
