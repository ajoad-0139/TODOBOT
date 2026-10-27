from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field, TypeAdapter, field_validator


class _ClientMessage(BaseModel):
    request_id: str | None = Field(default=None, min_length=1, max_length=64)


class ChatMessageIn(_ClientMessage):
    type: Literal["chat_message"]
    message: str = Field(max_length=2000)

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be blank")
        return v


class ConfirmIn(_ClientMessage):
    type: Literal["confirm"]
    operation_id: str = Field(min_length=1, max_length=64)


class CancelIn(_ClientMessage):
    type: Literal["cancel"]
    operation_id: str = Field(min_length=1, max_length=64)


ClientMessage = Annotated[ChatMessageIn | ConfirmIn | CancelIn, Field(discriminator="type")]
client_message_adapter = TypeAdapter(ClientMessage)

EventType = Literal[
    "connection_ready",
    "assistant_message",
    "tool_status",
    "clarification_request",
    "confirmation_required",
    "operation_success",
    "operation_error",
    "operation_cancelled",
    "error",
]


class ServerEvent(BaseModel):
    type: EventType
    message: str
    request_id: str | None = None
    operation_id: str | None = None
    operation: str | None = None
    data: dict[str, Any] | None = None