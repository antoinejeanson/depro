from datetime import date, timedelta

PASSWORD = "supersecret1"


def _register(client, email: str) -> None:
    r = client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201


def _iso(d: date) -> str:
    return d.isoformat()


def _create_one_off(client, day: date, start="09:00:00", end="10:00:00", title=None):
    return client.post(
        "/api/timeboxes",
        json={
            "title": title,
            "starts_at": f"{_iso(day)}T{start}",
            "ends_at": f"{_iso(day)}T{end}",
        },
    )


def _create_series(client, **overrides):
    payload = {
        "title": "Evening work",
        "rule": {
            "frequency": "weekly",
            "interval": 1,
            "weekdays": [0],  # Monday
            "start_time": "19:00",
            "end_time": "21:00",
        },
        "start_date": _iso(date.today() - timedelta(days=14)),
    }
    payload.update(overrides)
    return client.post("/api/timebox-series", json=payload)


def _get_range(client, start: date, end: date):
    return client.get("/api/timeboxes", params={"start": _iso(start), "end": _iso(end)})


TODAY = date.today()


def test_requires_auth(client):
    params = {"start": "2026-09-01", "end": "2026-09-30"}
    assert client.get("/api/timeboxes", params=params).status_code == 401
    assert client.get("/api/timebox-series").status_code == 401


def test_create_one_off(client):
    _register(client, "ada@example.com")
    r = _create_one_off(client, TODAY, title="Focus block")
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Focus block"
    assert body["series_id"] is None
    assert body["series_title"] is None


def test_create_one_off_validation(client):
    _register(client, "ada@example.com")
    assert _create_one_off(client, TODAY, start="10:00:00", end="09:00:00").status_code == 422
    assert _create_one_off(client, TODAY, start="10:00:00", end="10:00:00").status_code == 422


def test_list_range(client):
    _register(client, "ada@example.com")
    _create_one_off(client, TODAY, title="a")
    _create_one_off(client, TODAY + timedelta(days=1), title="b")
    _create_one_off(client, TODAY + timedelta(days=10), title="c")

    r = _get_range(client, TODAY, TODAY + timedelta(days=2))
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert titles == ["a", "b"]  # c is outside [start, end)


def _rule(**overrides):
    base = {"frequency": "daily", "start_time": "09:00", "end_time": "10:00"}
    base.update(overrides)
    return base


def test_series_create_validation(client):
    _register(client, "ada@example.com")
    # weekly without weekdays
    assert _create_series(client, rule=_rule(frequency="weekly")).status_code == 422
    # monthly without day_of_month
    assert _create_series(client, rule=_rule(frequency="monthly")).status_code == 422
    # end before start
    r = _create_series(client, rule=_rule(start_time="10:00", end_time="09:00"))
    assert r.status_code == 422
    # bad time format
    assert _create_series(client, rule=_rule(start_time="9:00")).status_code == 422
    # interval 0
    assert _create_series(
        client,
        rule={"frequency": "daily", "interval": 0, "start_time": "09:00", "end_time": "10:00"},
    ).status_code == 422


def test_series_materialization_is_idempotent(client):
    _register(client, "ada@example.com")
    # Daily series anchored 14 days ago; look at the next 7 days (all future).
    r = _create_series(
        client,
        rule={"frequency": "daily", "start_time": "08:00", "end_time": "09:00"},
        start_date=_iso(TODAY - timedelta(days=14)),
    )
    assert r.status_code == 201

    start = TODAY + timedelta(days=1)
    r1 = _get_range(client, start, start + timedelta(days=7))
    assert len(r1.json()) == 7
    r2 = _get_range(client, start, start + timedelta(days=7))
    assert len(r2.json()) == 7  # no duplicates on reload
    ids1 = {t["id"] for t in r1.json()}
    ids2 = {t["id"] for t in r2.json()}
    assert ids1 == ids2


def test_series_occurrence_times_and_series_title(client):
    _register(client, "ada@example.com")
    series = _create_series(
        client,
        rule={"frequency": "daily", "start_time": "08:30", "end_time": "10:00"},
        start_date=_iso(TODAY - timedelta(days=7)),
    ).json()

    start = TODAY + timedelta(days=1)
    boxes = _get_range(client, start, start + timedelta(days=2)).json()
    assert len(boxes) == 2
    for box in boxes:
        assert box["series_id"] == series["id"]
        assert box["series_title"] == "Evening work"
        assert box["starts_at"].endswith("T08:30:00")
        assert box["ends_at"].endswith("T10:00:00")


