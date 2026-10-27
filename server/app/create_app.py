from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.routes import tasks
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.services.task_service import TaskNotFoundError


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


app.include_router(tasks.router, prefix=f"{settings.API_V1_PREFIX}/tasks", tags=["tasks"])

