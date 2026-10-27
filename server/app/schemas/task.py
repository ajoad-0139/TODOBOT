from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.task import TaskPriority, TaskStatus

NON_NULLABLE_FIELDS = ("title", "status", "priority")


def _clean_title(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("title must not be empty or whitespace only")
    return value


def _to_naive_utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class TaskBase(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def _normalise_due_date(cls, v: datetime | None) -> datetime | None:
        return _to_naive_utc(v)


class TaskCreate(TaskBase):
    title: str = Field(max_length=200)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        return _clean_title(v)


class TaskUpdate(TaskBase):

    title: str | None = Field(default=None, max_length=200)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str | None) -> str | None:
        return None if v is None else _clean_title(v)

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self) -> "TaskUpdate":
        for name in NON_NULLABLE_FIELDS:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime