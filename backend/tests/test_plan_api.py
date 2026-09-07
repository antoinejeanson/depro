"""API tests for the live plan: /now, /timeboxes/{id}/plan, /spontaneous."""

import uuid
from datetime import date, datetime, time, timedelta

from app.models import Task

PASSWORD = "supersecret1"


def _register(client, email: str) -> None:
    r = client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201


def _task(client, **overrides):
    payload = {
        "title": "task",
        "notes": None,
        "priority": None,
        "due_at": None,
        "estimated_minutes": None,
        "tags": [],
    }
    payload.update(overrides)
    return client.post("/api/tasks", json=payload).json()


def _active_box(client, minutes=60, title="Focus"):
    now = datetime.now()
    r = client.post(
        "/api/timeboxes",
        json={
            "title": title,
            "starts_at": (now - timedelta(minutes=5)).replace(microsecond=0).isoformat(),
            "ends_at": (now + timedelta(minutes=minutes)).replace(microsecond=0).isoformat(),
        },
    )
    assert r.status_code == 201
    return r.json()


def _titles(plan):
    return [e["task"]["title"] for e in plan]


def test_plan_endpoints_require_auth(client):
    assert client.get("/api/timeboxes/now").status_code == 401
    assert client.post("/api/timeboxes/spontaneous", json={"minutes": 30}).status_code == 401
    assert client.get("/api/timeboxes/abc/plan").status_code == 401


def test_now_idle_when_no_active_box(client):
    _register(client, "ada@example.com")
    body = client.get("/api/timeboxes/now").json()
    assert body["state"] == "idle"
    assert body["timebox"] is None
    assert body["plan"] == []
    assert body["current"] is None


def test_now_returns_active_box_current_and_plan(client):
    _register(client, "ada@example.com")
    _task(client, title="overdue", due_at="2026-09-01T10:00:00", estimated_minutes=30)
    _task(client, title="later", estimated_minutes=30)
    box = _active_box(client, minutes=90)

    body = client.get("/api/timeboxes/now").json()
    assert body["state"] == "active"
    assert body["timebox"]["id"] == box["id"]
    assert body["current"]["task"]["title"] == "overdue"
    assert body["current"]["tier"] == 1
    assert body["current"]["reason"].startswith("Overdue")
    assert _titles(body["plan"]) == ["overdue", "later"]
    assert [e["tier"] for e in body["plan"]] == [1, 3]


def test_now_ignores_other_users_boxes(client):
    _register(client, "ada@example.com")
    _active_box(client)

    client.cookies.clear()
    _register(client, "bob@example.com")
    body = client.get("/api/timeboxes/now").json()
    assert body["state"] == "idle"


def test_spontaneous_creates_box_starting_now(client):
    _register(client, "ada@example.com")
    before = datetime.now()
    r = client.post("/api/timeboxes/spontaneous", json={"minutes": 45})
    assert r.status_code == 201
    body = r.json()
    starts = datetime.fromisoformat(body["starts_at"])
    ends = datetime.fromisoformat(body["ends_at"])
    assert before.replace(microsecond=0) <= starts <= datetime.now()
    assert (ends - starts).total_seconds() == 45 * 60
    assert body["series_id"] is None

    # It is immediately the active box.
    now_body = client.get("/api/timeboxes/now").json()
    assert now_body["timebox"]["id"] == body["id"]


def test_spontaneous_validation(client):
    _register(client, "ada@example.com")
    assert client.post("/api/timeboxes/spontaneous", json={"minutes": 1}).status_code == 422
    assert client.post("/api/timeboxes/spontaneous", json={"minutes": 0}).status_code == 422
    assert client.post("/api/timeboxes/spontaneous", json={"minutes": 9999}).status_code == 422


