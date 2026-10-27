"""Validated tools the agent may use.

Read-only tools and create_task run immediately. update_task and delete_task
only *prepare* a step; the graph executes steps after explicit confirmation.
All database work goes through the existing task service.
"""
import enum
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy.orm import Session

from app.models.task import Task, TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import task_service
from app.services.index_sync_service import try_sync_task
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)

STATUS_LABELS = {"pending": "To do", "in_progress": "In progress", "completed": "Done"}
PRIORITY_LABELS = {"low": "Low", "medium": "Medium", "high": "High"}


# ---------- argument schemas (what the LLM may send) ----------
class CreateTaskArgs(BaseModel):
    """What the LLM sees for create_task. due_date is a plain string because some
    providers (e.g. Groq) reject 'YYYY-MM-DD' against a date-time schema.
    It is converted to the strict TaskCreate right before use."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: str | None = Field(
        default=None,
        description="Due date as YYYY-MM-DD, or YYYY-MM-DDTHH:MM:SS if a time is given.",
    )


class ListTasksArgs(BaseModel):
    statuses: list[TaskStatus] | None = Field(default=None, description="Only these statuses. 'Unfinished' means pending and in_progress.")
    priority: TaskPriority | None = None
    limit: int = Field(default=20, ge=1, le=50)


class SemanticSearchArgs(BaseModel):
    query: str = Field(min_length=1, max_length=300, description="What the tasks are about, in natural language.")
    statuses: list[TaskStatus] | None = Field(default=None, description="Only these statuses. 'Unfinished' means pending and in_progress.")
    priorities: list[TaskPriority] | None = None
    limit: int = Field(default=5, ge=1, le=20)


class GetTaskArgs(BaseModel):
    task_id: int = Field(ge=1)


class _TargetArgs(BaseModel):
    task_id: int | None = Field(default=None, ge=1, description="Only when the id is known from earlier in this conversation.")
    target: str | None = Field(default=None, min_length=1, max_length=300, description="Short natural-language description of the task, e.g. 'the demo task'.")

    @model_validator(mode="after")
    def _need_one(self):
        if self.task_id is None and not self.target:
            raise ValueError("Provide task_id or target")
        return self


class UpdateTaskArgs(_TargetArgs):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: str | None = Field(default=None, description="New due date as YYYY-MM-DD, or YYYY-MM-DDTHH:MM:SS.")
    clear_description: bool = False
    clear_due_date: bool = False


class DeleteTaskArgs(_TargetArgs):
    pass


def _schema_only(name: str, description: str, args_schema: type[BaseModel]) -> StructuredTool:
    def _never_called(**kwargs):
        raise RuntimeError(f"{name} is executed by the agent graph, not by LangChain")

    return StructuredTool.from_function(
        func=_never_called, name=name, description=description, args_schema=args_schema
    )


TOOL_SCHEMAS = [
    _schema_only("create_task", "Create a new task. Resolve relative dates against today's date.", CreateTaskArgs),
    _schema_only("list_tasks", "List tasks, optionally filtered by status or priority. Use when no topic is involved.", ListTasksArgs),
    _schema_only("semantic_search_tasks", "Find tasks by meaning/topic, optionally filtered by status and priority.", SemanticSearchArgs),
    _schema_only("get_task", "Get one task by id.", GetTaskArgs),
    _schema_only("update_task", "Change a task's fields or status (including completing it). The user is asked to confirm before it is applied.", UpdateTaskArgs),
    _schema_only("delete_task", "Delete a task. The user is asked to confirm before it is applied.", DeleteTaskArgs),
]


@dataclass
class ToolContext:
    session_factory: Callable[[], Session]
    vector: VectorService
    search_min_score: float = 0.25
    ambiguity_margin: float = 0.08


@dataclass
class SearchHit:
    task: Task
    score: float


def task_to_dict(task: Task) -> dict[str, Any]:
    return TaskRead.model_validate(task).model_dump(mode="json")


def first_error(exc: ValidationError) -> str:
    parts = []
    for e in exc.errors():
        loc = ".".join(str(p) for p in e["loc"])
        parts.append(f"{loc}: {e['msg']}" if loc else e["msg"])
    return "; ".join(parts)


# ---------- immediate tools ----------
def create_task(ctx: ToolContext, args: CreateTaskArgs | TaskCreate) -> dict:
    if isinstance(args, CreateTaskArgs):
        # Strict validation happens here; this also parses the due_date string.
        args = TaskCreate.model_validate(args.model_dump())
    with ctx.session_factory() as db:
        task = task_service.create_task(db, args)  # committed here
        indexed = try_sync_task(db, ctx.vector, task.id)  # never raises
        return {
            "ok": True,
            "task": task_to_dict(task),
            "search_index": "indexed" if indexed else "pending_retry",
        }


def list_tasks(ctx: ToolContext, args: ListTasksArgs) -> dict:
    with ctx.session_factory() as db:
        if args.statuses:
            tasks: list[Task] = []
            for status in dict.fromkeys(args.statuses):
                tasks += task_service.list_tasks(db, status=status, priority=args.priority, limit=args.limit)
            tasks.sort(key=lambda t: (t.created_at, t.id))
            tasks = tasks[: args.limit]
        else:
            tasks = task_service.list_tasks(db, priority=args.priority, limit=args.limit)
        return {"ok": True, "count": len(tasks), "tasks": [task_to_dict(t) for t in tasks]}


def get_task(ctx: ToolContext, args: GetTaskArgs) -> dict:
    with ctx.session_factory() as db:
        try:
            return {"ok": True, "task": task_to_dict(task_service.get_task(db, args.task_id))}
        except task_service.TaskNotFoundError as exc:
            return {"ok": False, "error": str(exc)}


def _search_hits(ctx, db, query, statuses, priorities, limit) -> list[SearchHit]:
    candidates = ctx.vector.search(query, limit=max(limit * 3, 10), statuses=statuses, priorities=priorities)
    hits: list[SearchHit] = []
    for task_id, score in candidates:
        if score < ctx.search_min_score:
            continue
        task = db.get(Task, task_id)  # the database is authoritative
        if task is None:
            continue  # deleted since it was indexed
        if statuses and task.status not in statuses:
            continue  # vector payload may be stale
        if priorities and task.priority not in priorities:
            continue
        hits.append(SearchHit(task, score))
        if len(hits) == limit:
            break
    return hits


def semantic_search_tasks(ctx: ToolContext, args: SemanticSearchArgs) -> dict:
    with ctx.session_factory() as db:
        try:
            hits = _search_hits(ctx, db, args.query, args.statuses, args.priorities, args.limit)
        except Exception:
            logger.exception("Semantic search failed")
            return {"ok": False, "error": "Semantic search is temporarily unavailable."}
        return {
            "ok": True,
            "count": len(hits),
            "tasks": [{**task_to_dict(h.task), "score": round(h.score, 3)} for h in hits],
            "note": "Most similar tasks only; this is not guaranteed to be every related task.",
        }


# ---------- modifying tools: prepare now, execute after confirmation ----------
def _resolve_target(ctx, db, task_id, target):
    if task_id is not None:
        task = db.get(Task, task_id)
        if task is None:
            return "not_found", f"Task #{task_id} does not exist."
        return "ok", task
    hits = _search_hits(ctx, db, target, None, None, limit=5)
    if not hits:
        return "not_found", f'I could not find a task matching "{target}".'
    close = [h for h in hits if h.score >= hits[0].score - ctx.ambiguity_margin]
    if len(close) == 1:
        return "ok", close[0].task
    return "ambiguous", [h.task for h in close[:4]]


def _current_value(task: Task, field: str):
    value = getattr(task, field)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _fmt(field: str, value) -> str:
    if value is None:
        return "none"
    if field == "status":
        return STATUS_LABELS.get(value, str(value))
    if field == "priority":
        return PRIORITY_LABELS.get(value, str(value))
    text = str(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _build_changes(args: UpdateTaskArgs) -> dict:
    raw = {}
    for field in ("title", "description", "status", "priority", "due_date"):
        value = getattr(args, field)
        if value is not None:
            raw[field] = value
    if args.clear_description:
        raw["description"] = None
    if args.clear_due_date:
        raw["due_date"] = None
    if not raw:
        return {}
    # Strict validation; this also parses the due_date string.
    return TaskUpdate.model_validate(raw).model_dump(mode="json", exclude_unset=True)


def _resolve_or_report(ctx, db, args) -> tuple[str, Any]:
    try:
        return _resolve_target(ctx, db, args.task_id, args.target)
    except Exception:
        logger.exception("Target resolution failed")
        return "error", "Task search is temporarily unavailable."


def _not_ok(kind: str, found) -> dict:
    if kind == "ambiguous":
        return {"status": "ambiguous", "candidates": [{"id": t.id, "title": t.title} for t in found]}
    return {"status": kind, "message": found}


def prepare_update(ctx: ToolContext, args: UpdateTaskArgs) -> dict:
    try:
        changes = _build_changes(args)
    except ValidationError as exc:
        return {"status": "invalid", "message": first_error(exc)}
    if not changes:
        return {"status": "invalid", "message": "No changes were specified."}
    with ctx.session_factory() as db:
        kind, found = _resolve_or_report(ctx, db, args)
        if kind != "ok":
            return _not_ok(kind, found)
        task = found
        diff = {k: v for k, v in changes.items() if _current_value(task, k) != v}
        if not diff:
            return {"status": "noop", "message": f'"{task.title}" already has those values.'}
        details = "; ".join(f"{k}: {_fmt(k, _current_value(task, k))} → {_fmt(k, v)}" for k, v in diff.items())
        return {
            "status": "step",
            "step": {
                "action": "update",
                "task_id": task.id,
                "task_title": task.title,
                "expected_updated_at": task.updated_at.isoformat(),
                "changes": diff,
                "details": details,
                "summary": f'Update "{task.title}" ({details})',
            },
        }


def prepare_delete(ctx: ToolContext, args: DeleteTaskArgs) -> dict:
    with ctx.session_factory() as db:
        kind, found = _resolve_or_report(ctx, db, args)
        if kind != "ok":
            return _not_ok(kind, found)
        task = found
        return {
            "status": "step",
            "step": {
                "action": "delete",
                "task_id": task.id,
                "task_title": task.title,
                "expected_updated_at": task.updated_at.isoformat(),
                "changes": {},
                "details": "",
                "summary": f'Delete "{task.title}" (this cannot be undone)',
            },
        }


def merge_steps(steps: list[dict]) -> list[dict]:
    """One step per task, so a task is never changed twice from a stale snapshot."""
    result: dict[int, dict] = {}
    for step in steps:
        current = result.get(step["task_id"])
        if current is None or step["action"] == "delete":
            result[step["task_id"]] = dict(step)
        elif current["action"] == "update":
            current["changes"] = {**current["changes"], **step["changes"]}
            current["details"] += "; " + step["details"]
            current["summary"] = f'Update "{current["task_title"]}" ({current["details"]})'
        # an update after a delete of the same task is dropped
    return list(result.values())


def execute_step(ctx: ToolContext, step: dict) -> dict:
    """Apply one confirmed step. Re-validates the task immediately before acting."""
    action, task_id, title = step["action"], step["task_id"], step["task_title"]

    def fail(message: str) -> dict:
        return {"ok": False, "action": action, "task_id": task_id, "message": message}

    with ctx.session_factory() as db:
        task = db.get(Task, task_id)
        if task is None:
            return fail(f'"{title}" no longer exists, so nothing was changed.')
        if task.updated_at.isoformat() != step["expected_updated_at"]:
            return fail(f'"{title}" was modified after I prepared this change, so I did not apply it. Please ask again.')
        if action == "delete":
            task_service.delete_task(db, task_id)
            try_sync_task(db, ctx.vector, task_id)  # removes the vector; failures are retried later
            return {"ok": True, "action": action, "task_id": task_id, "message": f'Deleted "{title}".'}
        if action == "update":
            try:
                data = TaskUpdate.model_validate(step["changes"])
            except ValidationError as exc:
                return fail(f'Could not update "{title}": {first_error(exc)}')
            updated = task_service.update_task(db, task_id, data)
            indexed = try_sync_task(db, ctx.vector, task_id)
            message = f'Updated "{title}" ({step["details"]}).'
            if not indexed:
                message += " Search results for this task may lag briefly."
            return {
                "ok": True,
                "action": action,
                "task_id": task_id,
                "message": message,
                "data": {"task": task_to_dict(updated), "search_index": "indexed" if indexed else "pending_retry"},
            }
    return fail("Unsupported operation.")


# Immediate tools: name -> (argument schema, implementation)
IMMEDIATE_TOOLS = {
    "create_task": (CreateTaskArgs, create_task),
    "list_tasks": (ListTasksArgs, list_tasks),
    "semantic_search_tasks": (SemanticSearchArgs, semantic_search_tasks),
    "get_task": (GetTaskArgs, get_task),
}
# Prepared tools: name -> (argument schema, prepare function)
PREPARED_TOOLS = {
    "update_task": (UpdateTaskArgs, prepare_update),
    "delete_task": (DeleteTaskArgs, prepare_delete),
}