"""Pydantic schemas."""

import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class UserRead(BaseModel):
    id: UUID
    email: str
    created_at: datetime


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class TagRead(BaseModel):
    id: UUID
    name: str
    task_count: int = 0


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)
    priority: int | None = Field(default=None, ge=0, le=9)
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, gt=0)


class TaskCreate(TaskBase):
    tags: list[str] = []


class TaskUpdate(TaskBase):
    tags: list[str] = []


class TaskRead(BaseModel):
    id: UUID
    title: str
    notes: str | None
    priority: int | None
    due_at: datetime | None
    status: str
    progress: int
    estimated_minutes: int | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class ProgressIn(BaseModel):
    progress: int = Field(ge=0, le=100)


TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class SeriesRule(BaseModel):
    frequency: Literal["daily", "weekly", "monthly"]
    interval: int = Field(default=1, ge=1, le=365)
    weekdays: list[int] = Field(default_factory=list)  # 0 = Monday .. 6 = Sunday
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    start_time: str
    end_time: str

    @field_validator("start_time", "end_time")
    @classmethod
    def valid_hh_mm(cls, v: str) -> str:
        if not TIME_RE.match(v):
            raise ValueError("time must be HH:MM in 24h format")
        return v

    @model_validator(mode="after")
    def check_rule(self) -> "SeriesRule":
        if self.frequency == "weekly":
            if not self.weekdays:
                raise ValueError("weekly series need at least one weekday")
            if any(w < 0 or w > 6 for w in self.weekdays):
                raise ValueError("weekdays must be between 0 (Mon) and 6 (Sun)")
        if self.frequency == "monthly" and self.day_of_month is None:
            raise ValueError("monthly series need a day of month (1-31)")
        if self.start_time >= self.end_time:
            raise ValueError("end time must be after start time")
        return self


class SeriesCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    rule: SeriesRule
    start_date: date | None = None


class SeriesUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    rule: SeriesRule
    active: bool


class SeriesRead(BaseModel):
    id: UUID
    title: str
    rule: SeriesRule
    active: bool
    start_date: date
    created_at: datetime


class TimeboxCreate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def check_range(self) -> "TimeboxCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class TimeboxRead(BaseModel):
    id: UUID
    title: str | None
    starts_at: datetime
    ends_at: datetime
    series_id: UUID | None
    series_title: str | None


class SpontaneousIn(BaseModel):
    minutes: int = Field(ge=5, le=480)


class PlanEntry(BaseModel):
    task: TaskRead
    tier: int  # 1-4
    reason: str


class PlanResponse(BaseModel):
    timebox: TimeboxRead
    state: str  # "upcoming" | "active" | "past"
    plan: list[PlanEntry]
    completed: list[TaskRead]  # tasks completed during the window (past boxes)


class NowResponse(BaseModel):
    timebox: TimeboxRead | None
    state: str  # "active" | "idle"
    plan: list[PlanEntry]
    current: PlanEntry | None
