from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


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
