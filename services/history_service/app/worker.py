import asyncio
import json
from typing import Optional

from nats.aio.client import Client as NATS
from nats.js.api import DeliverPolicy, StorageType, StreamConfig
from nats.js.errors import APIError

from packages.common import MessageEnvelope

from .config import settings
from .storage import HistoryStorage


class HistoryWorker:
    def __init__(self, storage: HistoryStorage):
        self.storage = storage
        self.nc: Optional[NATS] = None
        self.js = None
        self.stream = settings.JETSTREAM_STREAM
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task:
            return
        self.nc = NATS()
        await self.nc.connect(servers=[settings.NATS_URL])
        self.js = self.nc.jetstream()
        await self._ensure_stream()
        self._task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        if self.nc:
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
            await self.js.update_stream(cfg)

    async def _consume(self) -> None:
        if not self.js:
            raise RuntimeError("JetStream not initialized")

        sub = await self.js.subscribe(
            subject=settings.SUBJECT_TEMPLATE.format(room="*"),
            deliver_policy=DeliverPolicy.ALL,
            manual_ack=True,
            durable="history-service",
        )

        async for msg in sub.messages:
            try:
                payload = json.loads(msg.data.decode("utf-8"))
                envelope = MessageEnvelope(**payload)
                self.storage.append(envelope.payload)
            except Exception:
                # Ignore malformed entries but ack to avoid blocking
                pass
            finally:
                try:
                    await msg.ack()
                except Exception:
                    continue

