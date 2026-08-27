"""
Database engine/session setup.

SQLite is used during development (a single file, navix.db, created next to
this module). Swapping to PostgreSQL later only requires changing the
DATABASE_URL environment variable (e.g.
"postgresql+psycopg2://user:pass@host/dbname") -- no other module in this
project imports sqlite3 directly or relies on SQLite-only SQL, so the swap
is a config change, not a rewrite.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

# check_same_thread is only needed for SQLite (FastAPI talks to the DB from
# multiple threads/async tasks). PostgreSQL/MySQL don't need this arg.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
