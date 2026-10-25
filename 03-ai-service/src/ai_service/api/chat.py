from fastapi import APIRouter

from ai_service.api.deps import Ctx, RequestId
from ai_service.schemas.chat import AskRequest, AskResponse

router = APIRouter(prefix="/v1", tags=["Чат"])


@router.post("/ask", response_model=AskResponse, summary="Вопрос пользователя по карточке")
async def ask(body: AskRequest, ctx: Ctx, request_id: RequestId) -> AskResponse:
    return await ctx.chat.answer(body, request_id)
