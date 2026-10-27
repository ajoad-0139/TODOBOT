import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from app.models.task import TaskPriority, TaskStatus
from app.services.embedding_service import build_task_embedding_text

_NAMESPACE = uuid.UUID("6f1c1d0e-5b7a-4c52-9a52-3f0f7c1b9a11")


def point_id_for(task_id: int) -> str:
    """Stable Qdrant point id derived from the database task id."""
    return str(uuid.uuid5(_NAMESPACE, f"task:{task_id}"))


class VectorService:
    """Thin wrapper around Qdrant. Synchronous; callers run it in a worker thread.

    Qdrant only holds embeddings plus {task_id, status, priority}. The
    relational database stays the source of truth.
    """

    def __init__(self, client: QdrantClient, collection: str, embedder):
        self.client = client
        self.collection = collection
        self.embedder = embedder

    def ensure_collection(self) -> bool:
        """Create the collection if missing. Returns True when it was just created."""
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                self.collection,
                vectors_config=VectorParams(size=self.embedder.dimension, distance=Distance.COSINE),
            )
            return True
        info = self.client.get_collection(self.collection)
        size = getattr(info.config.params.vectors, "size", None)
        if size != self.embedder.dimension:
            raise RuntimeError(
                f"Qdrant collection '{self.collection}' has vector size {size}, but the "
                f"embedding model produces {self.embedder.dimension}. Use a new collection name."
            )
        return False

    def upsert_task(self, task) -> None:
        vector = self.embedder.embed(build_task_embedding_text(task))
        payload = {"task_id": task.id, "status": task.status.value, "priority": task.priority.value}
        self.client.upsert(
            self.collection,
            points=[PointStruct(id=point_id_for(task.id), vector=vector, payload=payload)],
        )

    def delete_task(self, task_id: int) -> None:
        self.client.delete(
            self.collection, points_selector=PointIdsList(points=[point_id_for(task_id)])
        )

    def search(
        self,
        query: str,
        limit: int,
        statuses: list[TaskStatus] | None = None,
        priorities: list[TaskPriority] | None = None,
    ) -> list[tuple[int, float]]:
        """Return (task_id, score) pairs, best first. Callers must resolve ids in the database."""
        must = []
        if statuses:
            must.append(FieldCondition(key="status", match=MatchAny(any=[s.value for s in statuses])))
        if priorities:
            must.append(FieldCondition(key="priority", match=MatchAny(any=[p.value for p in priorities])))
        response = self.client.query_points(
            self.collection,
            query=self.embedder.embed(query),
            query_filter=Filter(must=must) if must else None,
            limit=limit,
            with_payload=True,
        )
        return [
            (int(p.payload["task_id"]), float(p.score))
            for p in response.points
            if p.payload and "task_id" in p.payload
        ]