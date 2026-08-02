import json

from openai import OpenAI

from .config import get_settings
from .dashboard import execute_widget_plan
from .schemas import CopilotInsight, CopilotPlan, CopilotResponse, WidgetPlan
from .sql_guard import UnsafeQueryError, validate_and_limit_sql


SCHEMA_CONTEXT = """
PostgreSQL analytics schema:
- shows(show_id, name, number_of_seasons, number_of_episodes, adult,
  in_production, original_name, popularity, eposide_run_time, type_id, status_id)
- show_votes(show_id, vote_count, vote_average)
- air_dates(show_id, is_first, date)
- genre_types(genre_type_id, genre_name)
- genres(show_id, genre_type_id)
- created_by_types(created_by_type_id, created_by_name)
- created_by(show_id, created_by_type_id)
- production_company_types(production_company_type_id, production_company_name)
- production_companies(show_id, production_company_type_id)
- production_country_types(production_country_type_id, production_country_name)
- production_countries(show_id, production_country_type_id)

Join facts using show_id. Join lookup tables using their matching *_type_id.
Ratings are from 0 to 10. popularity is a positive score. air_dates.date is a
PostgreSQL DATE. The source column is intentionally named eposide_run_time.
"""

SYSTEM_PROMPT = f"""
You are the visualization planner for a TV shows business intelligence app.
Turn each user request into a complete replacement dashboard, not widgets to
append to an existing overview.

Success criteria:
- Give the dashboard a short, specific title in the user's language.
- Return 3-6 widgets that together answer the question. Prefer 2-4 KPI cards
  for the most decision-useful scalar metrics plus 1-3 supporting charts or a
  detail table. Do not include unrelated catalog-overview widgets.
- Every SQL statement is a single read-only PostgreSQL SELECT or WITH query.
- Use only the documented schema and exact column names.
- Select only fields needed by the visual and use clear lowercase aliases.
- Aggregate before returning data and limit detail/table queries to 50 rows.
- For historical/current-period questions, exclude future dates with
  air_dates.date <= CURRENT_DATE unless the user explicitly asks for forecasts.
- Use KPI for one scalar, line/area for time, bar for category comparison, pie
  only for at most seven parts, scatter for relationships, and table for detail.
- For every KPI, select exactly one scalar aliased as value and set value_field
  to value (for example: SELECT COUNT(*) AS value FROM shows).
- x_field, y_fields, series_field and value_field must exactly match SQL aliases.
- Respond in the same language as the user.
- message briefly states what the dashboard measures. Do not invent findings;
  a separate step will write insights after the queries have run.
- If the request is ambiguous, create a sensible overview instead of guessing
  unsupported business facts.

{SCHEMA_CONTEXT}
"""


def _parsed_plan(response) -> CopilotPlan:
    parsed = getattr(response, "output_parsed", None)
    if isinstance(parsed, CopilotPlan):
        return parsed
    for output in response.output:
        if getattr(output, "type", None) != "message":
            continue
        for item in output.content:
            value = getattr(item, "parsed", None)
            if isinstance(value, CopilotPlan):
                return value
            refusal = getattr(item, "refusal", None)
            if refusal:
                raise ValueError(refusal)
    raise ValueError("OpenAI did not return a dashboard plan")


def _openai_plan(prompt: str) -> CopilotPlan:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.parse(
        model=settings.openai_model,
        reasoning={"effort": "low"},
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        text_format=CopilotPlan,
    )
    return _parsed_plan(response)


