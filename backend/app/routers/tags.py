"""Tag endpoints."""

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Tag, Task, TaskTag, User
from app.schemas import TagCreate, TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TagRead]:
    tags = db.query(Tag).filter(Tag.user_id == user.id).all()
    open_counts: dict[UUID, int] = dict(
        db.query(TaskTag.tag_id, func.count(Task.id))
        .join(Task, Task.id == TaskTag.task_id)
        .filter(Task.user_id == user.id, Task.status != "done")
        .group_by(TaskTag.tag_id)
        .all()
    )
    return [
        TagRead(id=t.id, name=t.name, task_count=open_counts.get(t.id, 0))
        for t in tags
    ]


@router.post("", status_code=201, response_model=TagRead)
def create_tag(
    payload: TagCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TagRead:
    name = payload.name.strip()
    existing = (
        db.query(Tag)
        .filter(Tag.user_id == user.id, func.lower(Tag.name) == name.lower())
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Tag already exists")
    tag = Tag(id=uuid.uuid4(), user_id=user.id, name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagRead(id=tag.id, name=tag.name, task_count=0)


@router.delete("/{tag_id}", status_code=204)
def delete_tag(
    tag_id: UUID,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == user.id).first()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()
