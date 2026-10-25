from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ai_service.ingest.normalize import RawEntry
from ai_service.ingest.rss import parse_feed
from ai_service.schemas.ingest import NewsSource, SourceStatus

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rss"


def _fake_fetcher(feeds: dict[str, bytes], failing: set[str] | None = None) -> Callable[..., Any]:
    async def fetch(
        client: httpx.AsyncClient, source: NewsSource, timeout_s: float
    ) -> tuple[list[RawEntry], SourceStatus]:
        if failing and source.name in failing:
            return [], SourceStatus(name=source.name, ok=False, error="HTTP 500")
        entries = parse_feed(feeds.get(source.name, b""))
        return entries, SourceStatus(name=source.name, ok=True, fetched=len(entries))

    return fetch


async def test_collect_contract(make_client: Callable[..., Any]) -> None:
    feeds = {
        "cbr_press": (FIXTURES / "cbr_press.xml").read_bytes(),
        "rbc": (FIXTURES / "rbc_full.xml").read_bytes(),
    }
    fetcher = _fake_fetcher(feeds, failing={"interfax"})
    async with make_client(fetcher=fetcher) as client:
        response = await client.post("/v1/news/collect", json={"limit": 10})
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"request_id", "mode", "items", "report"}
    statuses = {s["name"]: s for s in body["report"]["sources"]}
    assert statuses["interfax"]["ok"] is False and statuses["interfax"]["error"] == "HTTP 500"
    assert statuses["cbr_press"]["ok"] is True and statuses["cbr_press"]["fetched"] == 3
    assert body["report"]["returned"] == len(body["items"]) >= 3
    for item in body["items"]:
        assert item["id"] and item["title"] and item["summary_facts"] and item["published_at"]
        assert item["category"] and item["topic"]
    # лента ЦБ по ставке — релевантна и классифицирована
    assert any(i["topic"] == "monetary_policy" for i in body["items"])


async def test_collect_since_and_exclude(make_client: Callable[..., Any]) -> None:
    feeds = {"cbr_press": (FIXTURES / "cbr_press.xml").read_bytes()}
    async with make_client(fetcher=_fake_fetcher(feeds)) as client:
        full = await client.post("/v1/news/collect", json={"sources": ["cbr_press"]})
        items = full.json()["items"]
        exclude = [items[0]["source_url"]]
        partial = await client.post(
            "/v1/news/collect", json={"sources": ["cbr_press"], "exclude_urls": exclude}
        )
        future = await client.post(
            "/v1/news/collect",
            json={"sources": ["cbr_press"], "since": datetime(2099, 1, 1, tzinfo=UTC).isoformat()},
        )
    assert partial.json()["report"]["returned"] == len(items) - 1
    assert partial.json()["report"]["older_dropped"] == 1
    assert future.json()["items"] == []
    assert future.json()["report"]["older_dropped"] == len(items)


async def test_collect_empty_body_and_validation(make_client: Callable[..., Any]) -> None:
    async with make_client(fetcher=_fake_fetcher({})) as client:
        empty = await client.post("/v1/news/collect")
        bad = await client.post("/v1/news/collect", json={"limit": 0})
    assert empty.status_code == 200 and empty.json()["items"] == []
    assert bad.status_code == 422
