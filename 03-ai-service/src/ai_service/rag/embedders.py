"""Протоколы эмбеддеров и реализации на fastembed (ONNX, без torch). Модели грузятся лениво."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class SparseVec:
    indices: list[int]
    values: list[float]


class DenseEmbedder(Protocol):
    @property
    def dim(self) -> int: ...

    @property
    def model_name(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SparseEmbedder(Protocol):
    @property
    def model_name(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> list[SparseVec]: ...

    def embed_query(self, text: str) -> SparseVec: ...


class FastembedDense:
    def __init__(self, model_name: str, cache_dir: Path | None = None) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model: Any = None
        self._dim: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _load(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(
                model_name=self._model_name,
                cache_dir=str(self._cache_dir) if self._cache_dir else None,
            )
            self._dim = int(TextEmbedding.get_embedding_size(self._model_name))
        return self._model

    @property
    def dim(self) -> int:
        self._load()
        assert self._dim is not None
        return self._dim

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        return [[float(x) for x in vec] for vec in model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        return [float(x) for x in next(iter(model.query_embed(text)))]


class FastembedBm25:
    def __init__(self, language: str = "russian", cache_dir: Path | None = None) -> None:
        self._language = language
        self._cache_dir = cache_dir
        self._model: Any = None

    @property
    def model_name(self) -> str:
        return f"Qdrant/bm25[{self._language}]"

    def _load(self) -> Any:
        if self._model is None:
            from fastembed import SparseTextEmbedding

            self._model = SparseTextEmbedding(
                model_name="Qdrant/bm25",
                language=self._language,
                cache_dir=str(self._cache_dir) if self._cache_dir else None,
            )
        return self._model

    @staticmethod
    def _convert(raw: Any) -> SparseVec:
        return SparseVec(
            indices=[int(i) for i in raw.indices], values=[float(v) for v in raw.values]
        )

    def embed(self, texts: Sequence[str]) -> list[SparseVec]:
        model = self._load()
        return [self._convert(vec) for vec in model.embed(list(texts))]

    def embed_query(self, text: str) -> SparseVec:
        model = self._load()
        return self._convert(next(iter(model.query_embed(text))))
