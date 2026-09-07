"""Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


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
