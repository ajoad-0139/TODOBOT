from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.task import utcnow


class TaskIndexState(Base):
    """Which version of each task is in the vector index.

    No foreign key on purpose: the row of a deleted task must survive until
    its vector has been removed from Qdrant.
    """

    __tablename__ = "task_index_state"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    indexed_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)