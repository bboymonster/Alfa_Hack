"""FastAPI-приложение AI-сервиса. Все зависимости внедряемы (тесты подменяют их фейками)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_service import __version__
from ai_service.agent.graph import InsightPipeline
from ai_service.api import health, insight
from ai_service.app_context import AppContext
from ai_service.config import Settings, get_settings
from ai_service.datasets.store import Datasets, build_datasets
from ai_service.errors import install_error_handlers
from ai_service.llm.generator import InsightGenerator, build_generator
from ai_service.llm.provider import build_model_slots
from ai_service.logging import configure_logging, get_logger, request_id_middleware
from ai_service.rag.retriever import Retriever, build_retriever

log = get_logger(__name__)


def build_context(
    settings: Settings,
    *,
    generator: InsightGenerator | None = None,
    retriever: Retriever | None = None,
    datasets: Datasets | None = None,
) -> AppContext:
    generator = generator or build_generator(build_model_slots(settings))
    retriever = retriever or build_retriever(settings)
    datasets = datasets or build_datasets(settings.datasets_dir)
    return AppContext(
        settings=settings,
        generator=generator,
        retriever=retriever,
        datasets=datasets,
        insight=InsightPipeline(generator, retriever, datasets, settings),
    )


def create_app(
    settings: Settings | None = None,
    *,
    generator: InsightGenerator | None = None,
    retriever: Retriever | None = None,
    datasets: Datasets | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ctx = build_context(settings, generator=generator, retriever=retriever, datasets=datasets)
        app.state.ctx = ctx
        log.info(
            "app.started",
            mode=ctx.mode.value,
            corpus_available=ctx.retriever.available,
            datasets_available=ctx.datasets.available,
        )
        yield

    application = FastAPI(
        title="Alfa News Insights — AI-Service",
        version=__version__,
        description=(
            "Генерация инсайтов «Новость → Инсайт», чат по карточке, оценка важности, "
            "сбор новостей и поиск по отчётам Альфа-Банка. Контракт: "
            "specs/001-ai-service/contracts/openapi.yaml."
        ),
        lifespan=lifespan,
    )
    application.middleware("http")(request_id_middleware)
    install_error_handlers(application)
    application.include_router(health.router)
    application.include_router(insight.router)
    return application


app = create_app()
