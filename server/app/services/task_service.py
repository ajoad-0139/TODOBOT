from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.task import Task, TaskPriority, TaskStatus, utcnow
from app.schemas.task import TaskCreate, TaskUpdate
from app.errors.task_exceptions import TaskNotFoundError


def create_task(db: Session, data: TaskCreate) -> Task:
    task = Task(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError(task_id)
    return task


def list_tasks(
    db: Session,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Task]:
    stmt = select(Task)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    stmt = stmt.order_by(Task.created_at, Task.id).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def update_task(db: Session, task_id: int, data: TaskUpdate) -> Task:
    task = get_task(db, task_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return task
    for field, value in changes.items():
        setattr(task, field, value)
    task.updated_at = utcnow()
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: int) -> None:
    task = get_task(db, task_id)
    db.delete(task)
    db.commit()