"""Task CRUD endpoints."""

import uuid
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import get_current_user
from app.models import Tag, Task, User
from app.schemas import ProgressIn, TaskCreate, TaskRead, TaskUpdate
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
        tags=[tag.name for tag in sorted(task.tags, key=lambda t: t.name.lower())],
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
    task.due_at = payload.due_at
    task.estimated_minutes = payload.estimated_minutes
    _sync_tags(db, task, payload.tags, user.id)
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
