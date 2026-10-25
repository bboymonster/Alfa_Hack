import pytest

from ai_service.agent.rules import (
    classify_topic_offline,
    industry_match,
    match_triggers,
    positive_product_triggers,
)
from ai_service.schemas.common import NewsCategory
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.news import NewsItem


def _features(company: CompanyProfile, topic: NewsCategory) -> dict[str, str]:
    return {t.feature: t.value for t in match_triggers(company, topic)}


def test_key_rate_with_credit_triggers_loa(company_u1595: CompanyProfile) -> None:
    features = _features(company_u1595, NewsCategory.MONETARY_POLICY)
    assert features["CL_PRODUCT_LOA_MARK"] == "1"
    assert features["CL_PRODUCT_DEP_MARK"] == "1"
    assert features["MAINOKVED_CODE"] == "47.71"
    assert "FACTORING_MARK" not in features  # значение 0 → не триггер


def test_key_rate_without_credit_reports_zero(company_demo_local: CompanyProfile) -> None:
    triggers = match_triggers(company_demo_local, NewsCategory.MONETARY_POLICY)
    features = {t.feature: t for t in triggers}
    assert features["CL_PRODUCT_LOA_MARK"].value == "0"
    assert "нет кредитных продуктов" in features["CL_PRODUCT_LOA_MARK"].why
    assert "CL_PRODUCT_DEP_MARK" not in features
    assert positive_product_triggers(triggers) == []


def test_logistics_without_trade_flag(company_demo_local: CompanyProfile) -> None:
    features = {
        t.feature: t for t in match_triggers(company_demo_local, NewsCategory.LOGISTICS_TRADE)
    }
    assert features["FTS_FLAG"].value == "0"
    assert "нет внешнеторговой деятельности" in features["FTS_FLAG"].why


def test_logistics_with_trade_flag_mentions_countries(company_u1595: CompanyProfile) -> None:
    features = {t.feature: t for t in match_triggers(company_u1595, NewsCategory.LOGISTICS_TRADE)}
    assert features["FTS_FLAG"].value == "1"
    assert "Китай" in features["FTS_FLAG"].why
    assert features["CL_PRODUCT_GAR_MARK"].value == "1"


def test_labor_market_triggers(company_u1595: CompanyProfile) -> None:
    features = _features(company_u1595, NewsCategory.LABOR_MARKET)
    assert features["CL_PRODUCT_ZPP_MARK"] == "1"
    assert features["AMOUNT_WORKERS_FNS_GRADATION"] == "более 1000"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Банк России сохранил ключевую ставку на уровне 14%", NewsCategory.MONETARY_POLICY),
        (
            "Недельная инфляция замедлилась до 0,05%, рост цен стабилизировался",
            NewsCategory.INFLATION,
        ),
        ("Безработица на минимуме, дефицит кадров давит на зарплаты", NewsCategory.LABOR_MARKET),
        ("Госдума приняла законопроект о налоге на сверхприбыль", NewsCategory.REGULATION_TAX),
        (
            "Сроки импортных поставок выросли, таможня замедлила оформление",
            NewsCategory.LOGISTICS_TRADE,
        ),
        ("Цены на горячекатаный прокат и сталь стабилизировались", NewsCategory.COMMODITIES),
        (
            "Розничный товарооборот вырос на 5,8%, потребительский спрос на пике",
            NewsCategory.CONSUMER_DEMAND,
        ),
        ("Футбольный клуб выиграл чемпионат", NewsCategory.OTHER),
    ],
)
def test_classify_topic_offline(text: str, expected: NewsCategory) -> None:
    assert classify_topic_offline(text) == expected


def test_industry_match(
    company_u80: CompanyProfile, company_u1595: CompanyProfile, news_steel: NewsItem
) -> None:
    assert industry_match(company_u80, news_steel.text_for_analysis)
    assert not industry_match(company_u1595, news_steel.text_for_analysis)
