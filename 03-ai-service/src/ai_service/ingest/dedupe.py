"""Дедупликация новостей: нормализованный URL, нормализованный заголовок, Jaccard токенов."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ai_service.schemas.news import NewsItem

_TOKEN = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)
_TRACKING_PREFIXES = ("utm_", "yclid", "gclid", "fbclid", "from", "ref")
JACCARD_THRESHOLD = 0.8


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PREFIXES)
    ]
    path = parts.path.rstrip("/")
    return urlunsplit(
        (parts.scheme.lower() or "https", parts.netloc.lower(), path, urlencode(query), "")
    )


def normalize_title(title: str) -> str:
    return " ".join(t.lower() for t in _TOKEN.findall(title))


def title_tokens(title: str) -> set[str]:
    return {t.lower() for t in _TOKEN.findall(title) if len(t) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedupe(items: list[NewsItem]) -> tuple[list[NewsItem], int]:
    """Оставляет первую (самую свежую при предварительной сортировке) версию новости."""
    kept: list[NewsItem] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    kept_tokens: list[set[str]] = []
    dropped = 0
    for item in items:
        url_key = normalize_url(item.source_url) if item.source_url else ""
        title_key = normalize_title(item.title)
        tokens = title_tokens(item.title)
        duplicate = (url_key and url_key in seen_urls) or title_key in seen_titles
        if not duplicate:
            duplicate = any(jaccard(tokens, other) >= JACCARD_THRESHOLD for other in kept_tokens)
        if duplicate:
            dropped += 1
            continue
        if url_key:
            seen_urls.add(url_key)
        seen_titles.add(title_key)
        kept_tokens.append(tokens)
        kept.append(item)
    return kept, dropped
