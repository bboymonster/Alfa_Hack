import shutil

from fastapi import APIRouter

from ai_service import __version__
from ai_service.api.deps import Ctx
from ai_service.logging import get_logger
from ai_service.schemas.common import CorpusStatus, HealthResponse

log = get_logger(__name__)
router = APIRouter(tags=["Состояние"])


@router.get("/health", response_model=HealthResponse, summary="Состояние сервиса")
def health(ctx: Ctx) -> HealthResponse:
    # Liveness не зависит от корпуса: битый индекс помечает corpus.available=false,
    # а не роняет /health (иначе backend с depends_on: service_healthy не стартует).
    try:
        corpus = ctx.retriever.stats()
    except Exception as exc:
        log.warning("health.corpus_stats_failed", error=type(exc).__name__)
        corpus = CorpusStatus(available=False)
    return HealthResponse(
        mode=ctx.mode,
        version=__version__,
        models=ctx.generator.models,
        corpus=corpus,
        ocr_available=shutil.which("tesseract") is not None,
    )
