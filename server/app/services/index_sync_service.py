import asyncio
import logging

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.task import Task, utcnow
from app.models.task_index_state import TaskIndexState
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


def sync_task(db: Session, vector: VectorService, task_id: int) -> None:
    """Bring Qdrant in line with the database for one task. Raises on failure."""
    task = db.get(Task, task_id)
    state = db.get(TaskIndexState, task_id)
    if task is None:
        vector.delete_task(task_id)
        if state is not None:
            db.delete(state)
            db.commit()
        return
    vector.upsert_task(task)
    if state is None:
        state = TaskIndexState(task_id=task_id)
        db.add(state)
    state.indexed_updated_at = task.updated_at
    state.attempts = 0
    state.last_error = None
    state.last_attempt_at = utcnow()
    db.commit()


def try_sync_task(db: Session, vector: VectorService, task_id: int) -> bool:
    """Like sync_task, but never raises. A failure is recorded and retried by reconcile()."""
    try:
        sync_task(db, vector, task_id)
        return True
    except Exception as exc:
        logger.exception("Vector sync failed for task %s", task_id)
        db.rollback()
        _record_failure(db, task_id, exc)
        return False


def _record_failure(db: Session, task_id: int, exc: Exception) -> None:
    try:
        state = db.get(TaskIndexState, task_id)
        if state is None:
            state = TaskIndexState(task_id=task_id, attempts=0)
            db.add(state)
        state.attempts += 1
        state.last_error = f"{type(exc).__name__}: {exc}"[:500]
        state.last_attempt_at = utcnow()
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not record vector sync failure for task %s", task_id)


def reconcile(session_factory: sessionmaker, vector: VectorService, batch_size: int = 100) -> int:
    """One synchronisation pass between the tasks table and Qdrant.

    - tasks never indexed, or changed since they were indexed, are (re)indexed
    - index rows of deleted tasks have their vector removed
    - a newly created collection forces a full re-index
    """
    created = vector.ensure_collection()
    with session_factory() as db:
        if created:
            db.execute(delete(TaskIndexState))
            db.commit()
        stale_ids = db.scalars(
            select(Task.id)
            .outerjoin(TaskIndexState, TaskIndexState.task_id == Task.id)
            .where(
                or_(
                    TaskIndexState.task_id.is_(None),
                    TaskIndexState.indexed_updated_at.is_(None),
                    TaskIndexState.indexed_updated_at != Task.updated_at,
                )
            )
            .order_by(Task.id)
            .limit(batch_size)
        ).all()
        orphan_ids = db.scalars(
            select(TaskIndexState.task_id)
            .where(~exists().where(Task.id == TaskIndexState.task_id))
            .limit(batch_size)
        ).all()
        for task_id in [*stale_ids, *orphan_ids]:
            try_sync_task(db, vector, task_id)
    return len(stale_ids) + len(orphan_ids)


async def run_index_sync_loop(session_factory: sessionmaker, vector: VectorService, interval: int) -> None:
    while True:
        try:
            await asyncio.to_thread(reconcile, session_factory, vector)
        except Exception:
            logger.exception("Vector index reconciliation failed; will retry")
        await asyncio.sleep(interval)