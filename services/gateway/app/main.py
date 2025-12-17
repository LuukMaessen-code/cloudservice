import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from packages.common import ChatMessage, MessageEnvelope

from .config import settings
from .models import OutgoingMessage
from .nats_client import NatsClient

broker = NatsClient()
app = FastAPI(title="Cloudservice Demo Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await broker.connect()
    yield
    await broker.close()


app.router.lifespan_context = lifespan


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str, user: str) -> None:
    await websocket.accept()
    websocket._origin = "*" #bypass origin check for development
    subscription = await broker.subscribe_room(room)

    async def pump_messages() -> None:
        async for msg in subscription.messages:
            try:
                data = json.loads(msg.data.decode("utf-8"))
                outgoing = OutgoingMessage(**data)
                await websocket.send_json(outgoing.model_dump(mode="json"))
            except Exception:
                # Unparseable payload; ignore but still ack
                pass
            finally:
                await broker.ack(msg)

    pump_task = asyncio.create_task(pump_messages())
    try:
        while True:
            payload = await websocket.receive_text()
            envelope = MessageEnvelope(
                payload=ChatMessage(room=room, user=user, text=payload)
            )
            await broker.publish(envelope)
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        await websocket.close()

