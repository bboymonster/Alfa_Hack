import asyncio
from typing import Annotated

from fastapi import APIRouter, Query

from ai_service.api.deps import Ctx
from ai_service.errors import ApiError, ErrorCode
from ai_service.schemas.reports import ReportsResponse, SearchResponse

router = APIRouter(prefix="/v1/reports", tags=["Отчёты банка"])


@router.get("", response_model=ReportsResponse, summary="Проиндексированные отчёты")
async def list_reports(ctx: Ctx) -> ReportsResponse:
    reports = await asyncio.to_thread(ctx.retriever.list_reports)
    return ReportsResponse(corpus_available=ctx.retriever.available, reports=reports)


@router.get("/search", response_model=SearchResponse, summary="Поиск по корпусу отчётов")
async def search(
    ctx: Ctx,
    q: Annotated[str, Query(min_length=1, max_length=500)],
    k: Annotated[int, Query(ge=1, le=20)] = 5,
) -> SearchResponse:
    if not ctx.retriever.available:
        raise ApiError(
            ErrorCode.CORPUS_ERROR,
            "Индекс отчётов не построен: выполните `ai-service index-reports`.",
        )
    try:
        results = await asyncio.to_thread(ctx.retriever.search, q, k)
    except Exception as exc:
        raise ApiError(ErrorCode.CORPUS_ERROR, f"Сбой поиска: {type(exc).__name__}") from exc
    return SearchResponse(query=q, results=results, corpus_available=True)
