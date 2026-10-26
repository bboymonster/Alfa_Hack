"""Настройки сервиса. Env-префикс ``AI_``; порядок: переменные процесса → .env сервиса →
.env корня репо → значения по умолчанию. Без ``AI_LLM_API_KEY`` сервис работает offline."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
LOG_FORMATS = frozenset({"json", "console"})

SERVICE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = SERVICE_DIR.parent

# Точные идентификаторы из инструкции организаторов (Приложение 3).
ALLOWED_LLM_MODELS = frozenset(
    {
        "google/gemma-4-26b-a4b-it",
        "z-ai/glm-5.3-flash",
        "qwen/qwen3.6-35b-a3b",
        "deepseek/deepseek-v4.1-flash",
        "qwen/qwen3-vl-30b-a3b-instruct",
        "moonshotai/kimi-k2.6",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AI_",
        env_file=(REPO_ROOT / ".env", SERVICE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM
    llm_base_url: str = Field(default="https://changellenge.up.railway.app/v1", min_length=1)
    llm_api_key: SecretStr = SecretStr("")
    llm_model_main: str = "qwen/qwen3.6-35b-a3b"
    llm_model_fast: str = "google/gemma-4-26b-a4b-it"
    llm_model_checker: str = "z-ai/glm-5.3-flash"
    llm_timeout_s: float = Field(default=60.0, gt=0)
    llm_max_retries: int = Field(default=3, ge=1, le=10)
    llm_max_tokens: int = Field(default=4000, ge=256)
    llm_reasoning_enabled: bool = False
    insight_timeout_s: float = Field(default=120.0, gt=0)
    # Больше llm_timeout_s, чтобы один повтор после обрезанного JSON уложился в бюджет.
    chat_timeout_s: float = Field(default=90.0, gt=0)
    score_llm_adjust: bool = True
    prompt_version: str = "2026-10-26.1"

    # --- Данные
    articles_dir: Path = Path("data/articles")
    datasets_dir: Path = Path("data/datasets")
    index_dir: Path = Path("data/index")
    reports_catalog: Path = Path("src/ai_service/resources/reports_catalog.yaml")

    # --- RAG
    embed_dense_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embed_sparse_language: str = "russian"
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_min_score: float = Field(default=0.45, ge=0.0, le=1.0)
    ocr_lang: str = "rus+eng"
    ocr_dpi: int = Field(default=200, ge=72, le=400)
    chunk_max_chars: int = Field(default=800, ge=200)
    chunk_overlap: int = Field(default=150, ge=0)
    max_full_text_chars: int = Field(default=6000, ge=500)

    # --- Сбор новостей
    # NoDecode: pydantic-settings иначе требует JSON в env, а значение задаётся через запятую.
    news_sources_enabled: Annotated[list[str], NoDecode] = [
        "cbr_press",
        "cbr_news",
        "rbc",
        "interfax",
        "kommersant",
    ]
    news_sources_json: str = ""
    news_fetch_timeout_s: float = Field(default=15.0, gt=0)

    # --- Логи
    log_level: str = "INFO"
    log_format: str = "json"

    @field_validator("llm_model_main", "llm_model_fast", "llm_model_checker")
    @classmethod
    def _allowed_model(cls, value: str) -> str:
        value = value.strip()
        if value not in ALLOWED_LLM_MODELS:
            raise ValueError("Модель отсутствует в разрешённом списке Приложения 3")
        return value

    @field_validator("news_sources_enabled", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("llm_base_url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("AI_LLM_BASE_URL должен начинаться с http:// или https://")
        return value

    @field_validator("log_level")
    @classmethod
    def _log_level(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in LOG_LEVELS:
            raise ValueError(f"AI_LOG_LEVEL: ожидается одно из {sorted(LOG_LEVELS)}")
        return value

    @field_validator("log_format")
    @classmethod
    def _log_format(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in LOG_FORMATS:
            raise ValueError(f"AI_LOG_FORMAT: ожидается одно из {sorted(LOG_FORMATS)}")
        return value

    @model_validator(mode="after")
    def _chunking_consistent(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_max_chars:
            raise ValueError("AI_CHUNK_OVERLAP должен быть меньше AI_CHUNK_MAX_CHARS")
        return self

    @field_validator("articles_dir", "datasets_dir", "index_dir", "reports_catalog", mode="after")
    @classmethod
    def _resolve_relative(cls, value: Path) -> Path:
        return value if value.is_absolute() else (SERVICE_DIR / value).resolve()

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key.get_secret_value().strip())

    @property
    def ocr_cache_dir(self) -> Path:
        return self.index_dir / "ocr"

    @property
    def qdrant_path(self) -> Path:
        return self.index_dir / "qdrant"

    @property
    def manifest_path(self) -> Path:
        return self.index_dir / "manifest.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
