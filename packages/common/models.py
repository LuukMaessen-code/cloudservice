from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    room: str = Field(..., min_length=1, max_length=128)
    user: str = Field(..., min_length=1, max_length=64)
    text: str = Field(..., min_length=1, max_length=2000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageEnvelope(BaseModel):
    """Wrapper for messages placed on the bus."""

    type: str = Field(default="chat.message")
    payload: ChatMessage

