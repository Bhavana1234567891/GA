from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(engine, "connect")
def _register_vector(dbapi_connection, _connection_record) -> None:
    from pgvector.psycopg import register_vector

    try:
        register_vector(dbapi_connection)
    except Exception:
        # Extension may not exist yet on first boot.
        pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from pgvector.psycopg import register_vector

    from app import models  # noqa: F401 — register tables on Base.metadata

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        register_vector(conn.connection.dbapi_connection)
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw "
                    "ON chunks USING hnsw (embedding vector_cosine_ops)"
                )
            )
    except Exception:
        # Sequential scan is fine for a small company PDF corpus.
        pass
