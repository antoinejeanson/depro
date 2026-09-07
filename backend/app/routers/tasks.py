"""Task CRUD endpoints."""

import uuid
from collections import deque
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import get_current_user
from app.models import Tag, Task, TaskDependency, User
from app.schemas import (
    ParentRead,
    ProgressIn,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)
from app.task_service import apply_progress, complete_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


def task_to_read(task: Task) -> TaskRead:
    return TaskRead(
        id=task.id,
        title=task.title,
        notes=task.notes,
        priority=task.priority,
        due_at=task.due_at,
        status=task.status,
        progress=task.progress,
        estimated_minutes=task.estimated_minutes,
        recurrence=task.recurrence,
        next_due_at=task.next_due_at,
        tags=[tag.name for tag in sorted(task.tags, key=lambda t: t.name.lower())],
        parents=[
            ParentRead(id=p.id, title=p.title, status=p.status)
            for p in sorted(task.parents, key=lambda p: (p.title.lower(), p.id))
        ],
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
    )


def _get_task_or_404(db: DBSession, user: User, task_id: UUID) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _sync_tags(db: DBSession, task: Task, names: list[str], user_id: UUID) -> None:
    """Replace the task's tags, creating missing ones (case-insensitive)."""
    wanted: list[Tag] = []
    seen: set[str] = set()
    for raw in names:
        name = raw.strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        tag = (
            db.query(Tag)
            .filter(Tag.user_id == user_id, func.lower(Tag.name) == name.lower())
            .first()
        )
        if tag is None:
            tag = Tag(id=uuid.uuid4(), user_id=user_id, name=name)
            db.add(tag)
            db.flush()
        wanted.append(tag)
    task.tags = wanted


def _would_create_cycle(db: DBSession, task_id: UUID, parent_ids: list[UUID]) -> bool:
    """True if following the parent links from any of `parent_ids` reaches
    `task_id` (i.e. adding task_id -> parent edges would form a cycle)."""
    visited: set[UUID] = set()
    queue = deque(parent_ids)
    while queue:
        current = queue.popleft()
        if current == task_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        for dep in db.query(TaskDependency).filter(
            TaskDependency.child_id == current
        ):
            queue.append(dep.parent_id)
    return False


def _validate_parents(
    db: DBSession, user: User, task_id: UUID, parent_ids: list[UUID]
) -> list[UUID]:
    """Check parent ids (existence, self-dependency, cycles); return deduped."""
    unique = list(dict.fromkeys(parent_ids))
    if task_id in unique:
        raise HTTPException(status_code=422, detail="A task cannot be its own parent")
    if not unique:
        return unique
    existing = {
        row[0]
        for row in db.query(Task.id)
        .filter(Task.id.in_(unique), Task.user_id == user.id)
        .all()
    }
    if len(existing) != len(unique):
        raise HTTPException(status_code=422, detail="Parent task not found")
    if _would_create_cycle(db, task_id, unique):
        raise HTTPException(
            status_code=422, detail="These parents would create a cycle"
        )
    return unique


def _sync_parents(db: DBSession, task: Task, parent_ids: list[UUID]) -> None:
    """Replace the task's parent links."""
    if not parent_ids:
        task.parents = []
        return
    rows = db.query(Task).filter(Task.id.in_(parent_ids)).all()
    by_id = {p.id: p for p in rows}
    task.parents = [by_id[pid] for pid in parent_ids]


def _apply_recurrence(task: Task, recurrence, due_at: datetime | None) -> None:
    """Set the task's recurrence, re-anchoring the schedule when needed.

    A new/changed rule (or a moved due date) re-anchors: the due date is
    occurrence #0, so `next_due_at` becomes the due date itself. Otherwise
    the pending `next_due_at` is kept.
    """
    if recurrence is None:
        task.recurrence = None
        task.next_due_at = None
        return
    rule = recurrence.model_dump()
    schedule_changed = (
        task.due_at != due_at or task.recurrence is None or task.recurrence != rule
    )
    task.recurrence = rule
    if schedule_changed:
        task.next_due_at = due_at


def _sort_key(task: Task):
    # due_at asc (nulls last), priority desc (nulls last), newest first.
    return (
        task.due_at is None,
        task.due_at or datetime.min,
        -(task.priority if task.priority is not None else 0),
        -task.created_at.timestamp(),
    )


@router.get("", response_model=list[TaskRead])
def list_tasks(
    q: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TaskRead]:
    query = db.query(Task).filter(Task.user_id == user.id)
    if q:
        query = query.filter(Task.title.ilike(f"%{q}%"))
    if status:
        query = query.filter(Task.status == status)
    if tag:
        query = query.join(Task.tags).filter(func.lower(Tag.name) == tag.lower())
    tasks = query.options(selectinload(Task.tags)).all()
    return [task_to_read(t) for t in sorted(tasks, key=_sort_key)]


@router.post("", status_code=201, response_model=TaskRead)
def create_task(
    payload: TaskCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskRead:
    task = Task(
        id=uuid.uuid4(),
        user_id=user.id,
        title=payload.title.strip(),
        notes=payload.notes,
        priority=payload.priority,
        due_at=payload.due_at,
        estimated_minutes=payload.estimated_minutes,
    )
    db.add(task)
    _sync_tags(db, task, payload.tags, user.id)
    _validate_parents(db, user, task.id, payload.parents)
    _sync_parents(db, task, payload.parents)
    # Recurring tasks anchor their schedule at the due date (occurrence #0).
    if payload.recurrence is not None:
        task.recurrence = payload.recurrence.model_dump()
        task.next_due_at = payload.due_at
    db.commit()
    db.refresh(task)
    return task_to_read(task)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: UUID,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskRead:
    return task_to_read(_get_task_or_404(db, user, task_id))


@router.put("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskRead:
    task = _get_task_or_404(db, user, task_id)
    task.title = payload.title.strip()
    task.notes = payload.notes
    task.priority = payload.priority
    task.estimated_minutes = payload.estimated_minutes
    _sync_tags(db, task, payload.tags, user.id)
    _validate_parents(db, user, task.id, payload.parents)
    _sync_parents(db, task, payload.parents)
    _apply_recurrence(task, payload.recurrence, payload.due_at)
    task.due_at = payload.due_at
    db.commit()
    db.refresh(task)
    return task_to_read(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: UUID,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    task = _get_task_or_404(db, user, task_id)
    db.delete(task)
    db.commit()


@router.post("/{task_id}/progress", response_model=TaskRead)
def set_progress(
    task_id: UUID,
    payload: ProgressIn,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskRead:
    task = _get_task_or_404(db, user, task_id)
    apply_progress(task, payload.progress)
    db.commit()
    db.refresh(task)
    return task_to_read(task)


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete(
    task_id: UUID,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskRead:
    task = _get_task_or_404(db, user, task_id)
    complete_task(task)
    db.commit()
    db.refresh(task)
    return task_to_read(task)
