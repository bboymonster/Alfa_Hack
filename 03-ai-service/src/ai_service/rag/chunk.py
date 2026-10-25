"""Разбиение текста страницы на фрагменты по границам предложений с перекрытием."""

import re

_WS = re.compile(r"[ \t ]+")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[А-ЯA-Z«\d])")


def normalize_page_text(text: str) -> str:
    """Склеивает переносы слов OCR, убирает лишние пробелы, сохраняет абзацы."""
    text = text.replace("\r", "")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        joined = " ".join(line.strip() for line in block.splitlines() if line.strip())
        joined = _WS.sub(" ", joined).strip()
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def _sentences(text: str) -> list[str]:
    units: list[str] = []
    for paragraph in text.split("\n\n"):
        units.extend(s.strip() for s in _SENTENCE_END.split(paragraph) if s.strip())
    return units


def split_page(text: str, max_chars: int = 800, overlap: int = 150) -> list[str]:
    """Окна ≤ max_chars из целых предложений; хвост предыдущего окна (~overlap) повторяется."""
    normalized = normalize_page_text(text)
    if not normalized:
        return []
    sentences = _sentences(normalized)
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for sentence in sentences:
        if len(sentence) > max_chars:
            # Очень длинное «предложение» (таблица/список) режем жёстко.
            if current:
                chunks.append(" ".join(current))
                current, length = [], 0
            for start in range(0, len(sentence), max_chars - overlap):
                chunks.append(sentence[start : start + max_chars])
            continue
        if length + len(sentence) + 1 > max_chars and current:
            chunks.append(" ".join(current))
            tail: list[str] = []
            tail_len = 0
            for prev in reversed(current):
                if tail_len + len(prev) > overlap:
                    break
                tail.insert(0, prev)
                tail_len += len(prev) + 1
            current, length = tail, tail_len
        current.append(sentence)
        length += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if len(c.strip()) >= 20]
