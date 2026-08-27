from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.loop import run_agent
from app.config import settings
from app.database import get_db
from app.models import Transaction

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str
    trace: list[dict[str, Any]]
    mode: str


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    result = run_agent(payload.question.strip(), db)
    return ChatResponse(**result)


@router.get("/meta")
def meta(db: Session = Depends(get_db)) -> dict[str, Any]:
    count = db.scalar(select(func.count()).select_from(Transaction)) or 0
    first = db.scalar(select(func.min(Transaction.posted_on)))
    last = db.scalar(select(func.max(Transaction.posted_on)))
    categories = db.scalars(select(Transaction.category).distinct().order_by(Transaction.category)).all()
    return {
        "transaction_count": count,
        "start_date": first.isoformat() if first else None,
        "end_date": last.isoformat() if last else None,
        "categories": categories,
        "agent_mode": "llm" if settings.llm_enabled else "rules",
        "model": settings.llm_model if settings.llm_enabled else None,
        "today": date.today().isoformat(),
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
