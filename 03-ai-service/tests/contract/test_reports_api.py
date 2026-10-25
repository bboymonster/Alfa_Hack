from collections.abc import Callable
from typing import Any

import httpx


async def test_list_reports(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/v1/reports")
    assert response.status_code == 200
    body = response.json()
    assert body["corpus_available"] is True
    assert body["reports"][0]["file"] == "ALFA-Macro_Insights-Policy_Rate_11Sep.pdf"
    assert body["reports"][0]["extractor"] == "ocr"


async def test_search_ok(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/v1/reports/search", params={"q": "ставка", "k": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "ставка"
    assert body["results"][0]["page"] == 2
    assert body["results"][0]["chunk_id"]


async def test_search_validation(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/v1/reports/search", params={"q": "", "k": 2})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_search_without_corpus_is_503(make_client: Callable[..., Any]) -> None:
    async with make_client() as client:
        listing = await client.get("/v1/reports")
        response = await client.get("/v1/reports/search", params={"q": "ставка"})
    assert listing.json() == {"corpus_available": False, "reports": []}
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "corpus_error"
