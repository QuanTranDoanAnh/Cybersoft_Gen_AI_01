from collections.abc import Iterable

from psycopg import Connection, connect
from psycopg.rows import dict_row

from .config import get_settings


def get_connection() -> Connection:
    return connect(get_settings().database_url, row_factory=dict_row)


def fetch_all(sql: str, params: Iterable | None = None) -> list[dict]:
    settings = get_settings()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL statement_timeout = {settings.query_timeout_ms}")
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]


def fetch_value(sql: str, params: Iterable | None = None):
    rows = fetch_all(sql, params)
    if not rows:
        return None
    return next(iter(rows[0].values()))
