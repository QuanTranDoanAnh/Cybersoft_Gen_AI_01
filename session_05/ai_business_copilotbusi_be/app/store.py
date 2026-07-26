import json
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from .database import connect, execute_many, sql
from .models import BusinessTask, Customer, CustomerCreate, CustomerStatus, TaskCreate, TaskStatus

def init_db() -> None:
    with connect() as db:
        statements = (
            """CREATE TABLE IF NOT EXISTS customers (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, company TEXT NOT NULL,
              email TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
              value BIGINT NOT NULL DEFAULT 0, last_contact TEXT NOT NULL, owner TEXT NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL, priority TEXT NOT NULL, due_date TEXT NOT NULL,
              assignee TEXT NOT NULL, customer_id TEXT REFERENCES customers(id),
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS approvals (
              id TEXT PRIMARY KEY, action TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
              requested_by TEXT NOT NULL, reviewed_by TEXT, created_at TEXT NOT NULL,
              reviewed_at TEXT, task_id TEXT REFERENCES tasks(id)
            )""",
            """CREATE TABLE IF NOT EXISTS audit_logs (
              id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
              entity_type TEXT NOT NULL, entity_id TEXT, details TEXT NOT NULL,
              created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS notifications (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, message TEXT NOT NULL,
              level TEXT NOT NULL, is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL,
              password_hash TEXT NOT NULL, role TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            )""",
        )
        for statement in statements:
            db.execute(statement)

        if db.execute("SELECT COUNT(*) AS total FROM customers").fetchone()["total"] == 0:
            seed(db)
        if db.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"] == 0:
            from pwdlib import PasswordHash
            password_hash = PasswordHash.recommended().hash("Orbit@2026")
            users = [
                (str(uuid4()), "admin@orbit.local", "Việt Nguyễn", password_hash, "admin", 1, datetime.now().isoformat()),
                (str(uuid4()), "manager@orbit.local", "Ngọc Lan", password_hash, "manager", 1, datetime.now().isoformat()),
                (str(uuid4()), "sales@orbit.local", "Hoàng Nam", password_hash, "sales", 1, datetime.now().isoformat()),
                (str(uuid4()), "viewer@orbit.local", "Minh Anh", password_hash, "viewer", 1, datetime.now().isoformat()),
            ]
            execute_many(db, "INSERT INTO users VALUES(?,?,?,?,?,?,?)", users)


def seed(db: Any) -> None:
    today = date.today()
    seed_customers = [
        Customer(name="Minh Anh", company="Nova Retail", email="minhanh@nova.vn", phone="0901 234 567", status=CustomerStatus.active, value=420_000_000, last_contact=today - timedelta(days=3), owner="Ngọc Lan"),
        Customer(name="Quang Huy", company="GreenTech", email="huy@greentech.vn", phone="0902 456 789", status=CustomerStatus.at_risk, value=280_000_000, last_contact=today - timedelta(days=47), owner="Hoàng Nam"),
        Customer(name="Thu Hà", company="Lumière Studio", email="ha@lumiere.vn", status=CustomerStatus.lead, value=155_000_000, last_contact=today - timedelta(days=12), owner="Ngọc Lan"),
        Customer(name="Đức Long", company="Apex Logistics", email="long@apex.vn", status=CustomerStatus.active, value=630_000_000, last_contact=today - timedelta(days=6), owner="Minh Tuấn"),
        Customer(name="Bảo Trâm", company="Mộc Living", email="tram@mocliving.vn", status=CustomerStatus.at_risk, value=195_000_000, last_contact=today - timedelta(days=38), owner="Hoàng Nam"),
    ]
    execute_many(db, "INSERT INTO customers(id,name,company,email,phone,status,value,last_contact,owner) VALUES(?,?,?,?,?,?,?,?,?)", [
        (str(c.id), c.name, c.company, c.email, c.phone, c.status.value, c.value, c.last_contact.isoformat(), c.owner) for c in seed_customers
    ])
    seed_tasks = [
        BusinessTask(title="Gửi proposal Nova Retail", description="Hoàn thiện scope triển khai quý III", status=TaskStatus.in_progress, priority="high", due_date=today + timedelta(days=2), assignee="Ngọc Lan", customer_id=seed_customers[0].id),
        BusinessTask(title="Follow-up GreenTech", description="Làm rõ lý do giảm tương tác", status=TaskStatus.todo, priority="urgent", due_date=today - timedelta(days=2), assignee="Hoàng Nam", customer_id=seed_customers[1].id),
        BusinessTask(title="Demo giải pháp cho Lumière", status=TaskStatus.todo, priority="medium", due_date=today + timedelta(days=5), assignee="Ngọc Lan", customer_id=seed_customers[2].id),
        BusinessTask(title="Đối soát hợp đồng Apex", status=TaskStatus.done, priority="medium", due_date=today - timedelta(days=1), assignee="Minh Tuấn", customer_id=seed_customers[3].id),
        BusinessTask(title="Gia hạn dịch vụ Mộc Living", status=TaskStatus.in_progress, priority="high", due_date=today + timedelta(days=1), assignee="Hoàng Nam", customer_id=seed_customers[4].id),
    ]
    execute_many(db, "INSERT INTO tasks(id,title,description,status,priority,due_date,assignee,customer_id) VALUES(?,?,?,?,?,?,?,?)", [
        (str(t.id), t.title, t.description, t.status.value, t.priority, t.due_date.isoformat(), t.assignee, str(t.customer_id) if t.customer_id else None) for t in seed_tasks
    ])
    add_notification("Dữ liệu khởi tạo sẵn sàng", "Workspace Orbit đã được thiết lập với dữ liệu mẫu.", "info", db=db)


