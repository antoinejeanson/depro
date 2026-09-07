"""SQLAlchemy models.

M0 only defines the declarative base. Tables land with their milestones:
users/sessions (M1), tasks/tags/dependencies (M2), timeboxes/series (M3).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
