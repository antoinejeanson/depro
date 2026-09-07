PASSWORD = "supersecret1"


def _register(client, email: str) -> None:
    r = client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201


def _create_task(client, **overrides):
    payload = {
        "title": "Buy groceries",
        "notes": "milk, eggs",
        "priority": 5,
        "due_at": "2026-09-10T18:00:00",
        "estimated_minutes": 30,
        "tags": ["errands", "home"],
    }
    payload.update(overrides)
    return client.post("/api/tasks", json=payload)


def test_requires_auth(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/api/tags").status_code == 401


def test_create_task(client):
    _register(client, "ada@example.com")
    r = _create_task(client)
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Buy groceries"
    assert body["priority"] == 5
    assert body["due_at"] == "2026-09-10T18:00:00"
    assert body["estimated_minutes"] == 30
    assert body["status"] == "todo"
    assert body["progress"] == 0
    assert body["tags"] == ["errands", "home"]
    assert body["completed_at"] is None


def test_create_task_minimal(client):
    _register(client, "ada@example.com")
    r = _create_task(client, title="Only a title", notes=None, priority=None,
                     due_at=None, estimated_minutes=None, tags=[])
    assert r.status_code == 201
    body = r.json()
    assert body["priority"] is None
    assert body["due_at"] is None
    assert body["estimated_minutes"] is None
    assert body["tags"] == []


def test_create_task_validation(client):
    _register(client, "ada@example.com")
    assert _create_task(client, title="").status_code == 422
    assert _create_task(client, priority=10).status_code == 422
    assert _create_task(client, priority=-1).status_code == 422
    assert _create_task(client, estimated_minutes=0).status_code == 422


def test_list_tasks_filters(client):
    _register(client, "ada@example.com")
    _create_task(client, title="Buy groceries", tags=["errands"])
    _create_task(client, title="Write report", priority=9, tags=["work"])
    _create_task(client, title="Fix bike", tags=["home"])

    assert len(client.get("/api/tasks").json()) == 3
    assert len(client.get("/api/tasks", params={"q": "buy"}).json()) == 1
    assert len(client.get("/api/tasks", params={"q": "BUY"}).json()) == 1
    assert len(client.get("/api/tasks", params={"tag": "work"}).json()) == 1
    assert len(client.get("/api/tasks", params={"tag": "WORK"}).json()) == 1
    assert len(client.get("/api/tasks", params={"q": "nope"}).json()) == 0


def test_list_tasks_default_order(client):
    _register(client, "ada@example.com")
    _create_task(client, title="No due date")
    _create_task(client, title="Due soon", due_at="2026-09-01T09:00:00", priority=1)
    _create_task(client, title="Due soon, top priority",
                 due_at="2026-09-01T09:00:00", priority=9)
    titles = [t["title"] for t in client.get("/api/tasks").json()]
    assert titles == ["Due soon, top priority", "Due soon", "No due date"]


def test_status_filter(client):
    _register(client, "ada@example.com")
    task_id = _create_task(client).json()["id"]
    client.post(f"/api/tasks/{task_id}/progress", json={"progress": 50})
    assert len(client.get("/api/tasks", params={"status": "in_progress"}).json()) == 1
    assert len(client.get("/api/tasks", params={"status": "todo"}).json()) == 0
    assert len(client.get("/api/tasks", params={"status": "done"}).json()) == 0


def test_get_and_update_task(client):
    _register(client, "ada@example.com")
    task_id = _create_task(client).json()["id"]

    got = client.get(f"/api/tasks/{task_id}")
    assert got.status_code == 200

    r = client.put(
        f"/api/tasks/{task_id}",
        json={
            "title": "Buy more groceries",
            "notes": None,
            "priority": 7,
            "due_at": None,
            "estimated_minutes": 45,
            "tags": ["errands"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Buy more groceries"
    assert body["priority"] == 7
    assert body["due_at"] is None
    assert body["tags"] == ["errands"]


def test_delete_task(client):
    _register(client, "ada@example.com")
    task_id = _create_task(client).json()["id"]
    assert client.delete(f"/api/tasks/{task_id}").status_code == 204
    assert client.get(f"/api/tasks/{task_id}").status_code == 404


def test_progress_endpoint(client):
    _register(client, "ada@example.com")
    task_id = _create_task(client).json()["id"]

    r = client.post(f"/api/tasks/{task_id}/progress", json={"progress": 50})
    assert r.json()["status"] == "in_progress"
    assert r.json()["progress"] == 50

    r = client.post(f"/api/tasks/{task_id}/progress", json={"progress": 100})
    assert r.json()["status"] == "done"
    assert r.json()["completed_at"] is not None

    r = client.post(f"/api/tasks/{task_id}/progress", json={"progress": 0})
    assert r.json()["status"] == "todo"
    assert r.json()["completed_at"] is None


def test_complete_endpoint(client):
    _register(client, "ada@example.com")
    task_id = _create_task(client).json()["id"]
    r = client.post(f"/api/tasks/{task_id}/complete")
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["progress"] == 100


def test_tags_endpoints(client):
    _register(client, "ada@example.com")
    _create_task(client)  # tags: errands, home

    r = client.get("/api/tags")
    assert r.status_code == 200
    by_name = {t["name"]: t for t in r.json()}
    assert by_name["errands"]["task_count"] == 1
    assert by_name["home"]["task_count"] == 1

    # Completing the task drops the open count to 0.
    task_id = _create_task(client, title="Second").json()["id"]
    client.post(f"/api/tasks/{task_id}/complete")
    by_name = {t["name"]: t for t in client.get("/api/tags").json()}
    assert by_name["errands"]["task_count"] == 1
    assert by_name["home"]["task_count"] == 1


def test_tag_create_and_delete(client):
    _register(client, "ada@example.com")
    _create_task(client)

    r = client.post("/api/tags", json={"name": "Work"})
    assert r.status_code == 201
    work_id = r.json()["id"]
    assert client.post("/api/tags", json={"name": "work"}).status_code == 409

    # Deleting the tag detaches it from tasks but keeps the tasks.
    assert client.delete(f"/api/tags/{work_id}").status_code == 204
    assert len(client.get("/api/tasks").json()) == 1
    assert client.delete(f"/api/tags/{work_id}").status_code == 404


def test_user_isolation(client):
    _register(client, "ada@example.com")
    task_id = _create_task(client).json()["id"]
    tag_id = client.get("/api/tags").json()[0]["id"]

    client.cookies.clear()
    _register(client, "bob@example.com")

    # Bob sees nothing of Ada's.
    assert client.get("/api/tasks").json() == []
    assert client.get(f"/api/tasks/{task_id}").status_code == 404
    assert client.put(
        f"/api/tasks/{task_id}",
        json={"title": "hacked", "notes": None, "priority": None,
              "due_at": None, "estimated_minutes": None, "tags": []},
    ).status_code == 404
    assert client.delete(f"/api/tasks/{task_id}").status_code == 404
    assert client.delete(f"/api/tags/{tag_id}").status_code == 404

    # Bob can use the same tag name.
    assert client.post("/api/tags", json={"name": "errands"}).status_code == 201

    # Ada's task is intact.
    client.cookies.clear()
    client.post("/api/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert client.get(f"/api/tasks/{task_id}").status_code == 200
