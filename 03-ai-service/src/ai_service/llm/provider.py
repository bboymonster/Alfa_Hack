"""Слоты моделей: fast (классификация), main (генерация), checker (самопроверка)."""

from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ai_service.config import Settings
from ai_service.llm.callbacks import LlmLogCallback

SLOT_FAST = "fast"
SLOT_MAIN = "main"
SLOT_CHECKER = "checker"


@dataclass(frozen=True)
class ModelSlots:
    fast: BaseChatModel
    main: BaseChatModel
    checker: BaseChatModel
    names: dict[str, str]


def _chat_model(settings: Settings, slot: str, model: str) -> BaseChatModel:
    # Ретраи делает LangGraph RetryPolicy на уровне ноды, поэтому max_retries=0.
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_s,
        max_retries=0,
        max_tokens=settings.llm_max_tokens,
        temperature=0,
        # Шлюз поддерживает reasoning как OpenRouter. Иначе Qwen/GLM тратят
        # лимит ответа на thinking и обрывают JSON (проверено на реальном API).
        extra_body=(
            {"reasoning": {"enabled": settings.llm_reasoning_enabled}}
            if model != "google/gemma-4-26b-a4b-it"
            else None
        ),
        callbacks=[LlmLogCallback(slot, model)],
    )


def build_model_slots(settings: Settings) -> ModelSlots | None:
    """None, если ключа нет: сервис работает в offline-режиме."""
    if not settings.llm_enabled:
        return None
    names = {
        SLOT_FAST: settings.llm_model_fast,
        SLOT_MAIN: settings.llm_model_main,
        SLOT_CHECKER: settings.llm_model_checker,
    }
    return ModelSlots(
        fast=_chat_model(settings, SLOT_FAST, names[SLOT_FAST]),
        main=_chat_model(settings, SLOT_MAIN, names[SLOT_MAIN]),
        checker=_chat_model(settings, SLOT_CHECKER, names[SLOT_CHECKER]),
        names=names,
    )
