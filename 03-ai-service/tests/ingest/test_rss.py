from pathlib import Path

import httpx
import pytest

from ai_service.ingest.normalize import to_news_item
from ai_service.ingest.rss import fetch_source, parse_feed
from ai_service.ingest.sources import DEFAULT_SOURCES
from ai_service.schemas.common import NewsCategory

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rss"
CBR = next(s for s in DEFAULT_SOURCES if s.name == "cbr_press")
RBC = next(s for s in DEFAULT_SOURCES if s.name == "rbc")


def test_parse_cbr_feed() -> None:
    entries = parse_feed((FIXTURES / "cbr_press.xml").read_bytes())
    assert len(entries) == 3
    first = entries[0]
    assert first.link.startswith("https://www.cbr.ru/press/PR/")
    assert first.published is not None and first.published.tzinfo is not None
    assert "<p>" in first.summary  # сырой HTML — чистится при нормализации
    item = to_news_item(first, CBR)
    assert item is not None
    assert "<" not in item.summary_facts and "&nbsp;" not in item.summary_facts
    assert item.source == "Банк России (пресс-релизы)"
    assert item.topic == NewsCategory.MONETARY_POLICY
    assert item.category == "Финансы и ДКП"
    assert item.id == to_news_item(first, CBR).id  # стабильный uuid5 от URL


def test_parse_rbc_full_text() -> None:
    entries = parse_feed((FIXTURES / "rbc_full.xml").read_bytes())
    assert entries and entries[0].full_text
    item = to_news_item(entries[0], RBC)
    assert item is not None
    assert item.full_text and "Оставайтесь на связи с РБК" not in item.full_text
    assert item.source == "РБК"


def test_parse_garbage_returns_empty() -> None:
    assert parse_feed(b"not xml at all") == []


async def _transport(status: int = 200, body: bytes = b"") -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_source_ok() -> None:
    async with await _transport(200, (FIXTURES / "interfax.xml").read_bytes()) as client:
        entries, status = await fetch_source(client, DEFAULT_SOURCES[3], 5.0)
    assert status.ok and status.fetched == 3 and len(entries) == 3


@pytest.mark.parametrize("code", [500, 404])
async def test_fetch_source_http_error(code: int) -> None:
    async with await _transport(code, b"") as client:
        entries, status = await fetch_source(client, CBR, 5.0)
    assert entries == []
    assert status.ok is False
    assert status.error == f"HTTP {code}"


async def test_fetch_source_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        entries, status = await fetch_source(client, CBR, 5.0)
    assert entries == [] and status.ok is False and status.error == "ConnectError"
