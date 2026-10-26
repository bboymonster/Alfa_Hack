import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import auth, feed
from app.ai_client import AiClient
from app.config import Settings
from app.schemas import HealthResponse
from app.store import MemoryStore

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.store.start_enrichment()
        try:
            yield
        finally:
            app.state.store.stop_enrichment()

    application = FastAPI(
        title="Alfa News Insights — Backend",
        version="0.2.0",
        lifespan=lifespan,
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

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Клиент всегда получает JSON {detail}, а не plain-text «Internal Server Error».
        log.exception("api.unexpected path=%s error=%s", request.url.path, type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера. Повторите попытку позже."},
        )

    @application.get("/health", response_model=HealthResponse, tags=["Состояние"])
    def health() -> HealthResponse:
        ai_status, ai_mode = ai_client.runtime_status()
        return HealthResponse(
            ai="ai-service" if ai_status == "available" else "mock",
            ai_status=ai_status,
            ai_mode=ai_mode,
            enrichment=application.state.store.enrichment_status(),
        )

    return application


app = create_app()
