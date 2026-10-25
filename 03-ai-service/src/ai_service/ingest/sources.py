"""Источники новостей. Проверены 2026-10-25 (см. specs/001-ai-service/research.md, R8)."""

import json

from ai_service.config import Settings
from ai_service.schemas.common import NewsCategory
from ai_service.schemas.ingest import NewsSource

DEFAULT_SOURCES: list[NewsSource] = [
    NewsSource(
        name="cbr_press",
        url="https://www.cbr.ru/rss/RssPress",
        source_title="Банк России (пресс-релизы)",
        default_category=NewsCategory.MONETARY_POLICY,
    ),
    NewsSource(
        name="cbr_news",
        url="https://www.cbr.ru/rss/RssNews",
        source_title="Банк России (новости)",
        default_category=NewsCategory.MONETARY_POLICY,
    ),
    NewsSource(
        name="rbc",
        url="https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        source_title="РБК",
    ),
    NewsSource(
        name="interfax",
        url="https://www.interfax.ru/rss.asp",
        source_title="Интерфакс",
    ),
    NewsSource(
        name="kommersant",
        url="https://www.kommersant.ru/RSS/news.xml",
        source_title="Коммерсантъ",
    ),
]


def load_sources(settings: Settings) -> list[NewsSource]:
    """Список источников: JSON из AI_NEWS_SOURCES_JSON или дефолт, отфильтрованный по enabled."""
    if settings.news_sources_json.strip():
        raw = json.loads(settings.news_sources_json)
        sources = [NewsSource.model_validate(item) for item in raw]
    else:
        sources = list(DEFAULT_SOURCES)
    enabled = set(settings.news_sources_enabled)
    return [s for s in sources if s.enabled and (not enabled or s.name in enabled)]
