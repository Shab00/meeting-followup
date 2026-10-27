import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


# Schema for this service's own tables. Env-overridable so the same
# template works for other services.
_SEARCH_PATH = os.getenv("DB_SEARCH_PATH", "followup, public")


class Base(DeclarativeBase):
    pass


def _sqlalchemy_url(url: str) -> str:
    """Use the psycopg (v3) driver. A bare postgresql:// makes SQLAlchemy
    look for psycopg2, which isn't installed."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


engine = create_engine(_sqlalchemy_url(settings.database_url), pool_pre_ping=True)


@event.listens_for(engine, "connect")
def _set_search_path(dbapi_conn, _record):
    """Apply search_path on every pooled connection.

    Supavisor (Supabase's pooler) strips the `options=-csearch_path=...`
    parameter from the connection URL, so the URL alone cannot set the
    schema — verified empirically on meeting-processor: current_schema()
    stayed 'public' with connect_args, but returned the target schema
    after an explicit SET.

    Runs once per physical connection, before any query, so every
    checkout from the pool inherits the correct search_path.
    """
    with dbapi_conn.cursor() as cur:
        cur.execute(f"SET search_path TO {_SEARCH_PATH}")
    # DBAPI connection is not autocommit at connect-event time; without
    # this commit the SET is rolled back when the connection returns to
    # the pool.
    dbapi_conn.commit()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create the Workflow table. Imports app.models to register the model."""
    from app import models  # noqa: F401
    Base.metadata.create_all(engine)
