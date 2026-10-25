from datetime import UTC, datetime

from ai_service.agent.rules import classify_topic_offline, match_triggers
from ai_service.schemas.common import Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.news import NewsItem
from ai_service.schemas.score import ImportanceScore
from ai_service.scoring.scorer import score_news

NOW = datetime(2026, 9, 12, tzinfo=UTC)


def _score(company: CompanyProfile, role: Role, news: NewsItem) -> ImportanceScore:
    topic = classify_topic_offline(news.text_for_analysis)
    return score_news(company, role, news, topic, match_triggers(company, topic), now=NOW)


def test_labor_news_matters_more_to_accountant(
    company_u1595: CompanyProfile, news_labor: NewsItem
) -> None:
    accountant = _score(company_u1595, Role.ACCOUNTANT, news_labor)
    ceo = _score(company_u1595, Role.CEO, news_labor)
    assert accountant.score > ceo.score
    assert any(f.name == "role_focus" and f.delta == 2 for f in accountant.factors)


def test_steel_news_matters_more_to_metal_company(
    company_u80: CompanyProfile, company_u1595: CompanyProfile, news_steel: NewsItem
) -> None:
    metal = _score(company_u80, Role.CEO, news_steel)
    retail = _score(company_u1595, Role.CEO, news_steel)
    assert metal.score > retail.score
    assert any(f.name == "industry_match" for f in metal.factors)
    assert not any(f.name == "industry_match" for f in retail.factors)


def test_stale_news_penalised(company_u1595: CompanyProfile, news_key_rate: NewsItem) -> None:
    fresh = _score(company_u1595, Role.CFO, news_key_rate)
    old_news = news_key_rate.model_copy(update={"published_at": datetime(2026, 1, 1, tzinfo=UTC)})
    old = _score(company_u1595, Role.CFO, old_news)
    assert old.score == fresh.score - 1
    assert any(f.name == "freshness" for f in old.factors)


def test_score_clipped_and_deterministic(
    company_u1595: CompanyProfile, news_key_rate: NewsItem
) -> None:
    first = _score(company_u1595, Role.CFO, news_key_rate)
    second = _score(company_u1595, Role.CFO, news_key_rate)
    assert first == second
    assert 1 <= first.score <= 10
    assert first.score >= 9  # ставка + кредиты + депозиты + фокус CFO + масштаб события
