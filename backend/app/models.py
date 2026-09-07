"""SQLAlchemy models."""

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Session(Base):
    """A browser login session.

    The cookie holds the raw token; only its SHA-256 hash is stored, so a
    database leak does not leak valid sessions.
    """

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped["User"] = relationship(back_populates="sessions")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    priority: Mapped[int | None] = mapped_column(nullable=True)  # 0-9, 9 highest
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo | in_progress | done
    progress: Mapped[int] = mapped_column(default=0)  # 0-100
    estimated_minutes: Mapped[int | None] = mapped_column(nullable=True)
    # Recurrence (M5): rule JSON + when a recurring task becomes eligible again.
    recurrence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary="task_tags",
        back_populates="tasks",
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50))

    tasks: Mapped[list["Task"]] = relationship(
        secondary="task_tags",
        back_populates="tags",
    )


class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class TimeboxSeries(Base):
    """A regularly spaced series of timeboxes (e.g. every Monday 19:00-21:00).

    `rule` is a validated JSON dict:
      {"frequency": "daily"|"weekly"|"monthly",
       "interval": int >= 1,            # every N
       "weekdays": [0-6],               # weekly only, 0 = Monday
       "day_of_month": int | null,      # monthly only, 1-31
       "start_time": "HH:MM", "end_time": "HH:MM"}
    `start_date` anchors the interval counting (occurrence #0 is the first
    rule match on/after it).
    """

    __tablename__ = "timebox_series"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(100))
    rule: Mapped[dict] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    timeboxes: Mapped[list["Timebox"]] = relationship(
        back_populates="series",
        cascade="all, delete-orphan",
    )


class Timebox(Base):
    """A committed work block. One-offs have series_id = None; rows with a
    series_id are materialized occurrences of their series."""

    __tablename__ = "timeboxes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    series_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("timebox_series.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)

    series: Mapped[TimeboxSeries | None] = relationship(back_populates="timeboxes")