def test_update_series_keeps_past_and_regenerates_future(client):
    _register(client, "ada@example.com")
    series = _create_series(
        client,
        rule={"frequency": "daily", "start_time": "09:00", "end_time": "10:00"},
        start_date=_iso(TODAY - timedelta(days=14)),
    ).json()

    past_start = TODAY - timedelta(days=14)
    past = _get_range(client, past_start, TODAY).json()
    assert len(past) == 14

    # Change the rule; future occurrences must use the new times, past kept.
    r = client.put(
        f"/api/timebox-series/{series['id']}",
        json={
            "title": "Evening work",
            "rule": {"frequency": "daily", "start_time": "13:00", "end_time": "14:00"},
            "active": True,
        },
    )
    assert r.status_code == 200

    past_after = _get_range(client, past_start, TODAY).json()
    assert len(past_after) == 14
    assert all(t["starts_at"].endswith("T09:00:00") for t in past_after)

    future = _get_range(client, TODAY + timedelta(days=1), TODAY + timedelta(days=3)).json()
    assert len(future) == 2
    assert all(t["starts_at"].endswith("T13:00:00") for t in future)


def test_update_series_deletes_stored_future_occurrences(client):
    _register(client, "ada@example.com")
    series = _create_series(
        client,
        rule={"frequency": "daily", "start_time": "09:00", "end_time": "10:00"},
        start_date=_iso(TODAY + timedelta(days=1)),
    ).json()

    start = TODAY + timedelta(days=1)
    assert len(_get_range(client, start, start + timedelta(days=7)).json()) == 7

    client.put(
        f"/api/timebox-series/{series['id']}",
        json={
            "title": "Evening work",
            "rule": {"frequency": "daily", "start_time": "13:00", "end_time": "14:00"},
            "active": True,
        },
    )
    boxes = _get_range(client, start, start + timedelta(days=7)).json()
    assert len(boxes) == 7
    assert all(t["starts_at"].endswith("T13:00:00") for t in boxes)


def test_inactive_series_not_materialized(client):
    _register(client, "ada@example.com")
    series = _create_series(
        client,
        rule={"frequency": "daily", "start_time": "09:00", "end_time": "10:00"},
        start_date=_iso(TODAY - timedelta(days=7)),
    ).json()

    client.put(
        f"/api/timebox-series/{series['id']}",
        json={
            "title": "Evening work",
            "rule": {"frequency": "daily", "start_time": "09:00", "end_time": "10:00"},
            "active": False,
        },
    )
    start = TODAY + timedelta(days=1)
    assert _get_range(client, start, start + timedelta(days=7)).json() == []


def test_delete_series_removes_occurrences(client):
    _register(client, "ada@example.com")
    series = _create_series(
        client,
        rule={"frequency": "daily", "start_time": "09:00", "end_time": "10:00"},
        start_date=_iso(TODAY - timedelta(days=7)),
    ).json()
    start = TODAY + timedelta(days=1)
    assert len(_get_range(client, start, start + timedelta(days=7)).json()) == 7

    assert client.delete(f"/api/timebox-series/{series['id']}").status_code == 204
    assert client.get("/api/timebox-series").json() == []
    assert _get_range(client, start, start + timedelta(days=7)).json() == []


def test_delete_one_off_and_series_occurrence(client):
    _register(client, "ada@example.com")
    one_off = _create_one_off(
        client, TODAY + timedelta(days=1), title="solo", start="08:00:00", end="08:30:00"
    ).json()
    series = _create_series(
        client,
        rule={"frequency": "daily", "start_time": "09:00", "end_time": "10:00"},
        start_date=_iso(TODAY + timedelta(days=1)),
    ).json()
    boxes = _get_range(client, TODAY + timedelta(days=1), TODAY + timedelta(days=2)).json()
    assert [b["series_id"] for b in boxes] == [None, series["id"]]
    occ = boxes[1]

    assert client.delete(f"/api/timeboxes/{one_off['id']}").status_code == 204
    r = client.delete(f"/api/timeboxes/{occ['id']}")
    assert r.status_code == 409
    assert "series" in r.json()["detail"].lower()


def test_user_isolation(client):
    _register(client, "ada@example.com")
    one_off = _create_one_off(client, TODAY + timedelta(days=1)).json()
    series = _create_series(client).json()

    client.cookies.clear()
    _register(client, "bob@example.com")

    assert client.get("/api/timebox-series").json() == []
    assert client.get(
        "/api/timeboxes", params={"start": _iso(TODAY), "end": _iso(TODAY + timedelta(days=7))}
    ).json() == []
    assert client.delete(f"/api/timeboxes/{one_off['id']}").status_code == 404
    assert client.delete(f"/api/timebox-series/{series['id']}").status_code == 404

    # Bob's own data works.
    assert _create_one_off(client, TODAY + timedelta(days=2)).status_code == 201

    # Ada's data is intact.
    client.cookies.clear()
    client.post("/api/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert client.get("/api/timebox-series").json()[0]["id"] == series["id"]
