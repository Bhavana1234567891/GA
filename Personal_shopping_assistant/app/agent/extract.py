"""Pull structured shopping slots out of a plain English sentence."""

from __future__ import annotations

import re
from typing import Any

CATEGORY_ALIASES: list[tuple[str, str]] = [
    (r"\brunning shoes?\b", "running shoes"),
    (r"\b(?:trainers?|sneakers?)\b", "running shoes"),
    (r"\bformal shoes?\b", "formal shoes"),
    (r"\bsandals?\b", "sandals"),
    (r"\bdress(?:es)?\b|\bgowns?\b", "dress"),
    (r"\bt-?shirts?\b|\btees?\b", "t-shirt"),
    (r"\bshirts?\b", "shirt"),
    (r"\bjeans\b", "jeans"),
    (r"\bkurtas?\b", "kurta"),
]

BRANDS = [
    "nike",
    "adidas",
    "asics",
    "puma",
    "hoka",
    "skechers",
    "campus",
    "kalenji",
    "zara",
    "h&m",
    "forever 21",
    "westside",
    "mango",
    "uniqlo",
    "levi's",
    "levis",
    "manyavar",
    "global desi",
]

COLOURS = [
    "black",
    "navy",
    "white",
    "red",
    "blue",
    "pink",
    "beige",
    "grey",
    "gray",
    "green",
    "brown",
    "maroon",
    "white",
]

NEW_OPTIONS = re.compile(
    r"\b(new options?|show me (some )?(more|options|others?)|something else|more options)\b",
    re.I,
)
PROFILE_QUERY = re.compile(
    r"\b(what do you remember|my (budget|size|preferences?|profile)|what are my)\b",
    re.I,
)
REMOVE_BRAND = re.compile(
    r"(?:don'?t (?:buy|wear|like)|forget|not|no more|anymore)\s+(?:brand\s+)?([A-Za-z0-9&' -]+)",
    re.I,
)
BUDGET_NOW = re.compile(
    r"(?:budget (?:is )?(?:now )?|can (?:go|spend) (?:up to )?|raise.{0,12}budget.{0,8})\s*₹?\s*([\d,.]+)\s*(k)?",
    re.I,
)
BELOW = re.compile(
    r"(?:below|under|less than|max(?:imum)?|upto|up to|<)\s*₹?\s*([\d,.]+)\s*(k)?",
    re.I,
)
RANGE = re.compile(
    r"₹?\s*([\d,.]+)\s*(k)?\s*(?:-|–|to)\s*₹?\s*([\d,.]+)\s*(k)?",
    re.I,
)
INR = re.compile(r"₹\s*([\d,.]+)\s*(k)?", re.I)
SIZE = re.compile(r"\bsize\s*([0-9]{1,2}|xs|s|m|l|xl)\b", re.I)
AUDIENCE = re.compile(r"\b(for |)\b(women|woman|ladies|men|man|male|female|unisex)\b", re.I)


def _to_int(num: str, k_flag: str | None) -> int:
    cleaned = num.replace(",", "").strip()
    value = float(cleaned)
    if k_flag:
        value *= 1000
    elif value < 100 and "k" not in num.lower():
        # "1-2" already handled by k flag; bare 10 usually means 10 rupees — leave it
        pass
    return int(value)


def _normalize_k(num: str, k_flag: str | None) -> int:
    cleaned = num.replace(",", "").strip().lower()
    if cleaned.endswith("k"):
        return int(float(cleaned[:-1]) * 1000)
    value = float(cleaned)
    if k_flag:
        return int(value * 1000)
    return int(value)


def extract_preferences(text: str) -> dict[str, Any]:
    found: dict[str, Any] = {}
    lower = text.lower()

    for pattern, canonical in CATEGORY_ALIASES:
        if re.search(pattern, lower):
            found["categories"] = [canonical]
            break

    brands = [brand.title() if brand != "h&m" else "H&M" for brand in BRANDS if re.search(rf"\b{re.escape(brand)}\b", lower)]
    if "h&m" in lower and "H&M" not in brands:
        brands.append("H&M")
    if brands:
        found["brands"] = brands

    colours = []
    for colour in COLOURS:
        if re.search(rf"\b{colour}\b", lower):
            colours.append("grey" if colour == "gray" else colour)
    if colours:
        found["colours"] = list(dict.fromkeys(colours))

    range_match = RANGE.search(text)
    below_match = BELOW.search(text)
    now_match = BUDGET_NOW.search(text)
    if range_match:
        found["budget_min"] = _normalize_k(range_match.group(1), range_match.group(2))
        found["budget_max"] = _normalize_k(range_match.group(3), range_match.group(4))
    elif below_match:
        found["budget_max"] = _normalize_k(below_match.group(1), below_match.group(2))
    elif now_match:
        found["budget_max"] = _normalize_k(now_match.group(1), now_match.group(2))
    else:
        inr = INR.search(text)
        if inr and any(word in lower for word in ("budget", "price", "under", "below", "range")):
            found["budget_max"] = _normalize_k(inr.group(1), inr.group(2))

    size_match = SIZE.search(text)
    if size_match:
        token = size_match.group(1).upper()
        key = "shoes" if token.isdigit() else "clothing"
        if found.get("categories") == ["running shoes"]:
            key = "shoes"
        if found.get("categories") in (["dress"], ["shirt"], ["t-shirt"], ["kurta"]):
            key = "clothing"
        found["sizes"] = {key: token if not token.isdigit() else token}

    audience_match = AUDIENCE.search(lower)
    if audience_match:
        word = audience_match.group(2)
        if word in {"women", "woman", "ladies", "female"}:
            found["audience"] = "women"
        elif word in {"men", "man", "male"}:
            found["audience"] = "men"
        else:
            found["audience"] = "unisex"

    remove = []
    if re.search(r"don'?t (?:buy|wear|like)|forget|no more|anymore", lower):
        for brand in BRANDS:
            if brand in lower:
                remove.append("H&M" if brand == "h&m" else brand.title())
        if remove:
            found["remove_brands"] = list(dict.fromkeys(remove))
            found.pop("brands", None)

    found["wants_new_options"] = bool(NEW_OPTIONS.search(text))
    found["wants_profile"] = bool(PROFILE_QUERY.search(text))
    found["has_slots"] = any(
        key in found
        for key in (
            "categories",
            "brands",
            "colours",
            "budget_min",
            "budget_max",
            "sizes",
            "audience",
            "remove_brands",
        )
    )
    return found
