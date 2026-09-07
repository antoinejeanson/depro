"""Task state transitions shared by the API endpoints."""

from datetime import datetime

from app.models import Task
from app.recurrence import next_occurrence


def apply_progress(task: Task, value: int) -> None:
    """Set a task's progress, keeping status, completed_at and the recurrence
    schedule consistent."""
    value = max(0, min(100, value))
    if value >= 100:
        if task.recurrence is not None and task.due_at is not None:
            # Recurrence flip: the task goes back to "to-do" and re-enters
            # the schedule at the next occurrence strictly after now. No
            # backlog stacking: missed occurrences are simply skipped.
            task.status = "todo"
            task.progress = 0
            task.completed_at = None
            task.next_due_at = next_occurrence(
                task.recurrence, task.due_at, datetime.now()
            )
        else:
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
