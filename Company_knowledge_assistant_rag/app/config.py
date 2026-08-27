from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rag:rag@localhost:5432/company_kb"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = ""

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    ingest_version: str = "langchain-lcel-1"
    collection_name: str = "company_knowledge"
    chunk_size: int = 800
    chunk_overlap: int = 200
    retrieve_k: int = 20
    rerank_top_n: int = 5
    context_char_budget: int = 4500
    max_file_size_mb: int = 20

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def pdf_dir(self) -> Path:
        path = Path(__file__).resolve().parent.parent / "data" / "pdfs"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
