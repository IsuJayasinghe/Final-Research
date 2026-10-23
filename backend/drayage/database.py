"""
Database session management and connection handling for Component 2.
Connects to PostgreSQL 18 multi-schema database using SQLAlchemy and psycopg.
"""
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from .config import settings

logger = logging.getLogger("drayage.database")

Base = declarative_base()

# Configure SQLAlchemy engine with connection pool
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    connect_args={"connect_timeout": settings.DB_CONNECT_TIMEOUT_SECONDS},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_database_connection() -> bool:
    """
    Verifies live connectivity to the PostgreSQL smart_port_management database.
    Returns True if reachable and can execute SELECT 1, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            return True
    except Exception as e:
        logger.warning("Database connection check failed: %s", str(e))
        return False


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request.
    Closes the session after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
