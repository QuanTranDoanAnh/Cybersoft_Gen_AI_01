import pytest

from app.sql_guard import UnsafeQueryError, validate_and_limit_sql


def test_adds_limit_to_select():
    sql = validate_and_limit_sql("SELECT name FROM shows ORDER BY popularity DESC")
    assert "LIMIT 500" in sql


def test_allows_cte():
    sql = validate_and_limit_sql(
        "WITH ranked AS (SELECT name FROM shows) SELECT name FROM ranked"
    )
    assert sql.startswith("WITH")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM shows",
        "DROP TABLE shows",
        "SELECT * FROM users",
        "SELECT 1; SELECT 2",
        "SELECT pg_sleep(10)",
    ],
)
def test_rejects_unsafe_queries(sql: str):
    with pytest.raises(UnsafeQueryError):
        validate_and_limit_sql(sql)
