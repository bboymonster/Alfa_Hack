from typing import Annotated

from fastapi import Depends, Request

from ai_service.app_context import AppContext


def get_ctx(request: Request) -> AppContext:
    ctx: AppContext = request.app.state.ctx
    return ctx


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or "")


Ctx = Annotated[AppContext, Depends(get_ctx)]
RequestId = Annotated[str, Depends(get_request_id)]
