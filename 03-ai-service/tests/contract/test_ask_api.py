from collections.abc import Callable
from typing import Any

import httpx

from ai_service.schemas.card_fixture import BACKEND_MOCK_INSIGHT
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.news import NewsItem


def _body(company: CompanyProfile, news: NewsItem, question: str) -> dict[str, Any]:
    return {
        "news": news.model_dump(mode="json"),
        "card": BACKEND_MOCK_INSIGHT,
        "company": company.model_dump(mode="json"),
        "role": "CFO",
        "question": question,
    }


async def test_ask_contract(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    response = await app_client.post(
        "/v1/ask", json=_body(company_u1595, news_key_rate, "Как это влияет на наш долг?")
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"request_id", "mode", "answer", "sources", "on_topic"}
    assert body["on_topic"] is True
    assert body["mode"] == "offline"
    assert any(s["kind"] == "report" and s["page"] == 2 for s in body["sources"])


async def test_ask_offtopic(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    response = await app_client.post(
        "/v1/ask", json=_body(company_u1595, news_key_rate, "Напиши стихотворение")
    )
    assert response.status_code == 200
    assert response.json()["on_topic"] is False


async def test_ask_question_too_long(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    response = await app_client.post(
        "/v1/ask", json=_body(company_u1595, news_key_rate, "x" * 2001)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_ask_blank_question(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    response = await app_client.post("/v1/ask", json=_body(company_u1595, news_key_rate, "   "))
    assert response.status_code == 422


async def test_ask_deterministic_offline(
    make_client: Callable[..., Any], company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    async with make_client() as client:
        first = await client.post(
            "/v1/ask", json=_body(company_u1595, news_key_rate, "Что делать?")
        )
        second = await client.post(
            "/v1/ask", json=_body(company_u1595, news_key_rate, "Что делать?")
        )
    assert first.json()["answer"] == second.json()["answer"]
