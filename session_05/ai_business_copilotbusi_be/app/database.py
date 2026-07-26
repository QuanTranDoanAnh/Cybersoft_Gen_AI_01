import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


POSTGRES_ENV_KEYS = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASS", "DATABASE")


@dataclass(frozen=True)
class DatabaseSettings:
    engine: str
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    database: str | None = None
    sqlite_path: Path | None = None


def get_database_settings(env: Mapping[str, str] | None = None) -> DatabaseSettings:
    values = os.environ if env is None else env
    supplied = {key: values.get(key, "").strip() for key in POSTGRES_ENV_KEYS}
    configured = [key for key, value in supplied.items() if value]

    if configured and len(configured) != len(POSTGRES_ENV_KEYS):
        missing = [key for key, value in supplied.items() if not value]
        raise RuntimeError(
            "Cấu hình PostgreSQL chưa đầy đủ. Thiếu: " + ", ".join(missing)
        )

    if len(configured) == len(POSTGRES_ENV_KEYS):
        try:
            port = int(supplied["DB_PORT"])
        except ValueError as exc:
            raise RuntimeError("DB_PORT phải là một số nguyên hợp lệ") from exc
        if not 1 <= port <= 65535:
            raise RuntimeError("DB_PORT phải nằm trong khoảng 1-65535")

        return DatabaseSettings(
            engine="postgresql",
            host=supplied["DB_HOST"],
            port=port,
            user=supplied["DB_USER"],
            password=supplied["DB_PASS"],
            database=supplied["DATABASE"],
        )

    sqlite_path = Path(
        values.get(
            "DATABASE_PATH",
            str(Path(__file__).resolve().parent.parent / "data" / "orbit.db"),
        )
    )
    return DatabaseSettings(engine="sqlite", sqlite_path=sqlite_path)


SETTINGS = get_database_settings()


def connect() -> Any:
    if SETTINGS.engine == "postgresql":
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "Thiếu PostgreSQL driver. Hãy chạy: pip install -r requirements.txt"
            ) from exc

        return psycopg.connect(
            host=SETTINGS.host,
            port=SETTINGS.port,
            user=SETTINGS.user,
            password=SETTINGS.password,
            dbname=SETTINGS.database,
            connect_timeout=10,
            row_factory=dict_row,
        )

    assert SETTINGS.sqlite_path is not None
    SETTINGS.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(SETTINGS.sqlite_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def sql(query: str) -> str:
    """Convert DB-API placeholders for the selected database driver."""
    return query.replace("?", "%s") if SETTINGS.engine == "postgresql" else query


def execute_many(connection: Any, query: str, rows: list[tuple[Any, ...]]) -> None:
    cursor = connection.cursor()
    try:
        cursor.executemany(sql(query), rows)
    finally:
        cursor.close()


def database_engine() -> str:
    return SETTINGS.engine
