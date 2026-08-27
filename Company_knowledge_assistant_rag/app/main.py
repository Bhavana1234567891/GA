from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.db import init_db
from app.store import get_embeddings, get_reranker, get_vectorstore

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    get_embeddings()
    get_vectorstore()
    get_reranker()
    yield


app = FastAPI(
    title="Company Knowledge Assistant",
    description="LangChain RAG over uploaded company PDFs: ingest, chunk, embed, retrieve, rerank.",
    lifespan=lifespan,
)
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
