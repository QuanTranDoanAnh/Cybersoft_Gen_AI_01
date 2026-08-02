from app.schemas import WidgetPlan


def test_kpi_defaults_missing_value_field():
    plan = WidgetPlan(
        title="Total releases",
        chart_type="kpi",
        sql="SELECT COUNT(*) AS total_releases FROM air_dates",
    )

    assert plan.value_field == "value"

