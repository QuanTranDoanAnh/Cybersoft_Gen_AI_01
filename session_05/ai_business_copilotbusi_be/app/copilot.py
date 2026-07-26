import json
import os
from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from openai import OpenAI, OpenAIError

from . import store
from .models import ApprovalProposal, CopilotResponse, ToolTrace, Visualization


SYSTEM_PROMPT = """Bạn là AI Copilot cho hệ thống quản trị doanh nghiệp.
Trả lời ngắn gọn bằng tiếng Việt, dựa trên dữ liệu tool. Không tự bịa số liệu.
Các thao tác ghi dữ liệu chỉ được tạo đề xuất chờ người dùng phê duyệt.
Khi phù hợp, hãy nêu ra insight và hành động tiếp theo cụ thể."""


@tool
def get_dashboard_metrics() -> dict:
    """Lấy các KPI tổng quan hiện tại của doanh nghiệp."""
    customers = store.list_customers()
    tasks = store.list_tasks()
    open_tasks = [task for task in tasks if task.status is not "done"]

    return {
        "revenue": sum(
            customer.value for customer in customers if customer.status == "active"
        ),
        "active_customers": sum(customer.status == "active" for customer in customers),
        "at_risk_customers": sum(
            customer.status == "at_risk" for customer in customers
        ),
        "open_tasks": len(open_tasks),
        "overdue_tasks": sum(task.due_date < date.today() for task in open_tasks),
        "pipeline_value": sum(customer.value for customer in customers),
    }


@tool
def find_inactive_customers(inactive_days: int = 30) -> list[dict]:
    """Tìm khách hàng chưa được liên hệ trong một số ngày."""
    results = []
    for customer in store.list_customers():
        days = (date.today() - customer.last_contact).days
        if days >= inactive_days:
            results.append({**customer.model_dump(mode="json"), "inactive_days": days})

    return results


@tool
def get_overdue_tasks() -> list[dict]:
    """Lấy các công việc chưa hoàn thành và đã quá hạn."""
    return [
        task.model_dump(mode="json")
        for task in store.list_tasks
        if task.status != "done" and task.due_date < date.today()
    ]


@tool
def get_operations_report() -> dict:
    """Lấy thống kê phân bổ khách hàng, công việc và giá trị danh mục theo nhân viên để lập báo cáo hoặc biểu đồ."""
    customers = store.list_customers()
    tasks = store.list_tasks()
    return {
        "customer_distribution": {
            status: sum(customer.status == status for customer in customers)
            for status in ("active", "at_risk", "lead")
        },
        "task_distribution": {
            status: sum(task.status == status for task in tasks)
            for status in ("todo", "in_progress", "done")
        },
        "owner_performance": [
            {
                "owner": owner,
                "portfolio_value": sum(c.value for c in customers if c.owner == owner),
                "customers": sum(c.owner == owner for c in customers),
            }
            for owner in sorted({c.owner for c in customers})
        ],
    }


@tool
def propose_follow_up_task(
    customer_id: str, assignee: str, due_date: str, description: str
) -> dict:
    """Tạo đề xuất công việc follow-up; cần người dùng phê duyệt trước khi ghi dữ liệu."""
    customer = next(
        (item for item in store.list_customers() if str(item.id) == customer_id), None
    )
    return {
        "requires_approval": True,
        "action": "create_follow_up_task",
        "payload": {
            "customer_id": customer_id,
            "assignee": assignee,
            "due_date": due_date,
            "description": description,
            "title": f"Follow-up {customer.company if customer else 'khách hàng'}",
        },
        "reason": "Thao tác này sẽ tạo công việc mới trong hệ thống.",
    }


@tool
def research_web(query: str) -> str:
    """Tìm thông tin mới trên web bằng OpenAI Web Search; dùng cho thị trường, đối thủ và tin tức bên ngoài."""
    if not os.getenv("OPENAI_API_KEY"):
        return "Web research cần cấu hình OPENAI_API_KEY."
    try:
        response = OpenAI().responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            tools=[{"type": "web_search"}],
            input=f"Tìm kiếm web và trả lời ngắn gọn bằng tiếng Việt, kèm URL nguồn: {query}",
        )
        return response.output_text or "Web Search không trả về nội dung."
    except OpenAIError as exc:
        return f"OpenAI Web Search tạm thời không khả dụng ({type(exc).__name__})."


TOOLS = [
    get_dashboard_metrics,
    get_operations_report,
    find_inactive_customers,
    get_overdue_tasks,
    propose_follow_up_task,
    research_web,
]
TOOLS_BY_NAME = {item.name: item for item in TOOLS}


