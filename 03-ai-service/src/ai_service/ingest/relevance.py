"""Фильтр релевантности: экономика, бизнес, регулирование — да; спорт, культура,
происшествия — нет."""

from ai_service.agent.rules import TOPIC_KEYWORDS
from ai_service.schemas.common import NewsCategory
from ai_service.schemas.news import NewsItem

ECONOMIC_TERMS: tuple[str, ...] = tuple(
    sorted(
        {
            keyword
            for topic, keywords in TOPIC_KEYWORDS.items()
            if topic not in {NewsCategory.OTHER, NewsCategory.INDUSTRY_MARKETS}
            for keyword in keywords
        }
        | {
            "экономик",
            "бизнес",
            "компани",
            "банк",
            "минфин",
            "правительств",
            "бюджет",
            "выручк",
            "прибыл",
            "акци",
            "рубл",
            "доллар",
            "ввп",
            "инвестиц",
            "предприяти",
            "отрасл",
            "рынок",
            "рынк",
        }
    )
)

STOP_TOPICS: tuple[str, ...] = (
    "футбол",
    "хоккей",
    "матч",
    "чемпионат",
    "олимпи",
    "сборная",
    "тренер",
    "гол ",
    "турнир",
    "концерт",
    "фестивал",
    "кино",
    "фильм",
    "сериал",
    "актёр",
    "актер",
    "певиц",
    "певец",
    "театр",
    "выставк",
    "погод",
    "осадк",
    "гороскоп",
    "дтп",
    "пожар",
    "убийств",
    "задержан",
    "суд приговорил",
    "ранен",
    "погиб",
    "взрыв",
    "обстрел",
    "удар",
    "беспилотник",
    "дрон",
    "минобороны",
    "военн",
    "всу",
    "выборы",
    "экзитпол",
    "кандидат",
)


def relevance_signals(item: NewsItem) -> tuple[int, int]:
    text = item.text_for_analysis.lower()
    economic = sum(1 for term in ECONOMIC_TERMS if term in text)
    stop = sum(1 for term in STOP_TOPICS if term in text)
    return economic, stop


def is_relevant(item: NewsItem) -> bool:
    economic, stop = relevance_signals(item)
    if economic == 0:
        return False
    # Экономический контекст должен перевешивать «шумовые» темы.
    return economic >= 2 * stop if stop else True
