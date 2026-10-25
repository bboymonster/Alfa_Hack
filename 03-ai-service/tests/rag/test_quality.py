from ai_service.rag.quality import alpha_ratio, best_quote_span, clean_page_text, is_clean_text

CLEAN = (
    "ЦБ РФ принял решение оставить ставку неизменной на уровне 14,0%. Риторика регулятора "
    "стала жестче: вариант снижения ставки не рассматривался."
)
NOISE = "Омай.26 01К26 20% 24% ame С 19% 18% ar Gal 15% —— 12%|15%| 10% | - | 1 11% — 11%) |"


def test_alpha_ratio_distinguishes_noise() -> None:
    assert alpha_ratio(CLEAN) > 0.8
    assert alpha_ratio(NOISE) < 0.4
    assert is_clean_text(CLEAN)
    assert not is_clean_text(NOISE)
    assert not is_clean_text("")


def test_best_quote_is_substring_and_prefers_clean_part() -> None:
    text = NOISE + ". " + CLEAN + " Источники: Росстат, Альфа-Банк 12% 15% 20% 30%."
    quote = best_quote_span(text, max_chars=200)
    assert quote in text
    assert quote.startswith("ЦБ РФ принял решение")
    assert len(quote) <= 200


def test_clean_page_text_drops_captions_and_axes() -> None:
    page = (
        "Центр макроэкономического анализа\n11 сентября 2026 г.\n\n"
        "ЦБ РФ принял решение оставить ставку неизменной\nна уровне 14,0%. Риторика регулятора "
        "стала\nжестче: вариант снижения ставки не рассматривался.\n\n"
        "Рис. 5: Прирост кредитного портфеля по сегментам, % м/м\n"
        + NOISE
        + "\nИсточники: ЦБ РФ, Альфа-Банк\n\n"
        "Мы корректируем прогноз средней ключевой ставки на 2026 год до 14,5% годовых."
    )
    cleaned = clean_page_text(page)
    assert "ЦБ РФ принял решение оставить ставку неизменной\nна уровне 14,0%." in cleaned
    assert "прогноз средней ключевой ставки" in cleaned
    assert "Рис. 5" not in cleaned
    assert "Источники:" not in cleaned
    assert "20% 24%" not in cleaned
    assert clean_page_text(NOISE).strip() == ""


def test_best_quote_respects_max_chars_for_long_sentence() -> None:
    long_sentence = "слово " * 100 + "."
    quote = best_quote_span(long_sentence, max_chars=120)
    assert quote in long_sentence
    assert len(quote) <= 120
