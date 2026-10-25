import shutil

from fastapi import APIRouter

from ai_service import __version__
from ai_service.api.deps import Ctx
from ai_service.schemas.common import HealthResponse

router = APIRouter(tags=["Состояние"])


@router.get("/health", response_model=HealthResponse, summary="Состояние сервиса")
def health(ctx: Ctx) -> HealthResponse:
    return HealthResponse(
        mode=ctx.mode,
        version=__version__,
        models=ctx.generator.models,
        corpus=ctx.retriever.stats(),
        ocr_available=shutil.which("tesseract") is not None,
    )
