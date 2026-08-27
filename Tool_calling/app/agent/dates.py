"""Turn phrases like 'last month' into inclusive YYYY-MM-DD ranges."""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def resolve_period(text: str, today: date) -> tuple[date | None, date | None]:
    q = text.lower()

    if "last month" in q:
        year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        return month_bounds(year, month)
    if "this month" in q:
        return month_bounds(today.year, today.month)
    if "last week" in q:
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return start, end
    if "this week" in q:
        start = today - timedelta(days=today.weekday())
        return start, today
    if "yesterday" in q:
        day = today - timedelta(days=1)
        return day, day
    if "today" in q:
        return today, today
    if "last 30 days" in q or "past 30 days" in q:
        return today - timedelta(days=29), today
    if "this year" in q:
        return date(today.year, 1, 1), today
    if "last year" in q:
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)

    for name, month in MONTHS.items():
        if re.search(rf"\b{name}\b", q):
            year_match = re.search(r"\b(20\d{2})\b", q)
            year = int(year_match.group(1)) if year_match else today.year
            if month > today.month and year == today.year and not year_match:
                year -= 1
            return month_bounds(year, month)

    iso = re.search(r"\b(20\d{2})-(\d{2})(?:-(\d{2}))?\b", q)
    if iso:
        year, month, day = int(iso.group(1)), int(iso.group(2)), iso.group(3)
        if day:
            parsed = date(year, month, int(day))
            return parsed, parsed
        return month_bounds(year, month)

    return None, None
