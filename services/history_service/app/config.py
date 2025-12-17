from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    NATS_URL: str = "nats://nats:4222"
    JETSTREAM_STREAM: str = "CHAT"
    SUBJECT_TEMPLATE: str = "chat.room.{room}"
    STORAGE_PATH: Path = Path("/data/history")
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://16.16.217.223:8000",
        "http://16.16.217.223:9000",
        "http://16.16.217.223",
        "http://16.16.217.223:4222",
    ]


settings = Settings()

