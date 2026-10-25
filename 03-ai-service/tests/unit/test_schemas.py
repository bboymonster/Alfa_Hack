from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_service.schemas.card_fixture import BACKEND_MOCK_INSIGHT
from ai_service.schemas.chat import AskRequest
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.insight import Card
from ai_service.schemas.news import NewsItem


def _profile(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "synthetic_u": "U_1",
        "name": "Тест",
        "mainokved_code": "47.71",
        "mainokved_name": "Розница",
        "cl_product_loa_mark": 1.0,
        "fts_flag": "0.0",
        "revenue_company": 1_000.0,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(1.0, True), (0.0, False), ("1.0", True), ("0", False), (True, True), ("nan", False)],
)
def test_marks_coerced_to_bool(raw: object, expected: bool) -> None:
    profile = CompanyProfile.model_validate(_profile(cl_product_loa_mark=raw))
    assert profile.cl_product_loa_mark is expected


def test_nan_strings_become_none() -> None:
    profile = CompanyProfile.model_validate(_profile(amount_workers_spark_gradation="NaN"))
    assert profile.amount_workers_spark_gradation is None


def test_negative_revenue_rejected() -> None:
    with pytest.raises(ValidationError):
        CompanyProfile.model_validate(_profile(revenue_company=-1))


def test_derived_properties() -> None:
    profile = CompanyProfile.model_validate(_profile(revenue_company=16_461_800_000.0))
    assert profile.is_large_business
    assert profile.industry_prefix == "47"
    assert profile.revenue_human == "16,46 млрд ₽"


def test_news_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        NewsItem(
            id="n",
            title="t",
            summary_facts="s",
            source="src",
            published_at=datetime(2026, 1, 1),
            category="c",
        )
    item = NewsItem(
        id="n",
        title="t",
        summary_facts="s",
        source="src",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        category="c",
    )
    assert item.text_for_analysis == "t\ns"


def test_card_accepts_backend_mock_insight() -> None:
    card = Card.model_validate(BACKEND_MOCK_INSIGHT)
    assert card.alfa_report_page is None
    assert card.traceability.verified_sources == []


def test_question_length_limit(company_u1595: CompanyProfile, news_key_rate: NewsItem) -> None:
    card = Card.model_validate(BACKEND_MOCK_INSIGHT)
    with pytest.raises(ValidationError):
        AskRequest(
            news=news_key_rate, card=card, company=company_u1595, role="CFO", question="x" * 2001
        )
    request = AskRequest(
        news=news_key_rate, card=card, company=company_u1595, role="CFO", question="  вопрос  "
    )
    assert request.question == "вопрос"
