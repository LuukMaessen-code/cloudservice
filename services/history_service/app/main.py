from contextlib import asynccontextmanager
from typing import AsyncIterator, List

from fastapi import FastAPI, HTTPException, Depends, Request
from jose import jwt, JWTError
from fastapi.middleware.cors import CORSMiddleware

from packages.common import ChatMessage

from .config import settings
from .storage import HistoryStorage
from .worker import HistoryWorker

storage = HistoryStorage(settings.STORAGE_PATH)
worker = HistoryWorker(storage)
app = FastAPI(title="Cloudservice Demo History")

# Keycloak/JWT config (update these to match your Keycloak setup)
KEYCLOAK_REALM = "demo-chat"
KEYCLOAK_SERVER_URL = "http://localhost:8080"
KEYCLOAK_AUDIENCE = "cloudservice-gateway"
KEYCLOAK_ISSUER = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_ALGORITHMS = ["RS256"]

import requests
from functools import lru_cache

@lru_cache()
def get_public_key():
    url = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    resp = requests.get(url)
    resp.raise_for_status()
    jwks = resp.json()["keys"]
    # Use the first key (for demo, production should check kid)
    return jwt.algorithms.RSAAlgorithm.from_jwk(jwks[0])

def get_current_user(request: Request):
    auth: str = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(
            token,
            get_public_key(),
            algorithms=KEYCLOAK_ALGORITHMS,
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await worker.start()
    yield
    await worker.stop()


app.router.lifespan_context = lifespan


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/history/{room}", response_model=List[ChatMessage])
async def read_history(room: str, limit: int = 50, user=Depends(get_current_user)) -> List[ChatMessage]:
    if limit <= 0 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return storage.read_latest(room, limit=limit)

