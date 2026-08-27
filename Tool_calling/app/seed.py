"""Deterministic synthetic ledger used to answer questions without real bank data."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Transaction

CATEGORIES: dict[str, list[str]] = {
    "Food & Dining": [
        "Starbucks",
        "Chipotle",
        "McDonald's",
        "Sweetgreen",
        "Local Bistro",
        "Pizza Hut",
        "Uber Eats",
        "Dunkin'",
    ],
    "Groceries": ["Whole Foods", "Trader Joe's", "Walmart", "Costco", "Kroger"],
    "Transport": ["Uber", "Lyft", "Shell", "Chevron", "Metro Card", "City Parking"],
    "Shopping": ["Amazon", "Target", "Nike", "Zara", "Best Buy", "IKEA"],
    "Entertainment": ["AMC Theaters", "Steam", "Concert Tickets", "Spotify Concert"],
    "Bills & Utilities": [
        "Electric Co",
        "City Water",
        "Fiber Internet",
        "Mobile Plan",
        "Rent",
    ],
    "Healthcare": ["CVS Pharmacy", "City Dental", "Urgent Care", "Gym Membership"],
    "Travel": ["Delta Airlines", "Airbnb", "Hilton", "Uber Airport"],
    "Subscriptions": ["Netflix", "Spotify", "iCloud", "The New York Times", "Adobe CC"],
}

PAYMENT_METHODS = ["Visa ****4412", "Mastercard ****8821", "Debit ****1109"]

# Weighted so food/groceries happen often, travel/rent less often.
CATEGORY_WEIGHTS = {
    "Food & Dining": 22,
    "Groceries": 14,
    "Transport": 14,
    "Shopping": 12,
    "Entertainment": 8,
    "Bills & Utilities": 8,
    "Healthcare": 6,
    "Travel": 4,
    "Subscriptions": 8,
}


def _amount_for(category: str, merchant: str, rng: random.Random) -> Decimal:
    ranges = {
        "Food & Dining": (8, 48),
        "Groceries": (28, 160),
        "Transport": (6, 42),
        "Shopping": (18, 220),
        "Entertainment": (12, 90),
        "Bills & Utilities": (40, 180),
        "Healthcare": (15, 260),
        "Travel": (80, 650),
        "Subscriptions": (6, 55),
    }
    if merchant == "Rent":
        return Decimal("1850.00")
    lo, hi = ranges[category]
    cents = rng.randint(lo * 100, hi * 100)
    return Decimal(cents) / Decimal(100)


def seed_if_empty(db: Session, today: date | None = None) -> int:
    existing = db.scalar(select(func.count()).select_from(Transaction))
    if existing:
        return 0

    today = today or date.today()
    start = date(today.year, today.month, 1) - timedelta(days=180)
    rng = random.Random(42)

    names = list(CATEGORIES)
    weights = [CATEGORY_WEIGHTS[name] for name in names]
    rows: list[Transaction] = []
    day = start

    while day <= today:
        count = 1 if rng.random() < 0.35 else rng.randint(2, 5)
        if day.weekday() >= 5:
            count += rng.randint(0, 2)
        used = set()
        for _ in range(count):
            category = rng.choices(names, weights=weights, k=1)[0]
            merchant = rng.choice(CATEGORIES[category])
            key = (category, merchant)
            if category == "Bills & Utilities" and merchant == "Rent":
                if day.day > 5 or key in used:
                    continue
            if category == "Subscriptions" and day.day not in {1, 2, 3, 14, 15}:
                if rng.random() > 0.15:
                    continue
            used.add(key)
            amount = _amount_for(category, merchant, rng)
            rows.append(
                Transaction(
                    posted_on=day,
                    merchant=merchant,
                    category=category,
                    amount=amount,
                    description=f"{merchant} purchase",
                    payment_method=rng.choice(PAYMENT_METHODS),
                )
            )
        day += timedelta(days=1)

    db.add_all(rows)
    db.commit()
    return len(rows)
