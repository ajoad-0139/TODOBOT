from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]

    # Input of the current turn (always supplied, None when unused)
    request_id: str | None
    user_message: str | None
    decision: Literal["confirm", "cancel"] | None
    decision_operation_id: str | None

    # Persisted conversation state
    pending: dict[str, Any] | None  # {operation_id, steps, event}
    clarification: dict[str, Any] | None  # {operation, args, candidates}

    # Turn bookkeeping
    last_request_id: str | None
    completed: bool
    events: list[dict[str, Any]]
    deferred: list[dict[str, Any]]
    needs_summary: bool
    route: str