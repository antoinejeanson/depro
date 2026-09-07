"""Timebox and timebox-series endpoints.

GET /timeboxes materializes series occurrences lazily: occurrences for the
requested range are stored as timebox rows on first load, so past boxes keep
their history even after a series is edited (future occurrences regenerate,
past ones are kept).
"""

import uuid
from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import get_current_user
from app.models import Timebox, TimeboxSeries, User
from app.schemas import (
    SeriesCreate,
    SeriesRead,
    SeriesUpdate,
    TimeboxCreate,
    TimeboxRead,
)
from app.timebox_service import first_occurrence_date, series_occurrences

timeboxes_router = APIRouter(prefix="/timeboxes", tags=["timeboxes"])
series_router = APIRouter(prefix="/timebox-series", tags=["timebox-series"])


def timebox_to_read(tb: Timebox) -> TimeboxRead:
    return TimeboxRead(
        id=tb.id,
        title=tb.title,
        starts_at=tb.starts_at,
        ends_at=tb.ends_at,
        series_id=tb.series_id,
        series_title=tb.series.title if tb.series else None,
    )


def series_to_read(series: TimeboxSeries) -> SeriesRead:
    return SeriesRead(
        id=series.id,
        title=series.title,
        rule=series.rule,
        active=series.active,
        start_date=series.start_date,
        created_at=series.created_at,
    )


def _get_timebox_or_404(db: DBSession, user: User, timebox_id: UUID) -> Timebox:
    tb = db.query(Timebox).filter(Timebox.id == timebox_id, Timebox.user_id == user.id).first()
    if tb is None:
        raise HTTPException(status_code=404, detail="Timebox not found")
    return tb


def _get_series_or_404(db: DBSession, user: User, series_id: UUID) -> TimeboxSeries:
    series = db.query(TimeboxSeries).filter(
        TimeboxSeries.id == series_id, TimeboxSeries.user_id == user.id
    ).first()
    if series is None:
        raise HTTPException(status_code=404, detail="Series not found")
    return series


def _materialize(db: DBSession, user: User, start: date, end: date) -> None:
    """Store missing series occurrences in [start, end) as timebox rows.

    Dedup is per (series, day), not per exact start time: once a day has a
    stored occurrence it is kept as-is (with its original times) even if the
    series rule later changes — past boxes are history.
    """
    series_list = (
        db.query(TimeboxSeries)
        .filter(TimeboxSeries.user_id == user.id, TimeboxSeries.active.is_(True))
        .all()
    )
    added = False
    for series in series_list:
        for day, starts_at, ends_at in series_occurrences(
            series.rule, series.start_date, start, end
        ):
            day_start = datetime.combine(day, time.min)
            exists = (
                db.query(Timebox.id)
                .filter(
                    Timebox.series_id == series.id,
                    Timebox.starts_at >= day_start,
                    Timebox.starts_at < day_start + timedelta(days=1),
                )
                .first()
            )
            if exists is None:
                db.add(
                    Timebox(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        series_id=series.id,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        title=None,
                    )
                )
                added = True
    if added:
        db.commit()


# ---------------------------------------------------------------- timeboxes


@timeboxes_router.get("", response_model=list[TimeboxRead])
def list_timeboxes(
    start: date,
    end: date,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TimeboxRead]:
    """Timeboxes in [start, end) (ISO dates, end exclusive)."""
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be after start")
    _materialize(db, user, start, end)
    boxes = (
        db.query(Timebox)
        .filter(
            Timebox.user_id == user.id,
            Timebox.starts_at >= datetime.combine(start, time.min),
            Timebox.starts_at < datetime.combine(end, time.min),
        )
        .order_by(Timebox.starts_at, Timebox.id)
        .options(selectinload(Timebox.series))
        .all()
    )
    return [timebox_to_read(b) for b in boxes]


@timeboxes_router.post("", status_code=201, response_model=TimeboxRead)
def create_timebox(
    payload: TimeboxCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TimeboxRead:
    tb = Timebox(
        id=uuid.uuid4(),
        user_id=user.id,
        title=payload.title,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(tb)
    db.commit()
    db.refresh(tb)
    return timebox_to_read(tb)


@timeboxes_router.delete("/{timebox_id}", status_code=204)
def delete_timebox(
    timebox_id: UUID,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    tb = _get_timebox_or_404(db, user, timebox_id)
    if tb.series_id is not None:
        raise HTTPException(
            status_code=409,
            detail="This timebox belongs to a series — edit or delete the series instead.",
        )
    db.delete(tb)
    db.commit()


# ---------------------------------------------------------------- series


@series_router.get("", response_model=list[SeriesRead])
def list_series(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SeriesRead]:
    series_list = (
        db.query(TimeboxSeries).filter(TimeboxSeries.user_id == user.id).all()
    )
    return [series_to_read(s) for s in series_list]


@series_router.post("", status_code=201, response_model=SeriesRead)
def create_series(
    payload: SeriesCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SeriesRead:
    rule = payload.rule.model_dump()
    anchor = payload.start_date or first_occurrence_date(rule, date.today())
    series = TimeboxSeries(
        id=uuid.uuid4(),
        user_id=user.id,
        title=payload.title.strip(),
        rule=rule,
        active=True,
        start_date=anchor,
    )
    db.add(series)
    db.commit()
    db.refresh(series)
    return series_to_read(series)


@series_router.put("/{series_id}", response_model=SeriesRead)
def update_series(
    series_id: UUID,
    payload: SeriesUpdate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SeriesRead:
    series = _get_series_or_404(db, user, series_id)
    series.title = payload.title.strip()
    series.rule = payload.rule.model_dump()
    series.active = payload.active
    # Regenerate future occurrences; past ones are kept as history.
    db.query(Timebox).filter(
        Timebox.series_id == series.id, Timebox.starts_at > datetime.now()
    ).delete(synchronize_session=False)
    db.commit()
    db.refresh(series)
    return series_to_read(series)


@series_router.delete("/{series_id}", status_code=204)
def delete_series(
    series_id: UUID,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    series = _get_series_or_404(db, user, series_id)
    db.query(Timebox).filter(Timebox.series_id == series.id).delete(
        synchronize_session=False
    )
    db.delete(series)
    db.commit()

