import logging
import re
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.schemas.chat import CancelIn, ChatMessageIn, ConfirmIn, ServerEvent, client_message_adapter

logger = logging.getLogger(__name__)
router = APIRouter()

CONVERSATION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def build_thread_id(conversation_id: str) -> str:
    # Once authentication exists, return f"{user_id}:{conversation_id}" here so that
    # one user can never open another user's conversation state.
    return conversation_id


async def _send(websocket: WebSocket, event: dict | ServerEvent) -> None:
    model = event if isinstance(event, ServerEvent) else ServerEvent.model_validate(event)
    await websocket.send_json(model.model_dump(mode="json", exclude_none=True))


def _error(code: str, message: str, request_id: str | None = None, data: dict | None = None) -> ServerEvent:
    return ServerEvent(type="error", message=message, request_id=request_id, data={"code": code, **(data or {})})


@router.websocket("/ws/chat/{conversation_id}")
async def chat_socket(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    agent = getattr(websocket.app.state, "agent", None)
    if agent is None:
        await _send(websocket, _error("agent_unavailable", "The assistant is not available."))
        await websocket.close(code=1011)
        return
    if not CONVERSATION_ID_RE.match(conversation_id):
        await _send(websocket, _error("invalid_conversation_id", "Conversation id must be 8-64 letters, digits, '-' or '_'."))
        await websocket.close(code=1008)
        return

    thread_id = build_thread_id(conversation_id)
    await _send(websocket, ServerEvent(type="connection_ready", message="Connected.", data={"conversation_id": conversation_id}))
    try:
        pending = await agent.get_pending_event(thread_id)
        if pending:  # reconnect: ask again, state survived in the checkpoint
            await _send(websocket, pending)
    except Exception:
        logger.exception("Could not restore conversation state")

    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_message(websocket, agent, thread_id, raw)
    except WebSocketDisconnect:
        logger.info("Client disconnected from %s", conversation_id)


async def _handle_message(websocket: WebSocket, agent, thread_id: str, raw: str) -> None:
    try:
        parsed = client_message_adapter.validate_json(raw)
    except ValidationError as exc:
        problems = [{"field": ".".join(str(p) for p in e["loc"]), "problem": e["msg"]} for e in exc.errors()]
        await _send(websocket, _error("invalid_message", "Invalid message.", data={"problems": problems}))
        return

    request_id = parsed.request_id or uuid.uuid4().hex
    try:
        if isinstance(parsed, ChatMessageIn):
            events = await agent.run_turn(thread_id, request_id=request_id, message=parsed.message)
        elif isinstance(parsed, ConfirmIn):
            events = await agent.run_turn(thread_id, request_id=request_id, decision="confirm", operation_id=parsed.operation_id)
        elif isinstance(parsed, CancelIn):
            events = await agent.run_turn(thread_id, request_id=request_id, decision="cancel", operation_id=parsed.operation_id)
        else:  # unreachable: the discriminated union is exhaustive
            return
        for event in events:
            await _send(websocket, {**event, "request_id": request_id})
    except WebSocketDisconnect:
        raise
    except Exception:
        logger.exception("Agent turn failed")
        await _send(websocket, _error("internal_error", "Something went wrong while processing your message.", request_id))