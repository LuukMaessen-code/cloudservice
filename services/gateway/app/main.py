
import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator
from jose import jwt
import requests
import os

from dotenv import load_dotenv
load_dotenv()

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
    client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
    client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET"),  # Set in Keycloak admin
    admin_client_id=os.getenv("KEYCLOAK_ADMIN_CLIENT_ID"),
    admin_client_secret=os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET"),  # Set to the admin client secret in Keycloak
    realm=os.getenv("KEYCLOAK_REALM"),
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
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.close(code=4401)
        return
    # Get Keycloak public key for JWT validation
    try:
        # Discover JWKS URI from Keycloak
        realm_url = f"{keycloak.server_url}/realms/{keycloak.realm}"
        jwks_uri = f"{realm_url}/protocol/openid-connect/certs"
        jwks = requests.get(jwks_uri).json()
        # Find the key matching the token's kid
        unverified_header = jwt.get_unverified_header(token)
        key = next((k for k in jwks['keys'] if k['kid'] == unverified_header['kid']), None)
        if not key:
            raise Exception("Public key not found for token kid")
        # Decode and verify token using the JWK dict directly
        user = jwt.decode(token, key, algorithms=[key['alg']], audience="account", options={"verify_exp": True})
    except Exception as e:
        await websocket.accept()
        await websocket.close(code=4401)
        return
    await websocket.accept()
    username = user.get("preferred_username", user.get("sub"))
    try:
        subscription = await broker.subscribe_room(room)
    except Exception as e:
        await websocket.close(code=1011)
        return

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

