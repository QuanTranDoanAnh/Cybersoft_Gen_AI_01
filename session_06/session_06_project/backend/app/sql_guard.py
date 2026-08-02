import re

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from .config import get_settings


ALLOWED_TABLES = {
    "shows",
    "show_votes",
    "air_dates",
    "genre_types",
    "genres",
    "created_by_types",
    "created_by",
    "production_company_types",
    "production_companies",
    "production_country_types",
    "production_countries",
}

FORBIDDEN_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|replace|merge|copy|"
    r"grant|revoke|call|execute|vacuum|analyze|refresh|set|show)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(ValueError):
    pass


def validate_and_limit_sql(sql: str) -> str:
    candidate = sql.strip().rstrip(";").strip()
    if not candidate:
        raise UnsafeQueryError("The query is empty")
    if ";" in candidate:
        raise UnsafeQueryError("Only one SQL statement is allowed")
    if FORBIDDEN_PATTERN.search(candidate):
        raise UnsafeQueryError("Only read-only SELECT queries are allowed")

    try:
        expression = parse_one(candidate, read="postgres")
    except ParseError as exc:
        raise UnsafeQueryError(f"Invalid PostgreSQL query: {exc}") from exc

    if not isinstance(expression, (exp.Select, exp.Union)):
        raise UnsafeQueryError("The query must be a SELECT statement")

    cte_names = {cte.alias_or_name.lower() for cte in expression.find_all(exp.CTE)}
    referenced_tables = {
        table.name.lower()
        for table in expression.find_all(exp.Table)
        if table.name.lower() not in cte_names
    }
    unknown_tables = referenced_tables - ALLOWED_TABLES
    if unknown_tables:
        names = ", ".join(sorted(unknown_tables))
        raise UnsafeQueryError(f"Query references unknown tables: {names}")
    if not referenced_tables:
        raise UnsafeQueryError("The query must read from an analytics table")

    limit = expression.args.get("limit")
    max_rows = get_settings().max_query_rows
    if limit is None:
        expression = expression.limit(max_rows)
    else:
        limit_value = limit.expression
        if isinstance(limit_value, exp.Literal) and limit_value.is_int:
            if int(limit_value.this) > max_rows:
                expression.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return expression.sql(dialect="postgres")
