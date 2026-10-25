"""Качество OCR-фрагментов: отсев «шума» графиков и выбор чистой цитаты-подстроки."""

import re

_LETTERS = re.compile(r"[А-Яа-яЁёA-Za-z]")
_NON_SPACE = re.compile(r"\S")
_WORD = re.compile(r"[А-Яа-яЁёA-Za-z]{3,}")
_SENTENCE = re.compile(r"[^.!?…]+[.!?…]?")

MIN_ALPHA_RATIO = 0.6
MIN_WORD_SHARE = 0.5


def alpha_ratio(text: str) -> float:
    non_space = len(_NON_SPACE.findall(text))
    return len(_LETTERS.findall(text)) / non_space if non_space else 0.0


def word_share(text: str) -> float:
    tokens = text.split()
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if _WORD.search(t)) / len(tokens)


def short_token_share(text: str) -> float:
    tokens = text.split()
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if len(t.strip(".,;:|—-–()[]«»")) <= 2) / len(tokens)


def is_clean_text(text: str) -> bool:
    """Фрагмент пригоден для цитирования: преимущественно слова, а не оси и легенды графиков."""
    return alpha_ratio(text) >= MIN_ALPHA_RATIO and word_share(text) >= MIN_WORD_SHARE


# Пороги для отдельного предложения строже: подписи к рисункам и оси графиков короткие,
# состоят из чисел, процентов и обрывков слов.
SENTENCE_MIN_WORD_SHARE = 0.55
SENTENCE_MAX_SHORT_SHARE = 0.4
SENTENCE_MIN_CHARS = 20
_FIGURE_CAPTION = re.compile(r"^(рис\.?|puc\.?|источник[и]?:|табл\.?)\s*\d*", re.IGNORECASE)


def is_clean_sentence(sentence: str) -> bool:
    stripped = sentence.strip()
    if len(stripped) < SENTENCE_MIN_CHARS or _FIGURE_CAPTION.match(stripped):
        return False
    return (
        alpha_ratio(stripped) >= MIN_ALPHA_RATIO
        and word_share(stripped) >= SENTENCE_MIN_WORD_SHARE
        and short_token_share(stripped) <= SENTENCE_MAX_SHORT_SHARE
    )


def is_clean_line(line: str) -> bool:
    """Строка OCR — часть текста, а не ось графика, легенда или подпись к рисунку."""
    stripped = line.strip()
    if not stripped or _FIGURE_CAPTION.match(stripped):
        return False
    if len(stripped) < 4:
        return False
    return (
        alpha_ratio(stripped) >= MIN_ALPHA_RATIO
        and word_share(stripped) >= SENTENCE_MIN_WORD_SHARE
        and short_token_share(stripped) <= SENTENCE_MAX_SHORT_SHARE
    )


def clean_page_text(text: str) -> str:
    """Удаляет «шумные» строки OCR (оси графиков, легенды, подписи), сохраняя абзацы.

    Работает по физическим строкам до склейки абзацев: шум графиков в OCR лежит отдельными
    строками, а предложения текста переносятся между строками.
    """
    kept_lines = [
        line
        for line in text.replace("\r", "").split("\n")
        if is_clean_line(line) or not line.strip()
    ]
    return "\n".join(kept_lines)


def best_quote_span(text: str, max_chars: int = 320, min_chars: int = 60) -> str:
    """Самая чистая непрерывная последовательность предложений (дословная подстрока text)."""
    spans = [(m.start(), m.end()) for m in _SENTENCE.finditer(text) if m.group().strip()]
    if not spans:
        return text[:max_chars].rstrip()

    def quality(start: int, end: int) -> float:
        piece = text[start:end]
        return alpha_ratio(piece) * 0.6 + word_share(piece) * 0.4

    # Кандидаты — непрерывные окна чистых предложений; «грязное» предложение окно обрывает,
    # чтобы в цитату не попадали оси графиков и легенды.
    best_start, best_end, best_q = spans[0][0], min(spans[0][1], spans[0][0] + max_chars), -1.0
    for i, (start, _) in enumerate(spans):
        end = start
        for span_start, span_end in spans[i:]:
            if span_end - start > max_chars:
                break
            if not is_clean_sentence(text[span_start:span_end]):
                break
            end = span_end
        if end == start:
            continue
        # Окна состоят только из чистых предложений, поэтому главное — покрытие (длина),
        # чистота текста — дополнительный критерий.
        length = end - start
        q = min(length / max_chars, 1.0) + 0.2 * quality(start, end)
        if length < min_chars:
            q -= 0.5
        if q > best_q:
            best_start, best_end, best_q = start, end, q
    quote = text[best_start:best_end].strip()
    return quote if quote else text[:max_chars].rstrip()
