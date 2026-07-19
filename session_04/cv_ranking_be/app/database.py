from __future__ import annotations

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()


def build_database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS", "")
    database = os.getenv("DATABASE")
    sslmode = os.getenv("DB_SSLMODE", "require")

    if db_host and db_user and database:
        encoded_user = quote_plus(db_user)
        encoded_pass = quote_plus(db_pass)
        encoded_sslmode = quote_plus(sslmode)
        return (
            f"postgresql+psycopg://{encoded_user}:{encoded_pass}@{db_host}:{db_port}/{database}"
            f"?sslmode={encoded_sslmode}"
        )

    return "sqlite:///./cv_ranking_platform.db"


DATABASE_URL = build_database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
