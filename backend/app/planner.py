"""The cold planner.

The plan is a pure function of (tasks, timebox, now): never stored, never
user-editable. The only way to influence a plan is to change a task's
attributes (priority, due date, estimate, status).

Tiers, in order:
  T1  Overdue / due today (due_at <= end of today)
  T2  In progress
  T3  To-do, fits remaining capacity (est <= remaining, or est unknown)
  T4  To-do, doesn't fit (est > remaining)

Fill rule: T1 and T2 are always included (commitments and momentum). To-dos
are walked in sort order; each either fits the remaining capacity (T3, and
shrinks it) or doesn't (T4). All T3s precede all T4s. Unknown estimates
count as 0 minutes but are still added.

Capacity is the timebox's full duration for upcoming boxes, and its
*remaining* wall-clock time for active boxes (ends_at - now) — which is why
the frontend refetches the plan every minute: remaining capacity shrinks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models import Task

MIN = datetime.min


@dataclass
class PlanItem:
    task: Task
    tier: int
    reason: str


def _est(t: Task) -> int:
    return t.estimated_minutes if t.estimated_minutes is not None else 0


def _prio_key(t: Task):
    # priority descending, nulls last
    return (t.priority is None, -(t.priority or 0))


def _due_key(t: Task):
    # due_at ascending, nulls last
    return (t.due_at is None, t.due_at or MIN)


def _est_key(t: Task):
    # estimated_minutes ascending, nulls last
    return (t.estimated_minutes is None, t.estimated_minutes or 0)


def _t1_reason(t: Task, now: datetime) -> str:
    if t.due_at is None:
        return "Due today"
    if t.due_at.date() < now.date():
        return f"Overdue (due {t.due_at:%b %d})"
    return f"Due today ({t.due_at:%H:%M})"


def _t3_reason(t: Task, est: int) -> str:
    parts = []
    if t.priority is not None:
        parts.append(f"Priority {t.priority}")
    parts.append(f"fits in {est} min" if est else "no estimate")
    return ", ".join(parts)


def _t4_reason(t: Task, est: int) -> str:
    parts = []
    if t.priority is not None:
        parts.append(f"Priority {t.priority}")
    parts.append(f"doesn't fit ({est} min)")
    return ", ".join(parts)


def plan_timebox(
    tasks: list[Task], tb, now: datetime, blocked: set | None = None
) -> list[PlanItem]:
    """Compute the live plan for a timebox. Past boxes get no plan.

    `blocked` is the set of task ids with at least one parent not done;
    the planner never auto-selects blocked tasks (the user can still advance
    them manually in the task list).
    """
    if tb.ends_at <= now:
        return []
    blocked = blocked or set()

    if tb.starts_at > now:
        capacity = (tb.ends_at - tb.starts_at).total_seconds() // 60
    else:
        capacity = (tb.ends_at - now).total_seconds() // 60
    capacity = max(0, int(capacity))
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=0)

    # Eligible = not done AND (no next_due_at or next_due_at <= now)
    # AND not blocked by an unfinished parent.
    eligible = [
        t
        for t in tasks
        if t.status != "done"
        and (t.next_due_at is None or t.next_due_at <= now)
        and t.id not in blocked
    ]

    t1 = [t for t in eligible if t.due_at is not None and t.due_at <= end_of_today]
    t1.sort(key=lambda t: (t.due_at, _prio_key(t), t.created_at, str(t.id)))
    t1_ids = {t.id for t in t1}

    t2 = [t for t in eligible if t.status == "in_progress" and t.id not in t1_ids]
    t2.sort(key=lambda t: (-t.progress, _prio_key(t), t.created_at, str(t.id)))

    todo = [t for t in eligible if t.status == "todo" and t.id not in t1_ids]
    todo.sort(key=lambda t: (_prio_key(t), _due_key(t), _est_key(t), t.created_at, str(t.id)))

    items: list[PlanItem] = []
    remaining = capacity
    for t in t1:
        items.append(PlanItem(t, 1, _t1_reason(t, now)))
        remaining -= _est(t)
    for t in t2:
        items.append(PlanItem(t, 2, f"In progress — {t.progress}%"))
        remaining -= _est(t)

    t3: list[PlanItem] = []
    t4: list[PlanItem] = []
    for t in todo:
        est = _est(t)
        if est == 0 or est <= remaining:
            t3.append(PlanItem(t, 3, _t3_reason(t, est)))
            remaining -= est
        else:
            t4.append(PlanItem(t, 4, _t4_reason(t, est)))
    items.extend(t3)
    items.extend(t4)
    return items
