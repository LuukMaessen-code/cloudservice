import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi_keycloak import FastAPIKeycloak
from fastapi.middleware.cors import CORSMiddleware

from packages.common import ChatMessage, MessageEnvelope

from .config import settings
from .models import OutgoingMessage
from .nats_client import NatsClient

broker = NatsClient()

# Keycloak config
keycloak = FastAPIKeycloak(
    server_url="http://keycloak:8080",
    client_id="cloudservice-gateway",
    client_secret="WANHrJcemRVg1agZHwdlsTCbUopHNUge",  # Set in Keycloak admin
    admin_client_id="cloudservice-admin",
    admin_client_secret="4kmE07MNxka9BeikgBprGQNYjzNg4jqg",  # Set to the admin client secret in Keycloak
    realm="demo-chat",
    callback_uri="http://localhost:8000/callback"
)

app = FastAPI(title="Cloudservice Demo Gateway")
keycloak.add_swagger_config(app)

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



# Secure health endpoint
@app.get("/healthz")
async def health(user=Depends(keycloak.get_current_user)) -> dict[str, str]:
    return {"status": "ok"}



# Secure WebSocket endpoint with Keycloak
@app.websocket("/gateway/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await websocket.accept()
    token = websocket.headers.get("authorization")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        user = keycloak.decode_token(token.replace("Bearer ", ""))
    except Exception:
        await websocket.close(code=4401)
        return
    username = user.get("preferred_username", user.get("sub"))
    subscription = await broker.subscribe_room(room)

    async def pump_messages() -> None:
        async for msg in subscription.messages:
            try:
                data = json.loads(msg.data.decode("utf-8"))
                outgoing = OutgoingMessage(**data)
                await websocket.send_json(outgoing.model_dump(mode="json"))
            except Exception:
                pass
            finally:
                await broker.ack(msg)

    pump_task = asyncio.create_task(pump_messages())
    try:
        while True:
            payload = await websocket.receive_text()
            envelope = MessageEnvelope(
                payload=ChatMessage(room=room, user=username, text=payload)
            )
            await broker.publish(envelope)
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        await websocket.close()

