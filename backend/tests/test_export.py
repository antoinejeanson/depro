"""API tests for the JSON export endpoint."""

PASSWORD = "supersecret1"


def _register(client, email: str) -> None:
    r = client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201


def test_export_requires_auth(client):
    assert client.get("/api/export").status_code == 401


def test_export_contains_all_user_data(client):
    _register(client, "ada@example.com")

    r = client.post(
        "/api/tasks",
        json={
            "title": "Water plants",
            "notes": None,
            "priority": 5,
            "due_at": "2026-09-07T19:00:00",
            "estimated_minutes": 15,
            "recurrence": {"frequency": "weekly", "interval": 1, "weekdays": [0]},
            "parents": [],
            "tags": ["home"],
        },
    )
    task = r.json()
    r = client.post(
        "/api/timeboxes",
        json={
            "title": "Focus",
            "starts_at": "2026-09-08T09:00:00",
            "ends_at": "2026-09-08T11:00:00",
        },
    )
    box = r.json()
    r = client.post(
        "/api/timebox-series",
        json={
            "title": "Weekly review",
            "rule": {
                "frequency": "weekly",
                "interval": 1,
                "weekdays": [0],
                "start_time": "17:00",
                "end_time": "17:30",
            },
            "start_date": "2026-09-07",
        },
    )
    assert r.status_code == 201

    r = client.get("/api/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert 'filename="depro-export-' in r.headers["content-disposition"]

    body = r.json()
    assert body["app"] == "depro"
    assert body["user"] == {"email": "ada@example.com"}
    assert [t["title"] for t in body["tasks"]] == ["Water plants"]
    assert body["tasks"][0]["id"] == task["id"]
    assert body["tasks"][0]["recurrence"]["frequency"] == "weekly"
    assert [t["name"] for t in body["tags"]] == ["home"]
    assert [t["id"] for t in body["timeboxes"]] == [box["id"]]
    assert [s["title"] for s in body["series"]] == ["Weekly review"]
    assert "exported_at" in body


def test_export_is_user_scoped(client):
    _register(client, "ada@example.com")
    client.post("/api/tasks", json={"title": "ada task", "parents": [], "tags": []})

    client.cookies.clear()
    _register(client, "bob@example.com")
    body = client.get("/api/export").json()
    assert body["tasks"] == []
    assert body["tags"] == []
    assert body["timeboxes"] == []
    assert body["series"] == []