def _openai_insight(prompt: str, plan: CopilotPlan, results: list) -> str:
    settings = get_settings()
    evidence = [
        {
            "title": widget.title,
            "description": widget.description,
            "data": widget.data[:25],
        }
        for widget in results
    ]
    response = OpenAI(api_key=settings.openai_api_key).responses.parse(
        model=settings.openai_model,
        reasoning={"effort": "low"},
        input=[
            {
                "role": "system",
                "content": (
                    "Write a concise, data-grounded BI insight in the same language "
                    "as the user. Lead with the answer, cite 2-4 important values or "
                    "comparisons visible in the supplied query results, and mention "
                    "a material caveat only if needed. Use 2-4 sentences. Never add "
                    "facts that are absent from the evidence."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": prompt,
                        "dashboard_title": plan.dashboard_title,
                        "query_results": evidence,
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ],
        text_format=CopilotInsight,
    )
    parsed = getattr(response, "output_parsed", None)
    if isinstance(parsed, CopilotInsight):
        return parsed.message
    for output in response.output:
        for item in getattr(output, "content", []):
            value = getattr(item, "parsed", None)
            if isinstance(value, CopilotInsight):
                return value.message
    return plan.message


def _demo_plan(prompt: str) -> CopilotPlan:
    normalized = prompt.lower()
    if any(word in normalized for word in ("genre", "thể loại")):
        widgets = [
            WidgetPlan(
                title="Phân bố theo thể loại",
                description="Top 10 thể loại có nhiều chương trình nhất",
                chart_type="bar",
                sql="""
                    SELECT gt.genre_name AS genre, COUNT(*) AS shows
                    FROM genres g JOIN genre_types gt
                      ON gt.genre_type_id = g.genre_type_id
                    GROUP BY gt.genre_name ORDER BY shows DESC LIMIT 10
                """,
                x_field="genre",
                y_fields=["shows"],
                number_format="compact",
            )
        ]
    elif any(word in normalized for word in ("country", "countries", "quốc gia")):
        widgets = [
            WidgetPlan(
                title="Top quốc gia sản xuất",
                description="Các quốc gia có nhiều chương trình nhất",
                chart_type="pie",
                sql="""
                    SELECT pct.production_country_name AS country, COUNT(*) AS shows
                    FROM production_countries pc
                    JOIN production_country_types pct
                      ON pct.production_country_type_id = pc.production_country_type_id
                    GROUP BY pct.production_country_name
                    ORDER BY shows DESC LIMIT 7
                """,
                x_field="country",
                y_fields=["shows"],
                number_format="compact",
            )
        ]
    elif any(word in normalized for word in ("year", "năm", "trend", "xu hướng")):
        widgets = [
            WidgetPlan(
                title="Số chương trình phát hành theo năm",
                description="Xu hướng phát hành trong 20 năm gần nhất",
                chart_type="area",
                sql="""
                    SELECT year, shows
                    FROM (
                        SELECT EXTRACT(YEAR FROM date)::int AS year,
                               COUNT(*) AS shows
                        FROM air_dates
                        WHERE date IS NOT NULL AND date <= CURRENT_DATE
                        GROUP BY year ORDER BY year DESC LIMIT 20
                    ) recent_years
                    ORDER BY year
                """,
                x_field="year",
                y_fields=["shows"],
                number_format="compact",
            )
        ]
    else:
        widgets = [
            WidgetPlan(
                title="Chương trình nổi bật",
                description="Top chương trình theo độ phổ biến",
                chart_type="bar",
                sql="""
                    SELECT name, ROUND(popularity::numeric, 1) AS popularity
                    FROM shows ORDER BY popularity DESC NULLS LAST LIMIT 10
                """,
                x_field="name",
                y_fields=["popularity"],
                number_format="decimal",
            )
        ]
    return CopilotPlan(
        dashboard_title="Phân tích theo yêu cầu",
        message="Đã tạo visual từ dữ liệu mẫu. Thêm OPENAI_API_KEY để dùng lập kế hoạch linh hoạt hơn.",
        widgets=widgets,
    )


def run_copilot(prompt: str) -> CopilotResponse:
    settings = get_settings()
    mode = "openai" if settings.openai_api_key else "demo"
    plan = _openai_plan(prompt) if settings.openai_api_key else _demo_plan(prompt)

    results = []
    errors = []
    for index, widget_plan in enumerate(plan.widgets):
        try:
            safe_sql = validate_and_limit_sql(widget_plan.sql)
            results.append(execute_widget_plan(widget_plan, safe_sql, index))
        except (UnsafeQueryError, Exception) as exc:
            errors.append(f"{widget_plan.title}: {exc}")

    if not results:
        detail = "; ".join(errors) or "No valid widgets were generated"
        raise ValueError(detail)

    message = plan.message
    if settings.openai_api_key:
        try:
            message = _openai_insight(prompt, plan, results)
        except Exception:
            # The queried dashboard is still useful if the optional narrative
            # call fails or times out.
            message = plan.message
    if errors:
        message += f" Có {len(errors)} visual không thể tạo do truy vấn không hợp lệ."
    return CopilotResponse(
        title=plan.dashboard_title,
        message=message,
        mode=mode,
        widgets=results,
    )
