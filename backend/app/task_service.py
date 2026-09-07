"""Task state transitions shared by the API endpoints.

M5 will extend `complete_task` with the recurrence flip.
"""

from datetime import datetime

from app.models import Task


def apply_progress(task: Task, value: int) -> None:
    """Set a task's progress, keeping status and completed_at consistent."""
    value = max(0, min(100, value))
    if value >= 100:
        task.status = "done"
        task.progress = 100
        task.completed_at = datetime.now()
    elif value <= 0:
        task.status = "todo"
        task.progress = 0
        task.completed_at = None
    else:
        task.status = "in_progress"
        task.progress = value


def complete_task(task: Task) -> None:
    apply_progress(task, 100)
