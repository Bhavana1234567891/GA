"""Synthetic catalog, shopper profiles, and scripted interactions."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product, ShoppingTask, UserProfile

SHOE_SIZES = ["7", "8", "9", "10", "11"]
CLOTHING_SIZES = ["XS", "S", "M", "L", "XL"]

PRODUCTS: list[dict] = [
    # Running shoes under ₹10,000 — enough for two "new options" rounds
    {"id": "P01", "name": "Nike Revolution 7", "brand": "Nike", "category": "running shoes", "colour": "black", "price": 7495, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P02", "name": "Asics Gel-Excite 10", "brand": "Asics", "category": "running shoes", "colour": "navy", "price": 7999, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P03", "name": "Puma Softride Symmetry", "brand": "Puma", "category": "running shoes", "colour": "grey", "price": 5499, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P04", "name": "Adidas Runfalcon 5", "brand": "Adidas", "category": "running shoes", "colour": "black", "price": 6999, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P05", "name": "Skechers Go Run Consistent", "brand": "Skechers", "category": "running shoes", "colour": "navy", "price": 8499, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P06", "name": "Campus North Plus", "brand": "Campus", "category": "running shoes", "colour": "blue", "price": 2499, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P07", "name": "Nike Downshifter 13", "brand": "Nike", "category": "running shoes", "colour": "white", "price": 6295, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P08", "name": "Asics Patriot 13", "brand": "Asics", "category": "running shoes", "colour": "black", "price": 5599, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P09", "name": "Decathlon Kalenji Run 100", "brand": "Kalenji", "category": "running shoes", "colour": "red", "price": 1999, "sizes": SHOE_SIZES, "audience": "unisex"},
    # Running shoes above ₹10,000 — appear only after budget is raised
    {"id": "P10", "name": "Nike Pegasus 41", "brand": "Nike", "category": "running shoes", "colour": "black", "price": 11895, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P11", "name": "Adidas Adizero SL", "brand": "Adidas", "category": "running shoes", "colour": "blue", "price": 12999, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P12", "name": "Asics Gel-Kayano 31", "brand": "Asics", "category": "running shoes", "colour": "navy", "price": 15999, "sizes": SHOE_SIZES, "audience": "unisex"},
    {"id": "P13", "name": "Hoka Clifton 9", "brand": "Hoka", "category": "running shoes", "colour": "white", "price": 13999, "sizes": SHOE_SIZES, "audience": "unisex"},
    # Women's dresses in the 1k–2k band and above it
    {"id": "D01", "name": "Zara Linen Midi Dress", "brand": "Zara", "category": "dress", "colour": "beige", "price": 1890, "sizes": CLOTHING_SIZES, "audience": "women"},
    {"id": "D02", "name": "H&M Floral A-Line", "brand": "H&M", "category": "dress", "colour": "pink", "price": 1499, "sizes": CLOTHING_SIZES, "audience": "women"},
    {"id": "D03", "name": "Forever 21 Shirt Dress", "brand": "Forever 21", "category": "dress", "colour": "blue", "price": 1299, "sizes": CLOTHING_SIZES, "audience": "women"},
    {"id": "D04", "name": "Westside Cotton Day Dress", "brand": "Westside", "category": "dress", "colour": "white", "price": 1699, "sizes": CLOTHING_SIZES, "audience": "women"},
    {"id": "D05", "name": "AND Wrap Dress", "brand": "AND", "category": "dress", "colour": "black", "price": 1999, "sizes": CLOTHING_SIZES, "audience": "women"},
    {"id": "D06", "name": "Global Desi Printed Dress", "brand": "Global Desi", "category": "dress", "colour": "maroon", "price": 1799, "sizes": CLOTHING_SIZES, "audience": "women"},
    {"id": "D07", "name": "Zara Satin Slip Dress", "brand": "Zara", "category": "dress", "colour": "black", "price": 3290, "sizes": CLOTHING_SIZES, "audience": "women"},
    {"id": "D08", "name": "Mango Structured Midi", "brand": "Mango", "category": "dress", "colour": "navy", "price": 4590, "sizes": CLOTHING_SIZES, "audience": "women"},
    # Other categories so memory filters are visible
    {"id": "S01", "name": "Uniqlo Oxford Shirt", "brand": "Uniqlo", "category": "shirt", "colour": "white", "price": 1990, "sizes": CLOTHING_SIZES, "audience": "men"},
    {"id": "S02", "name": "Levi's Slim Shirt", "brand": "Levi's", "category": "shirt", "colour": "blue", "price": 2499, "sizes": CLOTHING_SIZES, "audience": "men"},
    {"id": "J01", "name": "Levi's 511 Jeans", "brand": "Levi's", "category": "jeans", "colour": "navy", "price": 3999, "sizes": ["30", "32", "34", "36"], "audience": "men"},
    {"id": "K01", "name": "Manyavar Silk Kurta", "brand": "Manyavar", "category": "kurta", "colour": "maroon", "price": 3499, "sizes": CLOTHING_SIZES, "audience": "men"},
    {"id": "T01", "name": "H&M Oversized Tee", "brand": "H&M", "category": "t-shirt", "colour": "black", "price": 799, "sizes": CLOTHING_SIZES, "audience": "unisex"},
]

USERS: list[dict] = [
    {
        "user_id": "fresh",
        "display_name": "New shopper",
        "preferred_brands": [],
        "categories": [],
        "colours": [],
        "budget_min": None,
        "budget_max": None,
        "sizes": {},
        "audience": None,
    },
    {
        "user_id": "riya",
        "display_name": "Riya (pre-filled runner)",
        "preferred_brands": ["Nike", "Asics"],
        "categories": ["running shoes"],
        "colours": ["black", "navy"],
        "budget_min": None,
        "budget_max": 10000,
        "sizes": {"shoes": "9"},
        "audience": "unisex",
    },
    {
        "user_id": "meera",
        "display_name": "Meera (pre-filled dresses)",
        "preferred_brands": ["Zara", "H&M"],
        "categories": ["dress"],
        "colours": ["beige", "pink"],
        "budget_min": 1000,
        "budget_max": 2000,
        "sizes": {"clothing": "M"},
        "audience": "women",
    },
]


def seed_if_empty(db: Session) -> dict[str, int]:
    product_count = db.scalar(select(func.count()).select_from(Product)) or 0
    user_count = db.scalar(select(func.count()).select_from(UserProfile)) or 0
    added_products = 0
    added_users = 0

    if product_count == 0:
        for row in PRODUCTS:
            db.add(Product(**row))
            added_products += 1

    if user_count == 0:
        for row in USERS:
            db.add(UserProfile(**row))
            db.add(
                ShoppingTask(
                    user_id=row["user_id"],
                    category=row["categories"][-1] if row["categories"] else None,
                    budget_min=row["budget_min"],
                    budget_max=row["budget_max"],
                    shown_product_ids=[],
                    status="open",
                )
            )
            added_users += 1

    if added_products or added_users:
        db.commit()
    return {"products": added_products, "users": added_users}