def local_demo_response(message: str) -> CopilotResponse:
    lowered = message.lower()
    if any(
        term in lowered for term in ("tìm trên web", "tin mới", "đối thủ", "thị trường")
    ):
        return CopilotResponse(
            answer="Web research cần OPENAI_API_KEY. Sau khi cấu hình, Copilot sẽ dùng OpenAI Web Search và trả kết quả kèm nguồn."
        )
    if any(
        term in lowered
        for term in ("báo cáo", "thống kê", "biểu đồ", "phân bổ", "hiệu suất")
    ):
        result = get_operations_report.invoke({})
        trace = ToolTrace(
            tool="get_operations_report",
            arguments={},
            result=json.dumps(result, ensure_ascii=False),
        )
        return CopilotResponse(
            answer="Đây là báo cáo trực quan từ dữ liệu vận hành hiện tại.",
            traces=[trace],
            visualizations=build_visualizations([trace]),
        )
    if "quá hạn" in lowered or "trễ" in lowered:
        result = get_overdue_tasks.invoke({})
        answer = (
            f"Hiện có {len(result)} công việc quá hạn. Ưu tiên xử lý: "
            + ", ".join(item["title"] for item in result)
        )
        trace = ToolTrace(
            tool="get_overdue_tasks",
            arguments={},
            result=json.dumps(result, ensure_ascii=False),
        )
        return CopilotResponse(
            answer=answer, traces=[trace], visualizations=build_visualizations([trace])
        )
    if "30 ngày" in lowered or "chưa" in lowered and "liên hệ" in lowered:
        result = find_inactive_customers.invoke({"inactive_days": 30})
        answer = (
            f"Có {len(result)} khách hàng chưa được liên hệ trong ít nhất 30 ngày: "
            + ", ".join(item["company"] for item in result)
        )
        trace = ToolTrace(
            tool="find_inactive_customers",
            arguments={"inactive_days": 30},
            result=json.dumps(result, ensure_ascii=False),
        )
        return CopilotResponse(
            answer=answer, traces=[trace], visualizations=build_visualizations([trace])
        )
    result = get_dashboard_metrics.invoke({})
    answer = f"Doanh nghiệp có {result['active_customers']} khách hàng hoạt động, {result['at_risk_customers']} khách hàng cần chú ý và {result['open_tasks']} công việc đang mở."
    trace = ToolTrace(
        tool="get_dashboard_metrics",
        arguments={},
        result=json.dumps(result, ensure_ascii=False),
    )
    return CopilotResponse(
        answer=answer, traces=[trace], visualizations=build_visualizations([trace])
    )


def build_visualizations(traces: list[ToolTrace]) -> list[Visualization]:
    charts: list[Visualization] = []
    labels = {
        "active": "Đang hoạt động",
        "at_risk": "Cần chú ý",
        "lead": "Tiềm năng",
        "todo": "Cần làm",
        "in_progress": "Đang thực hiện",
        "done": "Hoàn thành",
    }
    for trace in traces:
        try:
            result = json.loads(trace.result)
        except (json.JSONDecodeError, TypeError):
            continue
        if trace.tool == "get_dashboard_metrics":
            charts.append(
                Visualization(
                    type="kpi",
                    title="KPI doanh nghiệp",
                    data=[
                        {
                            "label": "Doanh thu",
                            "value": result["revenue"],
                            "unit": "VND",
                        },
                        {
                            "label": "Pipeline",
                            "value": result["pipeline_value"],
                            "unit": "VND",
                        },
                        {
                            "label": "Khách hoạt động",
                            "value": result["active_customers"],
                        },
                        {"label": "Task đang mở", "value": result["open_tasks"]},
                    ],
                )
            )
        elif trace.tool == "get_operations_report":
            charts.extend(
                [
                    Visualization(
                        type="donut",
                        title="Phân bổ khách hàng",
                        data=[
                            {"label": labels.get(key, key), "value": value}
                            for key, value in result["customer_distribution"].items()
                        ],
                    ),
                    Visualization(
                        type="donut",
                        title="Tiến độ công việc",
                        data=[
                            {"label": labels.get(key, key), "value": value}
                            for key, value in result["task_distribution"].items()
                        ],
                    ),
                    Visualization(
                        type="bar",
                        title="Giá trị danh mục theo nhân viên",
                        unit="VND",
                        data=[
                            {"label": item["owner"], "value": item["portfolio_value"]}
                            for item in result["owner_performance"]
                        ],
                    ),
                ]
            )
        elif trace.tool == "find_inactive_customers" and result:
            charts.append(
                Visualization(
                    type="bar",
                    title="Giá trị khách hàng cần follow-up",
                    unit="VND",
                    data=[
                        {"label": item["company"], "value": item["value"]}
                        for item in result
                    ],
                )
            )
        elif trace.tool == "get_overdue_tasks" and result:
            charts.append(
                Visualization(
                    type="bar",
                    title="Công việc quá hạn",
                    description="Mỗi cột tương ứng một công việc",
                    data=[{"label": item["title"], "value": 1} for item in result],
                )
            )
    return charts


def run_copilot(message: str) -> CopilotResponse:
    if not os.getenv("OPENAI_API_KEY"):
        return local_demo_response(message)

    # Do not force a sampling temperature: GPT-5 reasoning models only accept
    # their default value, while ChatOpenAI omits this optional parameter when
    # it is not provided.
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    model_with_tools = model.bind_tools(TOOLS)
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=message)]
    traces: list[ToolTrace] = []
    approval = None

    try:
        for _ in range(4):
            ai_message = model_with_tools.invoke(messages)
            messages.append(ai_message)
            if not ai_message.tool_calls:
                return CopilotResponse(
                    answer=str(ai_message.content),
                    traces=traces,
                    approval=approval,
                    visualizations=build_visualizations(traces),
                )
            for call in ai_message.tool_calls:
                result = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
                traces.append(
                    ToolTrace(
                        tool=call["name"],
                        arguments=call["args"],
                        result=json.dumps(result, ensure_ascii=False, default=str),
                    )
                )
                if isinstance(result, dict) and result.get("requires_approval"):
                    approval = ApprovalProposal(
                        action=result["action"],
                        payload=result["payload"],
                        reason=result["reason"],
                    )
                messages.append(
                    ToolMessage(
                        content=json.dumps(result, ensure_ascii=False, default=str),
                        tool_call_id=call["id"],
                    )
                )
    except OpenAIError as exc:
        return CopilotResponse(
            answer=f"OpenAI hiện chưa xử lý được yêu cầu này ({type(exc).__name__}). Vui lòng thử lại sau.",
            traces=traces,
            approval=approval,
            visualizations=build_visualizations(traces),
        )

    return CopilotResponse(
        answer="Copilot đã đạt giới hạn số bước xử lý.",
        traces=traces,
        approval=approval,
        visualizations=build_visualizations(traces),
    )
