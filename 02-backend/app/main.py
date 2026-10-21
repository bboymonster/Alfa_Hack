from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import auth, feed
from app.config import Settings
from app.schemas import HealthResponse
from app.store import MemoryStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    application = FastAPI(
        title="Alfa News Insights — Backend",
        version="0.1.0",
        description=(
            "API для подключения frontend. Режим mock: данные в памяти, AI заменён заглушкой. "
            "Войдите через /api/auth/login и вставьте access_token в кнопку Authorize. "
            "Тестовый логин: alfa-hack-2026, пароль: password123."
        ),
    )
    application.state.settings = settings
    application.state.store = MemoryStore()
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
        return HealthResponse()

    return application


app = create_app()
