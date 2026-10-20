"""Database setup.

The database URL comes from the DATABASE_URL environment variable.
Locally it defaults to a SQLite file so the project runs with zero setup;
in Docker Compose it points at the PostgreSQL container.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jobtracker.db")

# SQLite needs this flag when used from multiple threads (FastAPI dev server).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
