"""Сбор новостей: параллельный fetch источников → нормализация → фильтры → дедуп → отчёт."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx

from ai_service.config import Settings
from ai_service.ingest.dedupe import dedupe, normalize_url
from ai_service.ingest.normalize import RawEntry, to_news_item
from ai_service.ingest.relevance import is_relevant
from ai_service.ingest.rss import fetch_source
from ai_service.ingest.sources import load_sources
from ai_service.llm.generator import InsightGenerator
from ai_service.logging import get_logger
from ai_service.schemas.common import CATEGORY_LABELS_RU, Mode
from ai_service.schemas.ingest import (
    CollectReport,
    CollectRequest,
    CollectResponse,
    NewsSource,
    SourceStatus,
)
from ai_service.schemas.news import NewsItem

log = get_logger(__name__)

Fetcher = Callable[
    [httpx.AsyncClient, NewsSource, float], Awaitable[tuple[list[RawEntry], SourceStatus]]
]


class NewsCollector:
    def __init__(
        self,
        generator: InsightGenerator,
        settings: Settings,
        fetcher: Fetcher = fetch_source,
    ) -> None:
        self.generator = generator
        self.settings = settings
        self.fetcher = fetcher

    def _select_sources(self, request: CollectRequest) -> list[NewsSource]:
        sources = load_sources(self.settings)
        if request.sources:
            wanted = set(request.sources)
            sources = [s for s in sources if s.name in wanted]
        return sources

    async def collect(self, request: CollectRequest, request_id: str) -> CollectResponse:
        started = time.perf_counter()
        sources = self._select_sources(request)
        now = datetime.now(UTC)
        statuses: list[SourceStatus] = []
        raw_items: list[NewsItem] = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AlfaNewsInsights/0.1)"},
        ) as client:
            results = await asyncio.gather(
                *(
                    self.fetcher(client, source, self.settings.news_fetch_timeout_s)
                    for source in sources
                ),
                return_exceptions=True,
            )
        for source, result in zip(sources, results, strict=True):
            if isinstance(result, BaseException):
                statuses.append(
                    SourceStatus(name=source.name, ok=False, error=type(result).__name__)
                )
                continue
            entries, status = result
            statuses.append(status)
            for raw in entries:
                item = to_news_item(raw, source, now)
                if item is not None:
                    raw_items.append(item)

        older_dropped = 0
        excluded = {normalize_url(u) for u in request.exclude_urls}
        filtered: list[NewsItem] = []
        for item in raw_items:
            if request.since and item.published_at <= _aware(request.since):
                older_dropped += 1
                continue
            if item.source_url and normalize_url(item.source_url) in excluded:
                older_dropped += 1
                continue
            filtered.append(item)

        filtered.sort(key=lambda i: i.published_at, reverse=True)
        unique, duplicates_dropped = dedupe(filtered)

        relevant, irrelevant_dropped = await self._filter_relevant(unique)
        items = relevant[: request.limit]

        log.info(
            "news.collected",
            sources=len(sources),
            fetched=len(raw_items),
            returned=len(items),
            duplicates=duplicates_dropped,
            irrelevant=irrelevant_dropped,
            older=older_dropped,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return CollectResponse(
            request_id=request_id,
            mode=self.generator.mode,
            items=items,
            report=CollectReport(
                sources=statuses,
                returned=len(items),
                duplicates_dropped=duplicates_dropped,
                irrelevant_dropped=irrelevant_dropped,
                older_dropped=older_dropped,
            ),
        )

    async def _filter_relevant(self, items: list[NewsItem]) -> tuple[list[NewsItem], int]:
        if self.generator.mode == Mode.LLM and items:
            try:
                verdicts = {c.news_id: c for c in await self.generator.classify_news(items)}
            except Exception as exc:
                log.warning("news.classify_failed", error=type(exc).__name__)
                verdicts = {}
            if verdicts:
                kept: list[NewsItem] = []
                for item in items:
                    verdict = verdicts.get(item.id)
                    if verdict is None:
                        if is_relevant(item):
                            kept.append(item)
                        continue
                    if verdict.relevant:
                        kept.append(
                            item.model_copy(
                                update={
                                    "topic": verdict.topic,
                                    "category": CATEGORY_LABELS_RU[verdict.topic],
                                }
                            )
                        )
                return kept, len(items) - len(kept)
        kept = [item for item in items if is_relevant(item)]
        return kept, len(items) - len(kept)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)
