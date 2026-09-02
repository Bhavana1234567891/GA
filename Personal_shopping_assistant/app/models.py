from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    brand: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    colour: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    sizes: Mapped[list] = mapped_column(JSON, default=list)
    audience: Mapped[str] = mapped_column(String(20), default="unisex")


class UserProfile(Base):
    """Long-term shopper memory — one row per user_id."""

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), default="")
    preferred_brands: Mapped[list] = mapped_column(JSON, default=list)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    colours: Mapped[list] = mapped_column(JSON, default=list)
    budget_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sizes: Mapped[dict] = mapped_column(JSON, default=dict)
    audience: Mapped[str | None] = mapped_column(String(20), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ShoppingTask(Base):
    """Task memory — current hunt and products already shown."""

    __tablename__ = "shopping_tasks"

    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("user_profiles.user_id"), primary_key=True
    )
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    budget_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shown_product_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="open")


class Message(Base):
    """Conversation memory — durable chat turns for this user."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("user_profiles.user_id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
