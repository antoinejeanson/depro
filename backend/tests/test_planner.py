"""Unit tests for the cold planner (pure functions, no DB)."""

import uuid
from datetime import datetime, timedelta

from app.models import Task
from app.planner import plan_timebox

NOW = datetime(2026, 9, 7, 12, 0, 0)  # a Monday, midday


def task(
    title="t",
    status="todo",
    priority=None,
    due_at=None,
    progress=0,
    est=None,
    next_due_at=None,
    created=None,
    id=None,
):
    return Task(
        id=id or uuid.uuid4(),
        user_id=uuid.uuid4(),
        title=title,
        status=status,
        priority=priority,
        due_at=due_at,
        progress=progress,
        estimated_minutes=est,
        next_due_at=next_due_at,
        created_at=created or NOW - timedelta(days=1),
    )


def box(starts, ends):
    return type("Box", (), {"starts_at": starts, "ends_at": ends})()


def titles(items):
    return [i.task.title for i in items]


def test_empty():
    assert plan_timebox([], box(NOW, NOW + timedelta(hours=2)), NOW) == []


def test_past_box_has_no_plan():
    t = task("a", est=30)
    assert plan_timebox([t], box(NOW - timedelta(days=2), NOW - timedelta(days=1)), NOW) == []


def test_done_tasks_excluded():
    t = task("done", status="done", due_at=NOW)
    assert plan_timebox([t], box(NOW, NOW + timedelta(hours=1)), NOW) == []


def test_next_due_at_in_future_excluded():
    t = task("not yet", next_due_at=NOW + timedelta(days=1))
    assert plan_timebox([t], box(NOW, NOW + timedelta(hours=1)), NOW) == []


def test_next_due_at_now_or_past_included():
    t = task("ready", next_due_at=NOW)
    items = plan_timebox([t], box(NOW, NOW + timedelta(hours=1)), NOW)
    assert titles(items) == ["ready"]


def test_t1_due_today_first():
    due_today = task("due today", due_at=NOW.replace(hour=18))
    overdue = task("overdue", due_at=NOW - timedelta(days=3))
    tomorrow = task("tomorrow", due_at=NOW + timedelta(days=1))
    items = plan_timebox([tomorrow, due_today, overdue], box(NOW, NOW + timedelta(hours=5)), NOW)
    # T1 = due today + overdue, sorted by due_at asc; tomorrow is T3.
    assert titles(items) == ["overdue", "due today", "tomorrow"]
    assert [i.tier for i in items] == [1, 1, 3]


def test_t1_sort_priority_then_created():
    # Same due_at: higher priority first, then earlier created.
    a = task("a", due_at=NOW, priority=5, created=NOW - timedelta(days=2))
    b = task("b", due_at=NOW, priority=9, created=NOW - timedelta(days=1))
    c = task("c", due_at=NOW, priority=5, created=NOW - timedelta(days=3))
    items = plan_timebox([a, b, c], box(NOW, NOW + timedelta(hours=5)), NOW)
    assert titles(items) == ["b", "c", "a"]


def test_in_progress_due_today_is_t1():
    t = task("ip due today", status="in_progress", progress=50, due_at=NOW.replace(hour=9))
    items = plan_timebox([t], box(NOW, NOW + timedelta(hours=2)), NOW)
    assert [i.tier for i in items] == [1]
    assert "Due today" in items[0].reason


def test_t2_in_progress_sorted_by_progress_desc():
    low = task("low", status="in_progress", progress=10)
    high = task("high", status="in_progress", progress=90)
    mid = task("mid", status="in_progress", progress=50)
    items = plan_timebox([low, high, mid], box(NOW, NOW + timedelta(hours=5)), NOW)
    assert titles(items) == ["high", "mid", "low"]
    assert [i.tier for i in items] == [2, 2, 2]


def test_t2_before_todo():
    ip = task("in progress", status="in_progress", progress=10)
    todo = task("todo", priority=9)
    items = plan_timebox([todo, ip], box(NOW, NOW + timedelta(hours=5)), NOW)
    assert titles(items) == ["in progress", "todo"]
    assert [i.tier for i in items] == [2, 3]


def test_t3_fits_and_shrinks_remaining():
    # 2h box = 120 min. 90 fits, then 45 doesn't (30 left), 30 fits (exactly).
    a = task("90", est=90, priority=9)
    b = task("45", est=45, priority=8)
    c = task("30", est=30, priority=7)
    items = plan_timebox([a, b, c], box(NOW, NOW + timedelta(hours=2)), NOW)
    assert titles(items) == ["90", "30", "45"]
    assert [i.tier for i in items] == [3, 3, 4]


def test_t3_unknown_est_always_added():
    a = task("big", est=300, priority=9)  # doesn't fit a 1h box
    b = task("unknown", est=None, priority=1)
    items = plan_timebox([a, b], box(NOW, NOW + timedelta(hours=1)), NOW)
    # unknown (0 min) is still added as T3; big is T4.
    assert "unknown" in titles(items)
    tiers = {i.task.title: i.tier for i in items}
    assert tiers["unknown"] == 3
    assert tiers["big"] == 4


def test_t3_sort_priority_due_est_created():
    # Same priority None: due first, then est asc, then created.
    a = task("a", est=60, created=NOW - timedelta(days=1))
    b = task("b", est=30, created=NOW - timedelta(days=2))
    c = task("c", est=30, created=NOW - timedelta(days=3))
    d = task("d", due_at=NOW + timedelta(days=1), est=90)
    items = plan_timebox([a, b, c, d], box(NOW, NOW + timedelta(hours=6)), NOW)
    # d has a due date -> before the no-due tasks. Among no-due: est asc then created asc.
    assert titles(items) == ["d", "c", "b", "a"]


def test_t4_reason_mentions_doesnt_fit():
    a = task("big", est=300)
    items = plan_timebox([a], box(NOW, NOW + timedelta(hours=1)), NOW)
    assert items[0].tier == 4
    assert "doesn't fit" in items[0].reason


def test_t1_reason_overdue():
    a = task("old", due_at=NOW - timedelta(days=5))
    items = plan_timebox([a], box(NOW, NOW + timedelta(hours=1)), NOW)
    assert items[0].tier == 1
    assert "Overdue" in items[0].reason


def test_active_box_uses_remaining_capacity():
    # Box started 90 min ago, ends in 30 min. A 60-min task no longer fits.
    starts = NOW - timedelta(minutes=90)
    ends = NOW + timedelta(minutes=30)
    a = task("60", est=60)
    items = plan_timebox([a], box(starts, ends), NOW)
    assert [i.tier for i in items] == [4]


def test_upcoming_box_uses_full_duration():
    # Same box but entirely in the future: full 2h duration, 60-min task fits.
    starts = NOW + timedelta(hours=1)
    ends = NOW + timedelta(hours=3)
    a = task("60", est=60)
    items = plan_timebox([a], box(starts, ends), NOW)
    assert [i.tier for i in items] == [3]


def test_all_tiers_in_order():
    overdue = task("overdue", due_at=NOW - timedelta(days=1))
    ip = task("ip", status="in_progress", progress=50)
    fits = task("fits", est=30, priority=9)
    nofit = task("nofit", est=600, priority=1)
    items = plan_timebox([nofit, fits, ip, overdue], box(NOW, NOW + timedelta(hours=1)), NOW)
    assert [i.tier for i in items] == [1, 2, 3, 4]
    assert titles(items) == ["overdue", "ip", "fits", "nofit"]
