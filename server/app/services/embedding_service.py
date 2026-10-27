import threading


def build_task_embedding_text(task) -> str:
    return (
        f"Title: {task.title}\n"
        f"Description: {task.description or ''}\n"
        f"Status: {task.status.value}\n"
        f"Priority: {task.priority.value}"
    )


class EmbeddingService:
    """Loads the Sentence Transformers model once and reuses it."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def load(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        model = self.load()
        # renamed in newer sentence-transformers versions
        getter = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
        return int(getter())

    def embed(self, text: str) -> list[float]:
        return self.load().encode(text, normalize_embeddings=True).tolist()