"""Callback LangChain: пишет structlog-событие на каждый вызов модели без текстов."""

import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from ai_service.logging import log_llm_call


class LlmLogCallback(BaseCallbackHandler):
    def __init__(self, slot: str, model: str) -> None:
        self.slot = slot
        self.model = model
        self._started: dict[UUID, float] = {}

    def on_chat_model_start(
        self, serialized: dict[str, Any], messages: Any, *, run_id: UUID, **kwargs: Any
    ) -> None:
        self._started[run_id] = time.perf_counter()

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], *, run_id: UUID, **kwargs: Any
    ) -> None:
        self._started[run_id] = time.perf_counter()

    def _latency(self, run_id: UUID) -> int:
        started = self._started.pop(run_id, None)
        return int((time.perf_counter() - started) * 1000) if started else 0

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        input_tokens: int | None = None
        output_tokens: int | None = None
        usage = (response.llm_output or {}).get("token_usage") or {}
        if usage:
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")
        else:
            for generation in response.generations:
                for item in generation:
                    message = getattr(item, "message", None)
                    meta = getattr(message, "usage_metadata", None)
                    if meta:
                        input_tokens = meta.get("input_tokens")
                        output_tokens = meta.get("output_tokens")
        log_llm_call(
            slot=self.slot,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=self._latency(run_id),
        )

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        log_llm_call(
            slot=self.slot,
            model=self.model,
            input_tokens=None,
            output_tokens=None,
            latency_ms=self._latency(run_id),
            ok=False,
            error=type(error).__name__,
        )
