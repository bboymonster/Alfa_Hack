from collections.abc import Callable
from typing import Any

import httpx


async def test_health_with_corpus(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "offline"
    assert body["corpus"]["available"] is True
    assert body["corpus"]["reports"] == 1
    assert body["models"] == {}
    assert response.headers["X-Request-ID"]


async def test_health_without_corpus(make_client: Callable[..., Any]) -> None:
    async with make_client() as client:
        response = await client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.status_code == 200
    assert response.json()["corpus"] == {
        "available": False,
        "reports": 0,
        "chunks": 0,
        "indexed_at": None,
    }
    assert response.headers["X-Request-ID"] == "abc123"


async def test_unknown_route_is_json_404(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/nope")
    assert response.status_code == 404
