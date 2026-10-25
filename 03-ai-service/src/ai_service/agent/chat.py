"""Чат по карточке: проверка темы, контекст из карточки и отчётов, ответ генератора."""

import asyncio
import re
import time

from ai_service.agent.context import ChatContext
from ai_service.agent.rules import TOPIC_KEYWORDS, classify_topic_offline
from ai_service.config import Settings
from ai_service.errors import ApiError, ErrorCode
from ai_service.llm.generator import InsightGenerator
from ai_service.logging import get_logger
from ai_service.rag.retriever import Retriever
from ai_service.schemas.chat import AskRequest, AskResponse
from ai_service.schemas.common import NewsCategory, SourceRef
from ai_service.schemas.reports import ReportChunk

log = get_logger(__name__)

_TOKEN = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)

# Вопросы, которые заведомо вне карточки.
OFFTOPIC_MARKERS: tuple[str, ...] = (
    "стих",
    "анекдот",
    "шутк",
    "рецепт",
    "погод",
    "песн",
    "сказк",
    "фильм",
    "футбол",
    "гороскоп",
    "переведи",
    "напиши код",
)

# Попытки изменить правила работы ассистента.
INJECTION_MARKERS: tuple[str, ...] = (
    "игнорируй",
    "забудь инструкц",
    "забудь правила",
    "системный промпт",
    "system prompt",
    "раскрой промпт",
    "ты теперь",
    "представь, что ты",
    "jailbreak",
)

# Общие деловые слова: вопрос про компанию/влияние считаем по теме.
BUSINESS_HINTS: tuple[str, ...] = (
    "компани",
    "бизнес",
    "влия",
    "риск",
    "возможност",
    "рекоменд",
    "что делать",
    "как нам",
    "нашей",
    "нашу",
    "наш ",
    "выручк",
    "долг",
    "кредит",
    "депозит",
    "ставк",
    "налог",
    "сотрудник",
    "поставк",
    "банк",
    "отчёт",
    "отчет",
    "прогноз",
    "цен",
    "спрос",
)


def _stems(text: str) -> set[str]:
    return {t.lower()[:5] for t in _TOKEN.findall(text) if len(t) > 3}


def is_on_topic(question: str, news_text: str, card_text: str, topic: NewsCategory) -> bool:
    lowered = question.lower()
    if any(marker in lowered for marker in INJECTION_MARKERS):
        return False
    if any(marker in lowered for marker in OFFTOPIC_MARKERS):
        return False
    if any(hint in lowered for hint in BUSINESS_HINTS):
        return True
    context = _stems(news_text) | _stems(card_text)
    for keyword in TOPIC_KEYWORDS[topic]:
        context |= _stems(keyword)
    overlap = _stems(question) & context
    if overlap:
        return True
    # Короткие уточнения («Что делать?», «Почему?») считаем вопросом по карточке.
    return len(_stems(question)) <= 2


class ChatService:
    def __init__(
        self, generator: InsightGenerator, retriever: Retriever, settings: Settings
    ) -> None:
        self.generator = generator
        self.retriever = retriever
        self.settings = settings

    async def _retrieve(self, request: AskRequest) -> list[ReportChunk]:
        if not self.retriever.available:
            return []
        query = f"{request.question} {request.news.title}"
        try:
            found = await asyncio.to_thread(self.retriever.search, query, 3)
        except Exception as exc:
            log.warning("chat.rag_failed", error=type(exc).__name__)
            return []
        return [
            c
            for c in found
            if (c.dense_score if c.dense_score is not None else c.score or 0.0)
            >= self.settings.rag_min_score
        ]

    async def answer(self, request: AskRequest, request_id: str) -> AskResponse:
        started = time.perf_counter()
        topic = request.news.topic or classify_topic_offline(request.news.text_for_analysis)
        card_text = " ".join(
            [
                request.card.why_it_matters,
                *request.card.risks,
                *request.card.opportunities,
                request.card.action_item,
                request.card.alfa_bank_position or "",
            ]
        )
        on_topic_hint = is_on_topic(
            request.question, request.news.text_for_analysis, card_text, topic
        )
        chunks = await self._retrieve(request) if on_topic_hint else []
        ctx = ChatContext(
            news=request.news,
            card=request.card,
            company=request.company,
            role=request.role,
            question=request.question,
            chunks=chunks,
            on_topic_hint=on_topic_hint,
        )
        try:
            async with asyncio.timeout(self.settings.chat_timeout_s):
                draft = await self.generator.answer(ctx)
        except TimeoutError as exc:
            raise ApiError(
                ErrorCode.LLM_TIMEOUT,
                f"Ответ не уложился в {self.settings.chat_timeout_s:.0f} с.",
            ) from exc
        except ApiError:
            raise
        except Exception as exc:
            log.warning("chat.failed", error=type(exc).__name__)
            raise ApiError(
                ErrorCode.LLM_ERROR, f"Сбой генерации ответа: {type(exc).__name__}."
            ) from exc

        on_topic = on_topic_hint and draft.on_topic
        sources: list[SourceRef] = []
        if on_topic:
            sources.append(
                SourceRef(
                    kind="news",
                    title=f"{request.news.source}: {request.news.title}",
                    url=request.news.source_url,
                )
            )
            used = set(draft.used_chunk_ids)
            for chunk in chunks:
                if chunk.chunk_id in used:
                    sources.append(
                        SourceRef(
                            kind="report",
                            title=chunk.title,
                            url=chunk.url,
                            page=chunk.page,
                            chunk_id=chunk.chunk_id,
                        )
                    )
            if request.card.alfa_report_name and not any(s.kind == "report" for s in sources):
                sources.append(
                    SourceRef(
                        kind="report",
                        title=request.card.alfa_report_name,
                        url=request.card.alfa_report_url,
                        page=request.card.alfa_report_page,
                    )
                )
        log.info(
            "chat.done",
            mode=self.generator.mode.value,
            on_topic=on_topic,
            chunks=len(chunks),
            sources=len(sources),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return AskResponse(
            request_id=request_id,
            mode=self.generator.mode,
            answer=draft.answer,
            sources=sources,
            on_topic=on_topic,
        )
