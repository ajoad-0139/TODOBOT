from contextlib import asynccontextmanager


@asynccontextmanager
async def open_checkpointer(url: str):
    """Open a LangGraph checkpointer. Conversation memory has its own database."""
    if url.startswith(("postgresql://", "postgres://")):
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(url) as saver:
            await saver.setup()
            yield saver
    elif url.startswith("sqlite:///"):
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        async with AsyncSqliteSaver.from_conn_string(url.removeprefix("sqlite:///")) as saver:
            yield saver
    else:
        raise ValueError("LANGGRAPH_CHECKPOINT_DATABASE_URL must start with sqlite:/// or postgresql://")