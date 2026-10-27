from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.task import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import task_service

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbSession):
    return task_service.create_task(db, payload)


@router.get("/", response_model=list[TaskRead])
def list_tasks(
    db: DbSession,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    return task_service.list_tasks(db, status, priority, skip, limit)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: DbSession):
    return task_service.get_task(db, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, db: DbSession):
    # Also used to change status, e.g. {"status": "completed"}.
    return task_service.update_task(db, task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbSession):
    task_service.delete_task(db, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)