def row_customer(row: Any) -> Customer:
    return Customer(id=UUID(row["id"]), name=row["name"], company=row["company"], email=row["email"], phone=row["phone"], status=row["status"], value=row["value"], last_contact=date.fromisoformat(row["last_contact"]), owner=row["owner"])


def row_task(row: Any) -> BusinessTask:
    return BusinessTask(id=UUID(row["id"]), title=row["title"], description=row["description"], status=row["status"], priority=row["priority"], due_date=date.fromisoformat(row["due_date"]), assignee=row["assignee"], customer_id=UUID(row["customer_id"]) if row["customer_id"] else None)


def list_customers(status: str | None = None) -> list[Customer]:
    with connect() as db:
        if status is None:
            rows = db.execute("SELECT * FROM customers ORDER BY value DESC").fetchall()
        else:
            rows = db.execute(
                sql("SELECT * FROM customers WHERE status = ? ORDER BY value DESC"),
                (status,),
            ).fetchall()
    return [row_customer(row) for row in rows]


def list_tasks() -> list[BusinessTask]:
    with connect() as db:
        rows = db.execute("SELECT * FROM tasks ORDER BY due_date").fetchall()
    return [row_task(row) for row in rows]


def add_customer(payload: CustomerCreate, actor: str = "system") -> Customer:
    customer = Customer(**payload.model_dump())
    with connect() as db:
        db.execute(sql("INSERT INTO customers(id,name,company,email,phone,status,value,last_contact,owner) VALUES(?,?,?,?,?,?,?,?,?)"), (str(customer.id), customer.name, customer.company, customer.email, customer.phone, customer.status.value, customer.value, customer.last_contact.isoformat(), customer.owner))
    add_audit(actor, "customer.created", "customer", str(customer.id), customer.model_dump(mode="json"))
    return customer


def add_task(payload: TaskCreate, actor: str = "system") -> BusinessTask:
    task = BusinessTask(**payload.model_dump())
    with connect() as db:
        db.execute(sql("INSERT INTO tasks(id,title,description,status,priority,due_date,assignee,customer_id) VALUES(?,?,?,?,?,?,?,?)"), (str(task.id), task.title, task.description, task.status.value, task.priority, task.due_date.isoformat(), task.assignee, str(task.customer_id) if task.customer_id else None))
    add_audit(actor, "task.created", "task", str(task.id), task.model_dump(mode="json"))
    add_notification("Công việc mới", f"{task.title} đã được giao cho {task.assignee}.", "success")
    return task


def update_task_status(task_id: UUID, status: TaskStatus, actor: str = "system") -> BusinessTask | None:
    with connect() as db:
        db.execute(sql("UPDATE tasks SET status=?, updated_at=? WHERE id=?"), (status.value, datetime.now().isoformat(), str(task_id)))
        row = db.execute(sql("SELECT * FROM tasks WHERE id=?"), (str(task_id),)).fetchone()
    if row:
        add_audit(actor, "task.status_changed", "task", str(task_id), {"status": status.value})
        return row_task(row)
    return None


def add_audit(actor: str, action: str, entity_type: str, entity_id: str | None, details: dict) -> None:
    with connect() as db:
        db.execute(sql("INSERT INTO audit_logs VALUES(?,?,?,?,?,?,?)"), (str(uuid4()), actor, action, entity_type, entity_id, json.dumps(details, ensure_ascii=False, default=str), datetime.now().isoformat()))


def list_audits(limit: int = 50) -> list[dict]:
    with connect() as db:
        rows = db.execute(sql("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?"), (limit,)).fetchall()
    return [{**dict(row), "details": json.loads(row["details"])} for row in rows]


def add_notification(title: str, message: str, level: str, db: Any | None = None) -> None:
    owns = db is None
    connection = db or connect()
    connection.execute(sql("INSERT INTO notifications VALUES(?,?,?,?,?,?)"), (str(uuid4()), title, message, level, 0, datetime.now().isoformat()))
    if owns:
        connection.commit(); connection.close()


def list_notifications() -> list[dict]:
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 30").fetchall()]


def get_user_by_email(email: str) -> dict | None:
    with connect() as db:
        row = db.execute(sql("SELECT * FROM users WHERE lower(email)=lower(?)"), (email.strip(),)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with connect() as db:
        row = db.execute(sql("SELECT * FROM users WHERE id=?"), (user_id,)).fetchone()
    return dict(row) if row else None


init_db()
