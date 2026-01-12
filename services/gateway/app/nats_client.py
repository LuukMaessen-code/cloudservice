import json
from typing import Optional

from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from nats.js.api import DeliverPolicy, StorageType, StreamConfig
from nats.js.errors import APIError

from packages.common import MessageEnvelope

from .config import settings


class NatsClient:
    def __init__(self) -> None:
        self.nc: Optional[NATS] = None
        self.js = None
        self.stream = settings.JETSTREAM_STREAM

    async def connect(self) -> None:
        self.nc = NATS()
        await self.nc.connect(servers=[settings.NATS_URL])
        self.js = self.nc.jetstream()
        await self._ensure_stream()

    async def close(self) -> None:
        if self.nc is not None:
            await self.nc.drain()
            await self.nc.close()

    async def _ensure_stream(self) -> None:
        subjects = [settings.SUBJECT_TEMPLATE.format(room="*")]
        cfg = StreamConfig(
            name=self.stream,
            subjects=subjects,
            storage=StorageType.FILE,
            max_msgs_per_subject=-1,
        )
        try:
            await self.js.add_stream(cfg)
        except APIError:
            # Likely exists; update to ensure subjects are present
            await self.js.update_stream(cfg)

    def subject_for_room(self, room: str) -> str:
        return settings.SUBJECT_TEMPLATE.format(room=room)

    async def publish(self, envelope: MessageEnvelope) -> None:
        if not self.js:
            raise RuntimeError("JetStream is not initialized")
        await self.js.publish(
            self.subject_for_room(envelope.payload.room),
            envelope.model_dump_json().encode("utf-8"),
        )

    async def subscribe_room(self, room: str):
        """Subscribe to a room, delivering only new messages after subscription."""
        if not self.js:
            raise RuntimeError("JetStream is not initialized")
        sub = await self.js.subscribe(
            subject=self.subject_for_room(room),
            deliver_policy=DeliverPolicy.NEW,
            manual_ack=True,
        )
        return sub
    
    async def publish_audit(self, subject: str, payload: dict) -> None:
        if not self.nc:
            raise RuntimeError("NATS connection is not initialized")
        # Publish audit events over core NATS to avoid JetStream ack parsing issues
        await self.nc.publish(subject, json.dumps(payload).encode("utf-8"))
        # Ensure the message is sent promptly
        await self.nc.flush()

    @staticmethod
    async def ack(msg: Msg) -> None:
        try:
            await msg.ack()
        except Exception:
            # Swallow ack errors to avoid crashing reader loop
            pass

