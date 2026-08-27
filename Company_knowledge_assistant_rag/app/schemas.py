from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    rerank: bool = True
    doc_type: str | None = None


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    rerank: bool = True
    doc_type: str | None = None
