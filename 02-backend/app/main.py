from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import auth, feed
from app.ai_client import AiClient
from app.config import Settings
from app.schemas import HealthResponse
from app.store import MemoryStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    application = FastAPI(
        title="Alfa News Insights — Backend",
        version="0.1.0",
        description=(
            "API для подключения frontend. Войдите через /api/auth/login и вставьте "
            "access_token в кнопку Authorize. Тестовый логин: alfa-hack-2026, пароль: "
            "password123. Инсайты и чат приходят из 03-ai-service (offline/llm), при "
            "недоступности — детерминированная заглушка."
        ),
    )
    application.state.settings = settings
    ai_client = AiClient(settings)
    application.state.ai_client = ai_client
    application.state.store = MemoryStore(ai_client=ai_client)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(auth.router)
    application.include_router(feed.router)

    @application.get("/health", response_model=HealthResponse, tags=["Состояние"])
    def health() -> HealthResponse:
        return HealthResponse(
            ai="ai-service" if settings.ai_service_enabled else "mock",
        )

    return application


app = create_app()
