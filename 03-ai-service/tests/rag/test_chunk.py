from itertools import pairwise

from ai_service.rag.chunk import normalize_page_text, split_page

SENTENCE = "ЦБ РФ сохранил ключевую ставку на уровне 14,0% и ужесточил риторику. "


def test_split_respects_max_and_overlaps() -> None:
    text = SENTENCE * 40  # ~2900 символов
    chunks = split_page(text, max_chars=800, overlap=150)
    assert len(chunks) >= 4
    assert all(len(c) <= 800 for c in chunks)
    # перекрытие: конец предыдущего окна встречается в начале следующего
    for prev, nxt in pairwise(chunks):
        tail = prev[-60:]
        assert tail.split(". ")[-1][:30] in nxt


def test_split_keeps_sentence_boundaries() -> None:
    chunks = split_page(SENTENCE * 15, max_chars=300, overlap=50)
    assert all(c.rstrip().endswith(".") for c in chunks)


def test_empty_and_short_pages_give_no_chunks() -> None:
    assert split_page("") == []
    assert split_page("   \n\n  ") == []
    assert split_page("Коротко.") == []


def test_normalize_joins_hyphenated_ocr_breaks() -> None:
    raw = "Инфляцион-\nные ожидания   остаются\nповышенными.\n\nНовый абзац."
    normalized = normalize_page_text(raw)
    assert "Инфляционные ожидания остаются повышенными." in normalized
    assert "\n\nНовый абзац." in normalized


def test_very_long_unit_is_hard_split() -> None:
    long_table = "Таблица " + "12,3 | 45,6 | " * 200  # без точек, > max_chars
    chunks = split_page(long_table, max_chars=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)
