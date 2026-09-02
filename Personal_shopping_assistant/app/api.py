from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import memory as store
from app.agent.loop import run_agent
from app.config import settings
from app.database import get_db
from app.models import Product

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=40)
    message: str = Field(min_length=1, max_length=2000)


class ResetRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=40)
    clear_profile: bool = False


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    user_id = payload.user_id.strip()
    message = payload.message.strip()
    result = run_agent(message, db, user_id)
    store.add_message(db, user_id, "user", message)
    store.add_message(db, user_id, "assistant", result["answer"])
    db.commit()
    return {
        **result,
        "user_id": user_id,
        "memory": store.snapshot(db, user_id),
    }


@router.get("/memory")
def memory(user_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    snap = store.snapshot(db, user_id)
    db.commit()
    return snap


@router.get("/history")
def chat_history(user_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    return {"user_id": user_id, "messages": store.history(db, user_id)}


@router.post("/reset")
def reset(payload: ResetRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    snap = store.reset_session(db, payload.user_id.strip(), clear_profile=payload.clear_profile)
    db.commit()
    return snap


@router.get("/meta")
def meta(db: Session = Depends(get_db)) -> dict[str, Any]:
    product_count = db.scalar(select(func.count()).select_from(Product)) or 0
    categories = db.scalars(select(Product.category).distinct().order_by(Product.category)).all()
    return {
        "product_count": product_count,
        "categories": categories,
        "users": store.list_users(db),
        "agent_mode": "llm" if settings.llm_enabled else "rules",
        "model": settings.llm_model if settings.llm_enabled else None,
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
