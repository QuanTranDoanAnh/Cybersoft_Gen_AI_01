from uuid import uuid4

from .database import fetch_all
from .schemas import DashboardResponse, WidgetPlan, WidgetResult


def _layout(index: int, chart_type: str) -> dict[str, int]:
    if chart_type == "kpi":
        return {"x": (index % 4) * 3, "y": 0, "w": 3, "h": 3}
    chart_index = max(0, index - 4)
    return {
        "x": (chart_index % 2) * 6,
        "y": 3 + (chart_index // 2) * 6,
        "w": 6,
        "h": 6,
    }


def execute_widget_plan(
    plan: WidgetPlan,
    sql: str,
    index: int,
    include_sql: bool = True,
) -> WidgetResult:
    data = fetch_all(sql)
    value_field = plan.value_field
    if plan.chart_type == "kpi" and data and value_field not in data[0]:
        value_field = next(iter(data[0]))
    return WidgetResult(
        id=str(uuid4()),
        title=plan.title,
        description=plan.description,
        chart_type=plan.chart_type,
        x_field=plan.x_field,
        y_fields=plan.y_fields,
        series_field=plan.series_field,
        value_field=value_field,
        number_format=plan.number_format,
        data=data,
        sql=sql if include_sql else None,
        layout=_layout(index, plan.chart_type),
    )


OVERVIEW_PLANS = [
    WidgetPlan(
        title="Total shows",
        description="Titles available in the catalog",
        chart_type="kpi",
        sql="SELECT COUNT(*) AS value FROM shows",
        value_field="value",
        number_format="compact",
    ),
    WidgetPlan(
        title="Average rating",
        description="Mean audience score across rated titles",
        chart_type="kpi",
        sql=(
            "SELECT ROUND(AVG(vote_average)::numeric, 2) AS value "
            "FROM show_votes WHERE vote_count >= 10"
        ),
        value_field="value",
        number_format="decimal",
    ),
    WidgetPlan(
        title="Total votes",
        description="Combined audience votes",
        chart_type="kpi",
        sql="SELECT SUM(vote_count) AS value FROM show_votes",
        value_field="value",
        number_format="compact",
    ),
    WidgetPlan(
        title="In production",
        description="Shows currently marked in production",
        chart_type="kpi",
        sql="SELECT COUNT(*) AS value FROM shows WHERE in_production = TRUE",
        value_field="value",
        number_format="compact",
    ),
    WidgetPlan(
        title="Top genres",
        description="Most represented genres in the catalog",
        chart_type="bar",
        sql="""
            SELECT gt.genre_name AS genre, COUNT(*) AS shows
            FROM genres g
            JOIN genre_types gt ON gt.genre_type_id = g.genre_type_id
            GROUP BY gt.genre_name
            ORDER BY shows DESC
            LIMIT 8
        """,
        x_field="genre",
        y_fields=["shows"],
        number_format="compact",
    ),
    WidgetPlan(
        title="Releases by year",
        description="Catalog growth during the last 25 release years",
        chart_type="area",
        sql="""
            SELECT year, shows
            FROM (
                SELECT EXTRACT(YEAR FROM date)::int AS year, COUNT(*) AS shows
                FROM air_dates
                WHERE date IS NOT NULL AND date <= CURRENT_DATE
                GROUP BY year
                ORDER BY year DESC
                LIMIT 25
            ) recent_years
            ORDER BY year
        """,
        x_field="year",
        y_fields=["shows"],
        number_format="compact",
    ),
    WidgetPlan(
        title="Most popular shows",
        description="Titles ranked by popularity score",
        chart_type="table",
        sql="""
            SELECT s.name, ROUND(s.popularity::numeric, 1) AS popularity,
                   ROUND(v.vote_average::numeric, 1) AS rating, v.vote_count
            FROM shows s
            LEFT JOIN show_votes v ON v.show_id = s.show_id
            ORDER BY s.popularity DESC NULLS LAST
            LIMIT 8
        """,
        number_format="number",
    ),
    WidgetPlan(
        title="Production countries",
        description="Countries with the largest number of titles",
        chart_type="pie",
        sql="""
            SELECT pct.production_country_name AS country, COUNT(*) AS shows
            FROM production_countries pc
            JOIN production_country_types pct
              ON pct.production_country_type_id = pc.production_country_type_id
            GROUP BY pct.production_country_name
            ORDER BY shows DESC
            LIMIT 7
        """,
        x_field="country",
        y_fields=["shows"],
        number_format="compact",
    ),
]


def get_overview_dashboard() -> DashboardResponse:
    widgets = [
        execute_widget_plan(plan, plan.sql, index, include_sql=False)
        for index, plan in enumerate(OVERVIEW_PLANS)
    ]
    return DashboardResponse(
        title="TV Shows Intelligence",
        subtitle="Interactive overview of catalog, ratings, genres and releases",
        widgets=widgets,
    )
