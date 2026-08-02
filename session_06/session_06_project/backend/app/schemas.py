from typing import Literal

from pydantic import BaseModel, Field, model_validator


ChartType = Literal["bar", "line", "area", "pie", "scatter", "table", "kpi"]
NumberFormat = Literal["number", "integer", "decimal", "percent", "compact"]


class WidgetPlan(BaseModel):
    title: str = Field(min_length=2, max_length=90)
    description: str = Field(default="", max_length=240)
    chart_type: ChartType
    sql: str = Field(min_length=8, max_length=5_000)
    x_field: str | None = None
    y_fields: list[str] = Field(default_factory=list, max_length=3)
    series_field: str | None = None
    value_field: str | None = None
    number_format: NumberFormat = "number"

    @model_validator(mode="after")
    def validate_visual_fields(self) -> "WidgetPlan":
        if self.chart_type == "kpi" and not self.value_field:
            # Structured output models occasionally omit this redundant field;
            # the executor verifies it against the actual scalar query result.
            self.value_field = "value"
        if self.chart_type not in {"kpi", "table"}:
            if not self.x_field or not self.y_fields:
                raise ValueError("Charts require x_field and at least one y_field")
        return self


class CopilotPlan(BaseModel):
    dashboard_title: str = Field(min_length=2, max_length=90)
    message: str = Field(min_length=2, max_length=300)
    widgets: list[WidgetPlan] = Field(min_length=1, max_length=6)


class CopilotInsight(BaseModel):
    message: str = Field(min_length=2, max_length=700)


class CopilotRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1_000)


class WidgetResult(BaseModel):
    id: str
    title: str
    description: str
    chart_type: ChartType
    x_field: str | None = None
    y_fields: list[str] = Field(default_factory=list)
    series_field: str | None = None
    value_field: str | None = None
    number_format: NumberFormat = "number"
    data: list[dict]
    sql: str | None = None
    layout: dict[str, int]


class DashboardResponse(BaseModel):
    title: str
    subtitle: str
    widgets: list[WidgetResult]


class CopilotResponse(BaseModel):
    title: str
    message: str
    mode: Literal["openai", "demo"]
    widgets: list[WidgetResult]


class MetaResponse(BaseModel):
    app_name: str
    model: str
    copilot_mode: Literal["openai", "demo"]
    dataset: str
