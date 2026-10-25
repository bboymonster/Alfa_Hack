from collections.abc import Callable
from typing import Any

import httpx

from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.news import NewsItem

BACKEND_INSIGHT_FIELDS = {
    "why_it_matters",
    "risks",
    "opportunities",
    "action_item",
    "alfa_bank_position",
    "alfa_report_name",
    "alfa_report_page",
    "alfa_report_url",
    "traceability",
}


def _body(company: CompanyProfile, news: NewsItem, role: str = "CFO") -> dict[str, Any]:
    return {
        "news": news.model_dump(mode="json"),
        "company": company.model_dump(mode="json"),
        "role": role,
    }


async def test_insight_contract(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    response = await app_client.post("/v1/insight", json=_body(company_u1595, news_key_rate))
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "request_id",
        "mode",
        "insight",
        "card",
        "importance",
        "traceability",
        "latency_ms",
    }
    assert body["mode"] == "offline"
    assert set(body["card"]) == BACKEND_INSIGHT_FIELDS
    assert isinstance(body["card"]["risks"], list)
    assert isinstance(body["card"]["traceability"]["matched_company_features"], list)
    assert 1 <= body["importance"]["score"] <= 10
    assert body["traceability"]["self_check"]["passed"] is True
    assert body["request_id"] == response.headers["X-Request-ID"]


async def test_insight_accepts_backend_bool_marks(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    payload = _body(company_u1595, news_key_rate)
    payload["company"]["cl_product_loa_mark"] = True
    payload["company"]["fts_flag"] = False
    response = await app_client.post("/v1/insight", json=payload)
    assert response.status_code == 200
    features = response.json()["card"]["traceability"]["matched_company_features"]
    assert "CL_PRODUCT_LOA_MARK=1" in features


async def test_insight_validation_error(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    response = await app_client.post(
        "/v1/insight", json=_body(company_u1595, news_key_rate, role="CTO")
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]
    assert body["error"]["request_id"]


async def test_insight_generator_failure_is_502(
    make_client: Callable[..., Any],
    fake_generator_factory: Callable[..., Any],
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    generator = fake_generator_factory(fail_draft=RuntimeError("boom"))
    async with make_client(generator=generator) as client:
        response = await client.post("/v1/insight", json=_body(company_u1595, news_key_rate))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_error"


async def test_insight_timeout_is_504(
    make_client: Callable[..., Any],
    fake_generator_factory: Callable[..., Any],
    settings: Any,
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    generator = fake_generator_factory(delay_s=0.5)
    fast = settings.model_copy(update={"insight_timeout_s": 0.05})
    async with make_client(generator=generator, settings=fast) as client:
        response = await client.post("/v1/insight", json=_body(company_u1595, news_key_rate))
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "llm_timeout"
