"""Database connection and session for SQLAlchemy."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_ERROR = (
    "DATABASE_URL is required. Set it in service/.env or deployment environment "
    "(example: postgresql://postgres:postgres@localhost:5432/accounts)."
)


def _build_engine():
    if not DATABASE_URL:
        return None
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
        )
    return create_engine(
        DATABASE_URL,
        pool_timeout=30,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine is not None else None
Base = declarative_base()


def get_db():
    """Dependency that yields a DB session."""
    if SessionLocal is None:
        raise RuntimeError(DATABASE_URL_ERROR)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
