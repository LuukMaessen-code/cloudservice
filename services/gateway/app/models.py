from pydantic import BaseModel

from packages.common import ChatMessage, MessageEnvelope


class OutgoingMessage(BaseModel):
    """Shape sent to WebSocket clients."""

    type: str
    payload: ChatMessage

