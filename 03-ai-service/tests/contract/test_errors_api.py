"""Формат ошибок роутера и устойчивость /health к сбоям корпуса."""

from collections.abc import Callable
from typing import Any

import httpx

from ai_service.schemas.common import CorpusStatus


async def test_unknown_route_uses_error_envelope(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/v1/nope")
    assert response.status_code == 404
    body = response.json()["error"]
    assert body["code"] == "not_found"
    assert body["request_id"] == response.headers["X-Request-ID"]


async def test_method_not_allowed_uses_error_envelope(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/v1/insight")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "request_error"


async def test_unsafe_request_id_is_replaced(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/health", headers={"X-Request-ID": "x" * 200 + "\t<script>"})
    assert response.status_code == 200
    echoed = response.headers["X-Request-ID"]
    assert echoed != "x" * 200 + "\t<script>"
    assert len(echoed) == 32


class BrokenCorpusRetriever:
    @property
    def available(self) -> bool:
        return True

    def stats(self) -> CorpusStatus:
        raise RuntimeError("Storage folder already accessed")

    def search(self, query: str, k: int) -> list[Any]:
        return []

    def list_reports(self) -> list[Any]:
        return []


async def test_health_survives_broken_corpus(make_client: Callable[..., Any]) -> None:
    async with make_client(retriever=BrokenCorpusRetriever()) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["corpus"]["available"] is False
