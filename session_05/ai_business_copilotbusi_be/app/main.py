import os
from datetime import date
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from . import store
from .auth import COOKIE_NAME, authenticate, create_session_token, get_current_user, public_user, require_roles
from .copilot import run_copilot
from .database import database_engine
from .models import ApprovalExecuteRequest, ApprovalExecuteResponse, CopilotRequest, CopilotResponse, Customer, CustomerCreate, DashboardMetrics, BusinessTask, LoginRequest, TaskCreate, TaskStatus

app = FastAPI(title="AI Business Copilot API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


require_writer = require_roles("admin", "manager", "sales")
require_approver = require_roles("admin", "manager")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "AI Business Copilot", "database": database_engine()}


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response) -> dict:
    user = authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    response.set_cookie(
        key=COOKIE_NAME, value=create_session_token(user), httponly=True,
        secure=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax", max_age=8 * 60 * 60, path="/",
    )
    store.add_audit(user["email"], "auth.login", "user", user["id"], {"role": user["role"]})
    return public_user(user)


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return public_user(user)


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response, user: dict = Depends(get_current_user)) -> None:
    store.add_audit(user["email"], "auth.logout", "user", user["id"], {})
    response.delete_cookie(COOKIE_NAME, path="/")


@app.get("/api/dashboard", response_model=DashboardMetrics)
def dashboard(user: dict = Depends(get_current_user)) -> DashboardMetrics:
    customers = store.list_customers()
    tasks = store.list_tasks()
    open_tasks = [task for task in tasks if task.status != TaskStatus.done]
    return DashboardMetrics(
        revenue=sum(customer.value for customer in customers if customer.status == "active"),
        active_customers=sum(customer.status == "active" for customer in customers),
        at_risk_customers=sum(customer.status == "at_risk" for customer in customers),
        open_tasks=len(open_tasks),
        overdue_tasks=sum(task.due_date < date.today() for task in open_tasks),
        pipeline_value=sum(customer.value for customer in customers),
    )


@app.get("/api/customers", response_model=list[Customer])
def list_customers(status: str | None = None, user: dict = Depends(get_current_user)) -> list[Customer]:
    return store.list_customers(status)


@app.post("/api/customers", response_model=Customer, status_code=201)
def create_customer(payload: CustomerCreate, actor: dict = Depends(require_writer)) -> Customer:
    return store.add_customer(payload, actor["email"])


@app.get("/api/tasks", response_model=list[BusinessTask])
def list_tasks(user: dict = Depends(get_current_user)) -> list[BusinessTask]:
    return store.list_tasks()


@app.post("/api/tasks", response_model=BusinessTask, status_code=201)
def create_task(payload: TaskCreate, actor: dict = Depends(require_writer)) -> BusinessTask:
    return store.add_task(payload, actor["email"])


@app.patch("/api/tasks/{task_id}/status", response_model=BusinessTask)
def patch_task_status(task_id: UUID, status: TaskStatus, actor: dict = Depends(require_writer)) -> BusinessTask:
    task = store.update_task_status(task_id, status, actor["email"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/copilot", response_model=CopilotResponse)
def copilot(payload: CopilotRequest, user: dict = Depends(get_current_user)) -> CopilotResponse:
    return run_copilot(payload.message)


@app.post("/api/approvals/execute", response_model=ApprovalExecuteResponse, status_code=201)
def execute_approval(request: ApprovalExecuteRequest, actor: dict = Depends(require_approver)) -> ApprovalExecuteResponse:
    if request.action != "create_follow_up_task":
        raise HTTPException(status_code=400, detail="Unsupported approval action")

    payload = request.payload
    required = ("title", "description", "assignee", "due_date", "customer_id")
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing fields: {', '.join(missing)}")

    try:
        customer_id = UUID(str(payload["customer_id"]))
        due_date = date.fromisoformat(str(payload["due_date"]))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid customer_id or due_date") from exc

    if not any(customer.id == customer_id for customer in store.list_customers()):
        raise HTTPException(status_code=404, detail="Customer not found")
    if due_date < date.today():
        raise HTTPException(status_code=422, detail="Due date cannot be in the past")

    task = store.add_task(TaskCreate(
        title=str(payload["title"]),
        description=str(payload["description"]),
        assignee=str(payload["assignee"]),
        due_date=due_date,
        customer_id=customer_id,
        priority=str(payload.get("priority", "high")),
    ), actor["email"])
    return ApprovalExecuteResponse(status="approved", message="Công việc đã được tạo thành công.", task=task)


@app.get("/api/audit-logs")
def audit_logs(actor: dict = Depends(require_approver)) -> list[dict]:
    return store.list_audits()


@app.get("/api/notifications")
def notifications(actor: dict = Depends(get_current_user)) -> list[dict]:
    return store.list_notifications()


@app.get("/api/reports/operations")
def operations_report(actor: dict = Depends(get_current_user)) -> dict:
    customers = store.list_customers()
    tasks = store.list_tasks()
    return {
        "customer_distribution": {status: sum(c.status == status for c in customers) for status in ("active", "at_risk", "lead")},
        "task_distribution": {status: sum(t.status == status for t in tasks) for status in ("todo", "in_progress", "done")},
        "owner_performance": [{"owner": owner, "portfolio_value": sum(c.value for c in customers if c.owner == owner), "customers": sum(c.owner == owner for c in customers)} for owner in sorted({c.owner for c in customers})],
    }
