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
KEYCLOAK_SERVER_URL = "http://keycloak:8080"
KEYCLOAK_AUDIENCE = "cloudservice-gateway"
KEYCLOAK_ISSUER = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_ALGORITHMS = ["RS256"]

import requests
from functools import lru_cache

def get_jwk_for_token(token: str):
    url = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    resp = requests.get(url)
    resp.raise_for_status()
    jwks = resp.json()["keys"]
    unverified_header = jwt.get_unverified_header(token)
    key = next((k for k in jwks if k["kid"] == unverified_header["kid"]), None)
    if not key:
        raise HTTPException(status_code=401, detail="Public key not found for token kid")
    return key

def get_current_user(request: Request):
    auth: str = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth.split(" ", 1)[1]
    try:
        key = get_jwk_for_token(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience="account",
            options={"verify_exp": True},
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
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

