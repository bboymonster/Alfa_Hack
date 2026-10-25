from fastapi import APIRouter

from ai_service.api.deps import Ctx, RequestId
from ai_service.schemas.score import ScoreRequest, ScoreResponse

router = APIRouter(prefix="/v1", tags=["Скоринг"])


@router.post(
    "/score",
    response_model=ScoreResponse,
    summary="Оценка важности новостей для компании и роли (пакетно)",
)
async def score(body: ScoreRequest, ctx: Ctx, request_id: RequestId) -> ScoreResponse:
    return await ctx.scoring.score_batch(body, request_id)
