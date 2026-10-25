"""Генераторы: протокол + LLM-реализация (structured output) + offline-шаблоны.

Граф агента одинаков для обоих режимов; различается только генератор.
"""

import json
from typing import Protocol, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ai_service.agent.context import (
    ChatContext,
    DraftContext,
    card_json,
    chunks_block,
    company_block,
    counterparties_block,
    features_block,
    role_focus_text,
)
from ai_service.agent.rules import ROLE_FOCUS, classify_topic_offline, extract_keywords
from ai_service.llm.offline import offline_answer, offline_draft
from ai_service.llm.provider import ModelSlots
from ai_service.prompts import PROMPT_VERSION
from ai_service.prompts.chat import CHAT_SYSTEM, CHAT_USER
from ai_service.prompts.check import CHECK_SYSTEM, CHECK_USER
from ai_service.prompts.classify import (
    PLAN_SYSTEM,
    PLAN_USER,
    RELEVANCE_SYSTEM,
    RELEVANCE_USER,
    SCORE_ADJUST_SYSTEM,
    SCORE_ADJUST_USER,
)
from ai_service.prompts.insight import FEEDBACK_BLOCK, INSIGHT_SYSTEM, INSIGHT_USER
from ai_service.schemas.chat import ChatDraft
from ai_service.schemas.common import Mode, NewsCategory, Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.insight import CheckReport, NewsPlan, SixQuestions
from ai_service.schemas.news import NewsItem
from ai_service.schemas.score import AdjustmentList, ImportanceScore

T = TypeVar("T", bound=BaseModel)


class NewsClassification(BaseModel):
    news_id: str
    relevant: bool
    topic: NewsCategory


class NewsClassificationList(BaseModel):
    items: list[NewsClassification]


class LLMCheck(BaseModel):
    passed: bool
    violations: list[str] = Field(default_factory=list, max_length=10)


class InsightGenerator(Protocol):
    @property
    def mode(self) -> Mode: ...

    @property
    def models(self) -> dict[str, str]: ...

    @property
    def prompt_version(self) -> str: ...

    async def plan(self, news: NewsItem) -> NewsPlan: ...

    async def draft(self, ctx: DraftContext, feedback: list[str]) -> SixQuestions: ...

    async def check(self, ctx: DraftContext, draft: SixQuestions) -> CheckReport: ...

    async def answer(self, ctx: ChatContext) -> ChatDraft: ...

    async def classify_news(self, items: list[NewsItem]) -> list[NewsClassification]: ...

    async def adjust_scores(
        self,
        company: CompanyProfile,
        role: Role,
        items: list[tuple[NewsItem, ImportanceScore]],
    ) -> AdjustmentList: ...


def plan_offline(news: NewsItem) -> NewsPlan:
    topic = news.topic or classify_topic_offline(news.text_for_analysis)
    keywords = extract_keywords(news.text_for_analysis, topic)
    queries = [news.title]
    if keywords:
        queries.append(" ".join(keywords[:5]))
    return NewsPlan(topic=topic, keywords=keywords, queries=queries[:4])


class OfflineGenerator:
    """Детерминированные шаблоны: демо и тесты без сети и ключа."""

    mode = Mode.OFFLINE
    prompt_version = PROMPT_VERSION

    @property
    def models(self) -> dict[str, str]:
        return {}

    async def plan(self, news: NewsItem) -> NewsPlan:
        return plan_offline(news)

    async def draft(self, ctx: DraftContext, feedback: list[str]) -> SixQuestions:
        return offline_draft(ctx)

    async def check(self, ctx: DraftContext, draft: SixQuestions) -> CheckReport:
        # Правила противоречий применяет нода self_check; шаблоны их не нарушают.
        return CheckReport(passed=True)

    async def answer(self, ctx: ChatContext) -> ChatDraft:
        return offline_answer(ctx)

    async def classify_news(self, items: list[NewsItem]) -> list[NewsClassification]:
        return [
            NewsClassification(
                news_id=item.id,
                relevant=True,
                topic=item.topic or classify_topic_offline(item.text_for_analysis),
            )
            for item in items
        ]

    async def adjust_scores(
        self,
        company: CompanyProfile,
        role: Role,
        items: list[tuple[NewsItem, ImportanceScore]],
    ) -> AdjustmentList:
        return AdjustmentList(adjustments=[])


