import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient

from app.agents.task_agent import TaskAgent, build_llm
from app.api import websocket
from app.api.routes import tasks
from app.core.config import settings
from app.db.base import Base
from app.db.checkpointer import open_checkpointer
from app.db.session import engine, SessionLocal
from app.models import task as _task_model
from app.models import task_index_state as _index_model
from app.services.embedding_service import EmbeddingService
from app.services.index_sync_service import run_index_sync_loop
from app.services.task_service import TaskNotFoundError
from fastapi.middleware.cors import CORSMiddleware
from app.services.vector_service import VectorService
from app.tools.task_tools import ToolContext

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # fine for dev; use Alembic later
    settings.validate_agent_settings()

    embedder = EmbeddingService(settings.EMBEDDING_MODEL)
    await asyncio.to_thread(embedder.load)  # load the model once, at startup
    client = QdrantClient(location=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
    vector = VectorService(client, settings.QDRANT_COLLECTION, embedder)
    ctx = ToolContext(
        SessionLocal,
        vector,
        search_min_score=settings.SEARCH_MIN_SCORE,
        ambiguity_margin=settings.TARGET_AMBIGUITY_MARGIN,
    )

    async with open_checkpointer(settings.LANGGRAPH_CHECKPOINT_DATABASE_URL) as checkpointer:
        app.state.agent = TaskAgent(ctx, build_llm(settings), checkpointer, settings.AGENT_HISTORY_MESSAGES)
        # Creates the collection (retrying if Qdrant is down) and keeps it in sync with the database.
        sync_loop = asyncio.create_task(
            run_index_sync_loop(SessionLocal, vector, settings.INDEX_SYNC_INTERVAL_SECONDS)
        )
        try:
            yield
        finally:
            sync_loop.cancel()
            with suppress(asyncio.CancelledError):
                await sync_loop


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


app.include_router(tasks.router, prefix=f"{settings.API_V1_PREFIX}/tasks", tags=["tasks"])
app.include_router(websocket.router)

