"""Загрузка и разбор RSS (feedparser). Полный текст РБК — элемент rbc_news:full-text."""

import calendar
import time
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx

from ai_service.ingest.normalize import RawEntry
from ai_service.logging import get_logger
from ai_service.schemas.ingest import NewsSource, SourceStatus

log = get_logger(__name__)

FULL_TEXT_KEYS = ("rbc_news_full-text", "rbc_news_fulltext", "content_encoded")


def _published(entry: dict[str, Any]) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)
    return None


def _full_text(entry: dict[str, Any]) -> str | None:
    for key in FULL_TEXT_KEYS:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value
    content = entry.get("content")
    if isinstance(content, list) and content:
        value = content[0].get("value") if isinstance(content[0], dict) else None
        if isinstance(value, str) and value.strip():
            return value
    return None


def parse_feed(content: bytes | str) -> list[RawEntry]:
    feed = feedparser.parse(content)
    entries: list[RawEntry] = []
    for entry in feed.entries:
        link = str(entry.get("link") or "").strip()
        title = str(entry.get("title") or "").strip()
        if not link or not title:
            continue
        entries.append(
            RawEntry(
                title=title,
                link=link,
                summary=str(entry.get("summary") or ""),
                published=_published(entry),
                full_text=_full_text(entry),
            )
        )
    return entries


async def fetch_source(
    client: httpx.AsyncClient, source: NewsSource, timeout_s: float
) -> tuple[list[RawEntry], SourceStatus]:
    started = time.perf_counter()
    try:
        response = await client.get(source.url, timeout=timeout_s)
        response.raise_for_status()
        entries = parse_feed(response.content)
    except httpx.HTTPStatusError as exc:
        status = SourceStatus(
            name=source.name,
            ok=False,
            error=f"HTTP {exc.response.status_code}",
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        log.warning("rss.fetch_failed", source=source.name, error=status.error)
        return [], status
    except Exception as exc:
        status = SourceStatus(
            name=source.name,
            ok=False,
            error=type(exc).__name__,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        log.warning("rss.fetch_failed", source=source.name, error=status.error)
        return [], status
    status = SourceStatus(
        name=source.name,
        ok=True,
        fetched=len(entries),
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    return entries, status