class LLMGenerator:
    """Реальные модели через structured output; слоты fast/main/checker."""

    mode = Mode.LLM
    prompt_version = PROMPT_VERSION

    def __init__(self, slots: ModelSlots) -> None:
        self.slots = slots
        self.models = dict(slots.names)

    @staticmethod
    async def _structured(model: BaseChatModel, schema: type[T], system: str, user: str) -> T:
        runnable = model.with_structured_output(schema)
        result = await runnable.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        if isinstance(result, schema):
            return result
        if isinstance(result, dict):
            return schema.model_validate(result)
        raise TypeError(f"Неожиданный тип structured output: {type(result).__name__}")

    async def plan(self, news: NewsItem) -> NewsPlan:
        user = PLAN_USER.format(
            title=news.title, summary=news.summary_facts, category=news.category
        )
        plan = await self._structured(self.slots.fast, NewsPlan, PLAN_SYSTEM, user)
        if not plan.queries:
            plan.queries = [news.title]
        return plan

    async def draft(self, ctx: DraftContext, feedback: list[str]) -> SixQuestions:
        full_text_block = f"Полный текст: {ctx.news_text}" if ctx.news.full_text else ""
        feedback_block = (
            FEEDBACK_BLOCK.format(violations="\n".join(f"- {v}" for v in feedback))
            if feedback
            else ""
        )
        user = INSIGHT_USER.format(
            title=ctx.news.title,
            summary=ctx.news.summary_facts,
            full_text_block=full_text_block,
            source=ctx.news.source,
            published_at=ctx.news.published_at.date().isoformat(),
            topic=ctx.plan.topic.value,
            company_block=company_block(ctx.company),
            features_block=features_block(ctx.triggers),
            counterparties_block=counterparties_block(ctx.counterparties),
            role=ctx.role.value,
            role_focus=role_focus_text(ctx.role),
            chunks_block=chunks_block(ctx.chunks),
            feedback_block=feedback_block,
        )
        return await self._structured(self.slots.main, SixQuestions, INSIGHT_SYSTEM, user)

    async def check(self, ctx: DraftContext, draft: SixQuestions) -> CheckReport:
        user = CHECK_USER.format(
            features_block=features_block(ctx.triggers),
            chunks_block=chunks_block(ctx.chunks, max_chars=600),
            title=ctx.news.title,
            summary=ctx.news.summary_facts,
            draft_json=json.dumps(draft.model_dump(), ensure_ascii=False),
        )
        result = await self._structured(self.slots.checker, LLMCheck, CHECK_SYSTEM, user)
        return CheckReport(passed=result.passed, violations=result.violations)

    async def answer(self, ctx: ChatContext) -> ChatDraft:
        user = CHAT_USER.format(
            title=ctx.news.title,
            summary=ctx.news.summary_facts,
            card_json=card_json(ctx.card),
            company_block=company_block(ctx.company),
            role=ctx.role.value,
            role_focus=role_focus_text(ctx.role),
            chunks_block=chunks_block(ctx.chunks, max_chars=800),
            question=ctx.question,
        )
        return await self._structured(self.slots.main, ChatDraft, CHAT_SYSTEM, user)

    async def classify_news(self, items: list[NewsItem]) -> list[NewsClassification]:
        if not items:
            return []
        block = "\n".join(f"{i.id} | {i.title} | {i.summary_facts[:300]}" for i in items)
        result = await self._structured(
            self.slots.fast,
            NewsClassificationList,
            RELEVANCE_SYSTEM,
            RELEVANCE_USER.format(items_block=block),
        )
        return result.items

    async def adjust_scores(
        self,
        company: CompanyProfile,
        role: Role,
        items: list[tuple[NewsItem, ImportanceScore]],
    ) -> AdjustmentList:
        if not items:
            return AdjustmentList(adjustments=[])
        block = "\n".join(
            f"{news.id} | {score.score} | {news.title} | {news.summary_facts[:300]}"
            for news, score in items
        )
        return await self._structured(
            self.slots.fast,
            AdjustmentList,
            SCORE_ADJUST_SYSTEM,
            SCORE_ADJUST_USER.format(
                company_block=company_block(company),
                role=role.value,
                role_focus=f"{ROLE_FOCUS[role].title}: {ROLE_FOCUS[role].description}",
                items_block=block,
            ),
        )


def build_generator(slots: ModelSlots | None) -> InsightGenerator:
    return LLMGenerator(slots) if slots else OfflineGenerator()
