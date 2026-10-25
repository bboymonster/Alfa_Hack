"""Единый формат ошибок API: {"error": {"code", "message", "request_id", "details"}}."""

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ai_service.logging import get_logger

log = get_logger(__name__)


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    LLM_TIMEOUT = "llm_timeout"
    LLM_ERROR = "llm_error"
    CORPUS_ERROR = "corpus_error"
    INTERNAL_ERROR = "internal_error"


STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.LLM_ERROR: 502,
    ErrorCode.CORPUS_ERROR: 503,
    ErrorCode.INTERNAL_ERROR: 500,
}


class ApiError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: list[dict[str, Any]] | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []
        self.status = status or STATUS_BY_CODE[code]


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or "")


def _payload(
    code: ErrorCode, message: str, request_id: str, details: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code.value,
            "message": message,
            "request_id": request_id,
            "details": details or [],
        }
    }


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        log.warning("api.error", code=exc.code.value, status=exc.status, message=exc.message)
        return JSONResponse(
            status_code=exc.status,
            content=_payload(exc.code, exc.message, _request_id(request), exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": [str(part) for part in err.get("loc", [])], "msg": str(err.get("msg", ""))}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_payload(
                ErrorCode.VALIDATION_ERROR,
                "Неправильные поля запроса.",
                _request_id(request),
                details,
            ),
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("api.unexpected", error_type=type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=_payload(
                ErrorCode.INTERNAL_ERROR, "Внутренняя ошибка AI-сервиса.", _request_id(request)
            ),
        )
