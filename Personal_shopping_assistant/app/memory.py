"""Read/write the three memory kinds and search the product catalog."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Message, Product, ShoppingTask, UserProfile

SIZE_KEY_BY_CATEGORY = {
    "running shoes": "shoes",
    "sneakers": "shoes",
    "formal shoes": "shoes",
    "sandals": "shoes",
    "dress": "clothing",
    "shirt": "clothing",
    "t-shirt": "clothing",
    "jeans": "clothing",
    "kurta": "clothing",
}


def _uniq(values: list[str] | None) -> list[str]:
    seen: list[str] = []
    for item in values or []:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if any(existing.lower() == key for existing in seen):
            continue
        seen.append(text)
    return seen


def ensure_user(db: Session, user_id: str, display_name: str = "") -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None:
        profile = UserProfile(
            user_id=user_id,
            display_name=display_name or user_id,
            preferred_brands=[],
            categories=[],
            colours=[],
            sizes={},
        )
        db.add(profile)
        db.flush()
    task = db.get(ShoppingTask, user_id)
    if task is None:
        task = ShoppingTask(user_id=user_id, shown_product_ids=[], status="open")
        db.add(task)
        db.flush()
    return profile


def serialize_profile(profile: UserProfile) -> dict[str, Any]:
    return {
        "user_id": profile.user_id,
        "display_name": profile.display_name,
        "preferred_brands": list(profile.preferred_brands or []),
        "categories": list(profile.categories or []),
        "colours": list(profile.colours or []),
        "budget_min": profile.budget_min,
        "budget_max": profile.budget_max,
        "sizes": dict(profile.sizes or {}),
        "audience": profile.audience,
    }


def serialize_task(task: ShoppingTask | None) -> dict[str, Any]:
    if task is None:
        return {
            "category": None,
            "budget_min": None,
            "budget_max": None,
            "shown_product_ids": [],
            "status": "open",
        }
    return {
        "category": task.category,
        "budget_min": task.budget_min,
        "budget_max": task.budget_max,
        "shown_product_ids": list(task.shown_product_ids or []),
        "status": task.status,
    }


def snapshot(db: Session, user_id: str) -> dict[str, Any]:
    profile = ensure_user(db, user_id)
    task = db.get(ShoppingTask, user_id)
    return {"profile": serialize_profile(profile), "task": serialize_task(task)}


def update_profile(
    db: Session,
    user_id: str,
    brands: list[str] | None = None,
    categories: list[str] | None = None,
    colours: list[str] | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    sizes: dict[str, Any] | None = None,
    audience: str | None = None,
    replace_brands: bool = False,
    replace_categories: bool = False,
    replace_colours: bool = False,
    remove_brands: list[str] | None = None,
    remove_colours: list[str] | None = None,
    remove_categories: list[str] | None = None,
    clear_budget: bool = False,
) -> dict[str, Any]:
    """Merge or overwrite long-term slots. Budget/audience/size keys overwrite."""
    profile = ensure_user(db, user_id)
    task = db.get(ShoppingTask, user_id)
    assert task is not None

    if brands is not None:
        profile.preferred_brands = (
            _uniq(brands) if replace_brands else _uniq([*(profile.preferred_brands or []), *brands])
        )
    if categories is not None:
        profile.categories = (
            _uniq(categories)
            if replace_categories
            else _uniq([*(profile.categories or []), *categories])
        )
        if categories:
            new_category = categories[-1]
            if task.category and task.category.lower() != new_category.lower():
                task.shown_product_ids = []
            task.category = new_category
    if colours is not None:
        profile.colours = (
            _uniq(colours) if replace_colours else _uniq([*(profile.colours or []), *colours])
        )

    if remove_brands:
        drop = {item.lower() for item in remove_brands}
        profile.preferred_brands = [b for b in (profile.preferred_brands or []) if b.lower() not in drop]
    if remove_colours:
        drop = {item.lower() for item in remove_colours}
        profile.colours = [c for c in (profile.colours or []) if c.lower() not in drop]
    if remove_categories:
        drop = {item.lower() for item in remove_categories}
        profile.categories = [c for c in (profile.categories or []) if c.lower() not in drop]

    if clear_budget:
        profile.budget_min = None
        profile.budget_max = None
        task.budget_min = None
        task.budget_max = None
    if budget_min is not None:
        profile.budget_min = int(budget_min)
        task.budget_min = int(budget_min)
    if budget_max is not None:
        profile.budget_max = int(budget_max)
        task.budget_max = int(budget_max)

    if sizes:
        merged = dict(profile.sizes or {})
        for key, value in sizes.items():
            if value is None or value == "":
                merged.pop(str(key), None)
            else:
                merged[str(key)] = str(value)
        profile.sizes = merged
    if audience:
        profile.audience = audience.strip().lower()

    db.add(profile)
    db.add(task)
    db.flush()
    return snapshot(db, user_id)


def _size_for_category(profile: UserProfile, category: str | None) -> str | None:
    if not category:
        return None
    key = SIZE_KEY_BY_CATEGORY.get(category.lower(), "clothing")
    sizes = profile.sizes or {}
    value = sizes.get(key) or sizes.get("shoes") or sizes.get("clothing")
    return str(value) if value is not None else None


def serialize_product(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "colour": product.colour,
        "price": product.price,
        "sizes": list(product.sizes or []),
        "audience": product.audience,
    }


def search_products(
    db: Session,
    user_id: str,
    category: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    colour: str | None = None,
    brand: str | None = None,
    size: str | None = None,
    audience: str | None = None,
    limit: int | None = None,
    record_shown: bool = True,
) -> dict[str, Any]:
    """Filter the catalog using live memory, then optionally mark results as shown."""
    profile = ensure_user(db, user_id)
    task = db.get(ShoppingTask, user_id)
    assert task is not None

    hunt_category = category or task.category or (profile.categories[-1] if profile.categories else None)
    hunt_min = budget_min if budget_min is not None else (
        task.budget_min if task.budget_min is not None else profile.budget_min
    )
    hunt_max = budget_max if budget_max is not None else (
        task.budget_max if task.budget_max is not None else profile.budget_max
    )
    hunt_audience = (audience or profile.audience or "").strip().lower() or None
    hunt_size = size or _size_for_category(profile, hunt_category)
    colour_hard = colour
    colour_boost = None if colour else ((profile.colours or [None])[0] if profile.colours else None)
    brand_pref = brand
    preferred_brands = [b.lower() for b in (profile.preferred_brands or [])]
    shown = set(task.shown_product_ids or [])

    if hunt_category:
        task.category = hunt_category
    if hunt_min is not None:
        task.budget_min = hunt_min
    if hunt_max is not None:
        task.budget_max = hunt_max

    query = select(Product)
    if hunt_category:
        query = query.where(Product.category.ilike(f"%{hunt_category}%"))
    if hunt_min is not None:
        query = query.where(Product.price >= int(hunt_min))
    if hunt_max is not None:
        query = query.where(Product.price <= int(hunt_max))
    if hunt_audience and hunt_audience != "unisex":
        query = query.where(Product.audience.in_([hunt_audience, "unisex"]))
    if brand_pref:
        query = query.where(Product.brand.ilike(f"%{brand_pref}%"))
    if colour_hard:
        query = query.where(Product.colour.ilike(f"%{colour_hard}%"))
    if shown:
        query = query.where(Product.id.notin_(shown))

    rows = list(db.scalars(query.order_by(Product.price.asc())).all())

    if hunt_size:
        sized = [row for row in rows if hunt_size in [str(s) for s in (row.sizes or [])]]
        if sized:
            rows = sized

    if colour_boost:
        boosted = [row for row in rows if colour_boost.lower() in row.colour.lower()]
        rest = [row for row in rows if colour_boost.lower() not in row.colour.lower()]
        rows = boosted + rest

    if preferred_brands and not brand_pref:
        preferred = [row for row in rows if row.brand.lower() in preferred_brands]
        others = [row for row in rows if row.brand.lower() not in preferred_brands]
        rows = preferred + others

    cap = max(1, min(int(limit or settings.search_limit), 8))
    picked = rows[:cap]
    payload = [serialize_product(row) for row in picked]

    if record_shown and payload:
        merged = _uniq([*(task.shown_product_ids or []), *[item["id"] for item in payload]])
        task.shown_product_ids = merged
        db.add(task)
        db.flush()

    return {
        "filters": {
            "category": hunt_category,
            "budget_min": hunt_min,
            "budget_max": hunt_max,
            "colour": colour_hard or colour_boost,
            "size": hunt_size,
            "audience": hunt_audience,
            "brand": brand_pref,
            "excluded_ids": sorted(shown),
        },
        "count": len(payload),
        "products": payload,
        "shown_product_ids": list(task.shown_product_ids or []),
        "note": None
        if payload
        else "No new catalog items match the current memory. Try a wider budget or a new category.",
    }


def history(db: Session, user_id: str, limit: int | None = None) -> list[dict[str, str]]:
    ensure_user(db, user_id)
    cap = limit or settings.history_limit
    rows = list(
        db.scalars(
            select(Message)
            .where(Message.user_id == user_id)
            .order_by(Message.id.desc())
            .limit(cap)
        ).all()
    )
    rows.reverse()
    return [{"role": row.role, "content": row.content} for row in rows]


def add_message(db: Session, user_id: str, role: str, content: str) -> None:
    ensure_user(db, user_id)
    db.add(Message(user_id=user_id, role=role, content=content))
    db.flush()


def reset_session(db: Session, user_id: str, clear_profile: bool = False) -> dict[str, Any]:
    """Drop conversation + shown items. Optionally wipe long-term prefs (stale-memory demo)."""
    profile = ensure_user(db, user_id)
    task = db.get(ShoppingTask, user_id)
    assert task is not None
    db.execute(delete(Message).where(Message.user_id == user_id))
    task.shown_product_ids = []
    task.status = "open"
    if clear_profile:
        profile.preferred_brands = []
        profile.categories = []
        profile.colours = []
        profile.budget_min = None
        profile.budget_max = None
        profile.sizes = {}
        profile.audience = None
        task.category = None
        task.budget_min = None
        task.budget_max = None
    db.add(profile)
    db.add(task)
    db.flush()
    return snapshot(db, user_id)


def list_users(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(select(UserProfile).order_by(UserProfile.user_id)).all()
    return [
        {"user_id": row.user_id, "display_name": row.display_name, "profile": serialize_profile(row)}
        for row in rows
    ]
