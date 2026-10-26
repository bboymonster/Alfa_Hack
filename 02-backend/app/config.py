from pathlib import Path
from secrets import token_urlsafe

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # Локальный .env имеет приоритет над корневым; переменные процесса — над обоими.
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    jwt_secret_key: str = Field(default_factory=lambda: token_urlsafe(48))
    access_token_expire_minutes: int = Field(default=1440, ge=1, le=10080)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # 03-ai-service: базовый адрес, таймаут и возможность полностью отключить AI.
    ai_service_url: str = "http://localhost:8001"
    ai_service_timeout_s: float = Field(default=60.0, gt=0, le=300)
    ai_service_enabled: bool = True
    ai_service_retry_interval_s: float = Field(default=15.0, gt=0, le=300)

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def use_temporary_key_if_empty(cls, value: str) -> str:
        return value or token_urlsafe(48)
