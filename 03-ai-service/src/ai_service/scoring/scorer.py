"""Детерминированный rule-based скорер важности (1–10) с объяснимыми факторами."""

from datetime import UTC, datetime

from ai_service.agent.rules import (
    ROLE_FOCUS,
    has_magnitude,
    industry_match,
    positive_product_triggers,
)
from ai_service.schemas.common import MatchedFeature, NewsCategory, Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.news import NewsItem
from ai_service.schemas.score import ImportanceScore, ScoreFactor

BASE_SCORE = 5
STALE_AFTER_DAYS = 30
MAX_TRIGGER_BONUS = 3


def score_news(
    company: CompanyProfile,
    role: Role,
    news: NewsItem,
    topic: NewsCategory,
    triggers: list[MatchedFeature],
    now: datetime | None = None,
) -> ImportanceScore:
    now = now or datetime.now(UTC)
    factors: list[ScoreFactor] = [
        ScoreFactor(name="base", delta=0, explanation=f"базовая оценка {BASE_SCORE}")
    ]
    score = BASE_SCORE
    text = news.text_for_analysis

    if industry_match(company, text):
        score += 2
        factors.append(
            ScoreFactor(
                name="industry_match",
                delta=2,
                explanation=f"новость касается отрасли компании ({company.mainokved_name})",
            )
        )

    products = positive_product_triggers(triggers)
    if products:
        bonus = min(len(products), MAX_TRIGGER_BONUS)
        score += bonus
        names = ", ".join(trigger.feature for trigger in products[:MAX_TRIGGER_BONUS])
        factors.append(
            ScoreFactor(
                name="company_triggers",
                delta=bonus,
                explanation=f"сработали признаки компании: {names}",
            )
        )

    focus = ROLE_FOCUS[role]
    if topic in focus.primary_topics:
        score += 2
        factors.append(
            ScoreFactor(
                name="role_focus",
                delta=2,
                explanation=f"тема в основном фокусе роли {role.value}: {focus.description}",
            )
        )
    elif topic in focus.secondary_topics:
        score += 1
        factors.append(
            ScoreFactor(
                name="role_focus",
                delta=1,
                explanation=f"тема во вторичном фокусе роли {role.value}",
            )
        )

    age_days = (now - news.published_at).days
    if age_days > STALE_AFTER_DAYS:
        score -= 1
        factors.append(
            ScoreFactor(
                name="freshness",
                delta=-1,
                explanation=f"новости {age_days} дней, актуальность снижена",
            )
        )

    if has_magnitude(text):
        score += 1
        factors.append(
            ScoreFactor(
                name="magnitude",
                delta=1,
                explanation="событие системного масштаба (регулятор, закон, санкции)",
            )
        )

    return ImportanceScore(news_id=news.id, score=max(1, min(10, score)), factors=factors)
