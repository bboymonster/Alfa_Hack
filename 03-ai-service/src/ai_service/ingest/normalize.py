"""Приведение записи RSS к NewsItem: чистка HTML, даты, категория, стабильный id."""

import html
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from ai_service.agent.rules import classify_topic_offline
from ai_service.schemas.common import CATEGORY_LABELS_RU, NewsCategory
from ai_service.schemas.ingest import NewsSource
from ai_service.schemas.news import NewsItem

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_SERVICE_TAILS = (
    "Оставайтесь на связи с РБК",
    "Читайте РБК",
    "Подробнее на РБК",
)

MAX_SUMMARY = 4000
MAX_FULL_TEXT = 20000


@dataclass
class RawEntry:
    title: str
    link: str
    summary: str
    published: datetime | None
    full_text: str | None = None


def strip_html(text: str) -> str:
    text = _TAG.sub(" ", text or "")
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    for tail in _SERVICE_TAILS:
        idx = text.find(tail)
        if idx > 0:
            text = text[:idx]
    return _WS.sub(" ", text).strip()


def news_id_for(url: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url.strip()))


def to_news_item(raw: RawEntry, source: NewsSource, now: datetime | None = None) -> NewsItem | None:
    title = strip_html(raw.title)
    summary = strip_html(raw.summary)
    full_text = strip_html(raw.full_text) if raw.full_text else None
    if not title or not raw.link:
        return None
    if not summary:
        summary = full_text[:MAX_SUMMARY] if full_text else title
    published = raw.published or now or datetime.now(UTC)
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    text = f"{title}\n{summary}"
    topic: NewsCategory = classify_topic_offline(text)
    if topic == NewsCategory.OTHER and source.default_category:
        topic = source.default_category
    return NewsItem(
        id=news_id_for(raw.link),
        title=title[:500],
        summary_facts=summary[:MAX_SUMMARY],
        full_text=full_text[:MAX_FULL_TEXT] if full_text else None,
        source=source.source_title,
        source_url=raw.link.strip()[:2000],
        published_at=published,
        category=CATEGORY_LABELS_RU[topic],
        topic=topic,
    )
