from enum import Enum
from pydantic import BaseModel, Field


class ChatMode(str, Enum):
    WITH_CONTEXT = "with_context"
    WITHOUT_CONTEXT = "without_context"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    mode: ChatMode = ChatMode.WITH_CONTEXT


class ChatResponse(BaseModel):
    conversation_id: str
    conversation_title: str
    mode: ChatMode
    reply: str
    used_context: bool
    messages: list[ChatMessage]
