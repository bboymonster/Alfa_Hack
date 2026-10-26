"""structlog: JSON в проде, консоль локально; request_id в контексте; события LLM-вызовов
без текстов промптов и ответов (принцип III конституции)."""

import logging
import re
import sys
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.requests import Request
from starlette.responses import Response

from ai_service.config import Settings

REQUEST_ID_HEADER = "X-Request-ID"


def configure_logging(settings: Settings) -> None:
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    # Логи — в stderr, чтобы CLI мог печатать JSON-результат в stdout.
    logging.basicConfig(level=level, stream=sys.stderr, format="%(message)s", force=True)
    renderer: structlog.types.Processor
    if settings.log_format == "console":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        # sys.stderr резолвится при каждом вызове: pytest подменяет потоки между тестами.
        logger_factory=lambda *_: structlog.PrintLogger(file=sys.stderr),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]


_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9_.:\-]{1,64}")


def new_request_id() -> str:
    return uuid.uuid4().hex


async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    # Чужой заголовок эхом уходит в ответ и во все логи — принимаем только безопасный формат.
    request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else new_request_id()
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
    try:
        response = await call_next(request)
    finally:
        structlog.contextvars.clear_contextvars()
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def log_llm_call(
    *,
    slot: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int,
    ok: bool = True,
    error: str | None = None,
) -> None:
    get_logger("ai_service.llm").info(
        "llm.call",
        slot=slot,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        ok=ok,
        error=error,
    )
