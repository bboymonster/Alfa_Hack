"""Фейки для RAG-тестов: детерминированные эмбеддеры и экстрактор без PDF/сети."""

import hashlib
import math
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from ai_service.rag.embedders import SparseVec
from ai_service.rag.extract import ExtractError

_TOKEN = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [t.lower()[:6] for t in _TOKEN.findall(text) if len(t) > 2]


class FakeDenseEmbedder:
    """Хэш-мешок слов: одинаковые слова → близкие векторы. dim=64, нормирован."""

    def __init__(self, dim: int = 64) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "fake-dense"

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for token in _tokens(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            vec[digest[0] % self._dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class FakeSparseEmbedder:
    @property
    def model_name(self) -> str:
        return "fake-sparse"

    def _vector(self, text: str) -> SparseVec:
        counts = Counter(_tokens(text))
        indices = [int(hashlib.md5(t.encode()).hexdigest()[:8], 16) % 100_000 for t in counts]
        return SparseVec(indices=indices, values=[float(v) for v in counts.values()])

    def embed(self, texts: Sequence[str]) -> list[SparseVec]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> SparseVec:
        return self._vector(text)


class FakeTextBackend:
    """Текстовый слой: содержимое задаётся словарём файл → {страница: текст}."""

    name = "text"

    def __init__(self, pages_by_file: dict[str, dict[int, str]]) -> None:
        self.pages_by_file = pages_by_file
        self.calls: list[str] = []

    def available(self) -> bool:
        return True

    def extract(self, pdf_path: Path, pages: list[int] | None) -> dict[int, str]:
        self.calls.append(pdf_path.name)
        if pdf_path.name not in self.pages_by_file:
            raise ExtractError(f"битый файл {pdf_path.name}")
        data = self.pages_by_file[pdf_path.name]
        return {n: data.get(n, "") for n in (pages or sorted(data))}


class FakeOcrBackend:
    name = "ocr"

    def __init__(self, pages_by_file: dict[str, dict[int, str]], available: bool = True) -> None:
        self.pages_by_file = pages_by_file
        self._available = available
        self.calls: list[tuple[str, list[int] | None]] = []

    def available(self) -> bool:
        return self._available

    def extract(self, pdf_path: Path, pages: list[int] | None) -> dict[int, str]:
        self.calls.append((pdf_path.name, pages))
        data = self.pages_by_file.get(pdf_path.name, {})
        return {n: data.get(n, "") for n in (pages or sorted(data))}