def test_plan_upcoming_box(client):
    _register(client, "ada@example.com")
    _task(client, title="a", estimated_minutes=30)
    tomorrow = date.today() + timedelta(days=1)
    r = client.post(
        "/api/timeboxes",
        json={
            "title": "Tomorrow",
            "starts_at": f"{tomorrow}T09:00:00",
            "ends_at": f"{tomorrow}T11:00:00",
        },
    )
    box = r.json()
    body = client.get(f"/api/timeboxes/{box['id']}/plan").json()
    assert body["state"] == "upcoming"
    assert body["completed"] == []
    assert _titles(body["plan"]) == ["a"]
    assert body["plan"][0]["tier"] == 3


def test_plan_past_box_returns_completed(client, test_db):
    _register(client, "ada@example.com")
    t = _task(client, title="done yesterday")
    start = (date.today() - timedelta(days=1)).isoformat()
    r = client.post(
        "/api/timeboxes",
        json={
            "title": "Yesterday",
            "starts_at": f"{start}T09:00:00",
            "ends_at": f"{start}T10:00:00",
        },
    )
    box = r.json()

    # Mark the task completed inside the window (API sets completed_at=now,
    # so set it directly).
    db = test_db()
    task = db.query(Task).filter(Task.id == uuid.UUID(t["id"])).first()
    task.status = "done"
    yesterday = date.today() - timedelta(days=1)
    task.completed_at = datetime.combine(yesterday, time(9, 30))  # inside 09:00-10:00
    db.commit()

    body = client.get(f"/api/timeboxes/{box['id']}/plan").json()
    assert body["state"] == "past"
    assert body["plan"] == []
    assert [c["title"] for c in body["completed"]] == ["done yesterday"]


def test_plan_is_live_after_completion(client):
    _register(client, "ada@example.com")
    a = _task(client, title="first", due_at="2026-09-01T10:00:00")
    _task(client, title="second", due_at="2026-09-02T10:00:00")
    _active_box(client)

    body = client.get("/api/timeboxes/now").json()
    assert body["current"]["task"]["title"] == "first"

    # Completing the current task shifts the live plan to the next one.
    r = client.post(f"/api/tasks/{a['id']}/complete")
    assert r.status_code == 200

    body = client.get("/api/timeboxes/now").json()
    assert body["current"]["task"]["title"] == "second"
    assert "first" not in _titles(body["plan"])


def test_plan_reflects_priority_change(client):
    _register(client, "ada@example.com")
    a = _task(client, title="low", priority=1, estimated_minutes=10)
    _task(client, title="high", priority=9, estimated_minutes=10)
    _active_box(client)

    body = client.get("/api/timeboxes/now").json()
    assert _titles(body["plan"]) == ["high", "low"]

    # Raising a task's priority is the only way to influence the plan.
    r = client.put(f"/api/tasks/{a['id']}", json={**a, "priority": 9})
    assert r.status_code == 200
    # Same priority now: tie broken by due_at (both null) then est then created;
    # 'low' was created first, so it comes first.
    body = client.get("/api/timeboxes/now").json()
    assert _titles(body["plan"]) == ["low", "high"]


def test_plan_capacity_tiers(client):
    _register(client, "ada@example.com")
    # 30-min box: a 20-min task fits, a 60-min task doesn't.
    _task(client, title="fits", priority=9, estimated_minutes=20)
    _task(client, title="nofit", priority=8, estimated_minutes=60)
    _active_box(client, minutes=30)

    body = client.get("/api/timeboxes/now").json()
    tiers = {e["task"]["title"]: e["tier"] for e in body["plan"]}
    assert tiers == {"fits": 3, "nofit": 4}
    assert "doesn't fit" in body["plan"][1]["reason"]


def test_plan_404_and_isolation(client):
    _register(client, "ada@example.com")
    box = _active_box(client)

    client.cookies.clear()
    _register(client, "bob@example.com")
    assert client.get(f"/api/timeboxes/{box['id']}/plan").status_code == 404
    assert client.get(f"/api/timeboxes/{uuid.uuid4()}/plan").status_code == 404
