from contextlib import asynccontextmanager
from typing import AsyncIterator, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from packages.common import ChatMessage

from .config import settings
from .storage import HistoryStorage
from .worker import HistoryWorker

storage = HistoryStorage(settings.STORAGE_PATH)
worker = HistoryWorker(storage)
app = FastAPI(title="Cloudservice Demo History")

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
async def read_history(room: str, limit: int = 50) -> List[ChatMessage]:
    if limit <= 0 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return storage.read_latest(room, limit=limit)

