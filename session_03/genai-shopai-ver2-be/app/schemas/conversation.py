from pydantic import BaseModel, Field

from app.schemas.chat import ChatMessage, ChatMode


class ConversationSummary(BaseModel):
    id: str
    title: str
    mode: ChatMode
    created_at: str
    updated_at: str
    message_count: int = 0
    last_message: str | None = None


class ConversationDetail(ConversationSummary):
    messages: list[ChatMessage]


class UpdateConversationRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    mode: ChatMode | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
