from fastapi import APIRouter

from ai_service.api.deps import Ctx, RequestId
from ai_service.schemas.insight import InsightRequest, InsightResponse

router = APIRouter(prefix="/v1", tags=["Инсайт"])


@router.post(
    "/insight",
    response_model=InsightResponse,
    summary="Инсайт по новости для компании и роли (6 вопросов ТЗ)",
)
async def insight(body: InsightRequest, ctx: Ctx, request_id: RequestId) -> InsightResponse:
    return await ctx.insight.run(body, request_id)
