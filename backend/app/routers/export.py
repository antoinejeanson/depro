"""JSON export of the user's data as a single download."""

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.deps import get_current_user
from app.models import Tag, Task, Timebox, TimeboxSeries, User
from app.routers.tasks import task_to_read
from app.routers.timeboxes import series_to_read, timebox_to_read

router = APIRouter()


@router.get("/export")
def export_data(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download everything the user owns: tasks, tags, timeboxes, series."""
    tasks = (
        db.query(Task).filter(Task.user_id == user.id).order_by(Task.created_at).all()
    )
    tags = db.query(Tag).filter(Tag.user_id == user.id).order_by(Tag.name).all()
    timeboxes = (
        db.query(Timebox)
        .filter(Timebox.user_id == user.id)
        .order_by(Timebox.starts_at)
        .all()
    )
    series = (
        db.query(TimeboxSeries)
        .filter(TimeboxSeries.user_id == user.id)
        .order_by(TimeboxSeries.created_at)
        .all()
    )
    payload = {
        "app": "depro",
        "exported_at": datetime.now().isoformat(),
        "user": {"email": user.email},
        "tasks": [task_to_read(t) for t in tasks],
        "tags": [{"id": str(t.id), "name": t.name} for t in tags],
        "timeboxes": [timebox_to_read(t) for t in timeboxes],
        "series": [series_to_read(s) for s in series],
    }
    return JSONResponse(
        content=jsonable_encoder(payload),
        headers={
            "Content-Disposition": (
                f'attachment; filename="depro-export-{datetime.now():%Y-%m-%d}.json"'
            )
        },
    )
