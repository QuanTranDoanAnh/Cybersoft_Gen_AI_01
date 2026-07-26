from fastapi.testclient import TestClient
import pytest

from app import copilot as copilot_module
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def login_admin():
    response = client.post("/api/auth/login", json={"email": "admin@orbit.local", "password": "Orbit@2026"})
    assert response.status_code == 200


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_and_lists():
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["active_customers"] > 0
    assert len(client.get("/api/customers").json()) >= 5
    assert len(client.get("/api/tasks").json()) >= 5


def test_copilot_local_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/copilot", json={"message": "Có task nào quá hạn?"})
    assert response.status_code == 200
    assert response.json()["traces"][0]["tool"] == "get_overdue_tasks"


def test_execute_follow_up_approval():
    customer = client.get("/api/customers").json()[0]
    response = client.post("/api/approvals/execute", json={
        "action": "create_follow_up_task",
        "payload": {
            "title": "Follow-up approval test",
            "description": "Test approval workflow",
            "assignee": "Ngọc Lan",
            "due_date": "2026-07-20",
            "customer_id": customer["id"],
            "priority": "high",
        },
    })
    assert response.status_code == 201
    assert response.json()["status"] == "approved"
    assert response.json()["task"]["title"] == "Follow-up approval test"


def test_reject_past_due_date():
    customer = client.get("/api/customers").json()[0]
    response = client.post("/api/approvals/execute", json={
        "action": "create_follow_up_task",
        "payload": {
            "title": "Invalid task",
            "description": "Past date",
            "assignee": "Ngọc Lan",
            "due_date": "2026-01-01",
            "customer_id": customer["id"],
        },
    })
    assert response.status_code == 422


def test_viewer_cannot_create_customer():
    login = client.post("/api/auth/login", json={"email": "viewer@orbit.local", "password": "Orbit@2026"})
    assert login.status_code == 200
    response = client.post("/api/customers", json={
        "name": "Viewer Test", "company": "No Write", "email": "viewer@example.com",
        "last_contact": "2026-07-12", "owner": "Nobody",
    })
    assert response.status_code == 403


def test_reports_notifications_and_audit():
    assert client.get("/api/reports/operations").status_code == 200
    assert client.get("/api/notifications").status_code == 200
    audit = client.get("/api/audit-logs")
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)


def test_copilot_returns_visualizations(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/copilot", json={"message": "Cho tôi báo cáo thống kê và biểu đồ vận hành"})
    assert response.status_code == 200
    body = response.json()
    assert body["traces"][0]["tool"] == "get_operations_report"
    assert {chart["type"] for chart in body["visualizations"]} == {"donut", "bar"}
    assert all(chart["data"] for chart in body["visualizations"])


def test_login_logout_and_protected_route():
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/dashboard").status_code == 401


def test_invalid_login():
    response = client.post("/api/auth/login", json={"email": "admin@orbit.local", "password": "wrong"})
    assert response.status_code == 401


def test_gpt5_model_does_not_force_temperature(monkeypatch):
    captured = {}

    class FakeModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return type("Message", (), {"content": "OK", "tool_calls": []})()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    monkeypatch.setattr(copilot_module, "ChatOpenAI", FakeModel)

    response = copilot_module.run_copilot("Tóm tắt dashboard")

    assert response.answer == "OK"
    assert captured["model"] == "gpt-5-mini"
    assert "temperature" not in captured


def test_web_research_uses_current_openai_web_search_tool(monkeypatch):
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"output_text": "Tin AI CRM mới nhất"})()

    class FakeOpenAI:
        def __init__(self):
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    monkeypatch.setattr(copilot_module, "OpenAI", FakeOpenAI)

    result = copilot_module.research_web.invoke({"query": "tin mới về AI CRM"})

    assert result == "Tin AI CRM mới nhất"
    assert captured["model"] == "gpt-5-mini"
    assert captured["tools"] == [{"type": "web_search"}]
