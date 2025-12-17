from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    NATS_URL: str = "nats://nats:4222"
    JETSTREAM_STREAM: str = "CHAT"
    SUBJECT_TEMPLATE: str = "chat.room.{room}"
    ALLOWED_ORIGINS: List[str] = ["*"]
    HISTORY_API_URL: str = "http://history:9000"


settings = Settings()

