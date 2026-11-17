"""Database setup. SQLite by default for local development, Postgres via DATABASE_URL."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ase.db")


class Base(DeclarativeBase):
    pass


def make_engine(url: str = DATABASE_URL):
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    return create_engine(url, **kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(bind=None):
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(bind or engine)
