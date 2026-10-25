from datetime import UTC, datetime

from ai_service.ingest.dedupe import dedupe, jaccard, normalize_title, normalize_url, title_tokens
from ai_service.ingest.normalize import RawEntry, strip_html, to_news_item
from ai_service.ingest.relevance import is_relevant
from ai_service.ingest.sources import DEFAULT_SOURCES
from ai_service.schemas.news import NewsItem

SRC = DEFAULT_SOURCES[2]  # РБК


def _item(title: str, url: str, summary: str = "Текст новости.") -> NewsItem:
    item = to_news_item(
        RawEntry(
            title=title, link=url, summary=summary, published=datetime(2026, 10, 1, tzinfo=UTC)
        ),
        SRC,
    )
    assert item is not None
    return item


def test_strip_html_and_entities() -> None:
    raw = "<p>Ставка&nbsp;<b>14,0%</b>&nbsp;сохранена.</p> Оставайтесь на связи с РБК в «Максе»."
    assert strip_html(raw) == "Ставка 14,0% сохранена."


def test_to_news_item_truncates_and_defaults() -> None:
    long_summary = "слово " * 2000
    item = _item("Заголовок новости", "https://example.com/a", long_summary)
    assert len(item.summary_facts) <= 4000
    assert item.published_at.tzinfo is not None
    assert to_news_item(RawEntry(title="", link="", summary="x", published=None), SRC) is None
    without_summary = to_news_item(
        RawEntry(title="Только заголовок", link="https://e.com/b", summary="", published=None),
        SRC,
    )
    assert without_summary is not None and without_summary.summary_facts == "Только заголовок"


def test_normalize_url_and_title() -> None:
    assert (
        normalize_url("HTTPS://www.RBC.ru/news/1/?utm_source=x&id=2#frag")
        == "https://www.rbc.ru/news/1?id=2"
    )
    assert normalize_title("ЦБ сохранил ставку: 14%!") == "цб сохранил ставку 14"
    assert (
        jaccard(
            title_tokens("ЦБ сохранил ключевую ставку"), title_tokens("ключевую ставку ЦБ сохранил")
        )
        == 1.0
    )


def test_dedupe_by_url_title_and_similarity() -> None:
    items = [
        _item("ЦБ сохранил ключевую ставку на уровне 14%", "https://a.ru/1"),
        _item("ЦБ сохранил ключевую ставку на уровне 14%!", "https://a.ru/1?utm_source=tg"),
        _item("ЦБ сохранил ключевую ставку на уровне 14 процентов", "https://b.ru/2"),
        _item("Банк России сохранил ключевую ставку на уровне 14% годовых", "https://c.ru/3"),
        _item("Инфляция замедлилась до 8,85%", "https://d.ru/4"),
    ]
    kept, dropped = dedupe(items)
    assert dropped == 2  # дубликат URL и дубликат с Jaccard ≥ 0.8
    assert [k.source_url for k in kept][-1] == "https://d.ru/4"
    assert len(kept) == 3


def test_relevance_filter() -> None:
    assert is_relevant(_item("Банк России сохранил ключевую ставку", "https://x/1", "Инфляция."))
    assert is_relevant(_item("Минфин предложил повысить НДС", "https://x/2", "Налоговая реформа."))
    assert not is_relevant(_item("Сборная выиграла матч чемпионата", "https://x/3", "Гол на 90-й."))
    assert not is_relevant(
        _item("В Казани открылся кинофестиваль", "https://x/4", "Фильмы и концерты.")
    )
    assert not is_relevant(
        _item("Минобороны отчиталось об ударе беспилотников", "https://x/5", "Удар по складу.")
    )
