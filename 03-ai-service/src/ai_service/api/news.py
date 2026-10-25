from fastapi import APIRouter

from ai_service.api.deps import Ctx, RequestId
from ai_service.schemas.ingest import CollectRequest, CollectResponse

router = APIRouter(prefix="/v1/news", tags=["Сбор новостей"])


@router.post(
    "/collect",
    response_model=CollectResponse,
    summary="Собрать и нормализовать новости из настроенных источников",
)
async def collect(
    ctx: Ctx, request_id: RequestId, body: CollectRequest | None = None
) -> CollectResponse:
    return await ctx.collector.collect(body or CollectRequest(), request_id)
