"""Единая политика повторов LLM-вызовов.

Повторяем сетевые сбои, 429/5xx шлюза и невалидный structured output (модель вернула
обрезанный JSON, markdown-обёртку или нарушила схему). Ошибки конфигурации и клиента
(401, 400, 422 от провайдера) не повторяем — они не исправятся сами.
"""

from langchain_core.exceptions import OutputParserException
from openai import APIConnectionError, APIStatusError, RateLimitError

MAX_CHAT_ATTEMPTS = 2
CHAT_RETRY_DELAY_S = 0.5


def is_retryable(exc: BaseException) -> bool:
    # APITimeoutError — подкласс APIConnectionError; RateLimitError — подкласс APIStatusError.
    if isinstance(exc, APIConnectionError | RateLimitError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    # pydantic.ValidationError и json.JSONDecodeError — подклассы ValueError;
    # TypeError — провайдер вернул None вместо структуры.
    return isinstance(exc, OutputParserException | ValueError | TypeError)
