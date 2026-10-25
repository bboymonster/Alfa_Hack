from collections.abc import Callable
from typing import Any

import httpx

from ai_service.config import Settings
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.news import NewsItem
from ai_service.schemas.score import Adjustment, AdjustmentList, ScoreRequest
from ai_service.scoring.service import ScoringService


def _body(company: CompanyProfile, role: str, *news: NewsItem) -> dict[str, Any]:
    return {
        "company": company.model_dump(mode="json"),
        "role": role,
        "news": [n.model_dump(mode="json") for n in news],
    }


async def test_score_batch_keeps_order(
    app_client: httpx.AsyncClient,
    company_u1595: CompanyProfile,
    news_labor: NewsItem,
    news_key_rate: NewsItem,
    news_steel: NewsItem,
) -> None:
    response = await app_client.post(
        "/v1/score", json=_body(company_u1595, "ACCOUNTANT", news_labor, news_key_rate, news_steel)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [s["news_id"] for s in body["scores"]] == [
        news_labor.id,
        news_key_rate.id,
        news_steel.id,
    ]
    assert all(1 <= s["score"] <= 10 for s in body["scores"])
    assert all(s["factors"] for s in body["scores"])
    assert body["mode"] == "offline"


async def test_role_changes_score(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile, news_labor: NewsItem
) -> None:
    accountant = await app_client.post(
        "/v1/score", json=_body(company_u1595, "ACCOUNTANT", news_labor)
    )
    ceo = await app_client.post("/v1/score", json=_body(company_u1595, "CEO", news_labor))
    assert accountant.json()["scores"][0]["score"] > ceo.json()["scores"][0]["score"]


async def test_score_validation(
    app_client: httpx.AsyncClient, company_u1595: CompanyProfile
) -> None:
    response = await app_client.post("/v1/score", json=_body(company_u1595, "CFO"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_llm_adjustment_applied_and_clipped(
    settings: Settings,
    fake_generator_factory: Callable[..., Any],
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
    news_steel: NewsItem,
) -> None:
    generator = fake_generator_factory(
        adjustments=AdjustmentList(
            adjustments=[
                Adjustment(news_id=news_key_rate.id, delta=1, reason="прямое влияние на долг"),
                Adjustment(news_id=news_steel.id, delta=-1, reason="не отрасль компании"),
            ]
        )
    )
    service = ScoringService(generator, settings)
    response = await service.score_batch(
        ScoreRequest(company=company_u1595, role="CFO", news=[news_key_rate, news_steel]), "r"
    )
    rate, steel = response.scores
    assert rate.score == 10  # 9+ с клипом
    assert rate.factors[-1].name == "llm_adjustment" and rate.factors[-1].delta == 1
    assert steel.factors[-1].delta == -1
    assert response.mode == "llm"
