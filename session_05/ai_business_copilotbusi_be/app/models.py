from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CustomerStatus(str, Enum):
    active = "active"
    at_risk = "at_risk"
    lead = "lead"


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class Customer(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    company: str
    email: str
    phone: str = ""
    status: CustomerStatus = CustomerStatus.lead
    value: int = 0
    last_contact: date
    owner: str


class CustomerCreate(BaseModel):
    name: str
    company: str
    email: str
    phone: str = ""
    status: CustomerStatus = CustomerStatus.lead
    value: int = 0
    last_contact: date = Field(default_factory=date.today)
    owner: str = "Chưa phân công"


class BusinessTask(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.todo
    priority: str = "medium"
    due_date: date
    assignee: str
    customer_id: UUID | None = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.todo
    priority: str = "medium"
    due_date: date
    assignee: str
    customer_id: UUID | None = None


class DashboardMetrics(BaseModel):
    revenue: int
    active_customers: int
    at_risk_customers: int
    open_tasks: int
    overdue_tasks: int
    pipeline_value: int


class CopilotRequest(BaseModel):
    message: str


class ToolTrace(BaseModel):
    tool: str
    arguments: dict
    result: str


class ApprovalProposal(BaseModel):
    action: str
    payload: dict
    reason: str


class Visualization(BaseModel):
    type: str
    title: str
    description: str | None = None
    unit: str | None = None
    data: list[dict]


class CopilotResponse(BaseModel):
    answer: str
    traces: list[ToolTrace] = []
    approval: ApprovalProposal | None = None
    visualizations: list[Visualization] = []
    created_at: datetime = Field(default_factory=datetime.now)


class ApprovalExecuteRequest(BaseModel):
    action: str
    payload: dict


class ApprovalExecuteResponse(BaseModel):
    status: str
    message: str
    task: BusinessTask


class LoginRequest(BaseModel):
    email: str
    password: str
