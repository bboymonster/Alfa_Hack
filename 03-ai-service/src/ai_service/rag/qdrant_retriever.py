"""Гибридный ретривер: dense + BM25 через prefetch и RRF; dense-score для гейта слабости."""

from datetime import datetime
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models

from ai_service.config import Settings
from ai_service.rag.catalog import ReportsCatalog
from ai_service.rag.embedders import DenseEmbedder, FastembedBm25, FastembedDense, SparseEmbedder
from ai_service.rag.extract import CachedExtractor, TesseractOcrBackend
from ai_service.rag.index import DENSE, SPARSE, ReportIndex
from ai_service.schemas.common import CorpusStatus
from ai_service.schemas.reports import ReportChunk, ReportDocument


def open_local_client(path: Path) -> QdrantClient:
    path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(path))


class QdrantHybridRetriever:
    def __init__(self, index: ReportIndex, dense: DenseEmbedder, sparse: SparseEmbedder) -> None:
        self.index = index
        self.dense = dense
        self.sparse = sparse

    @classmethod
    def from_settings(cls, settings: Settings) -> "QdrantHybridRetriever":
        dense = FastembedDense(settings.embed_dense_model, settings.index_dir / "models")
        sparse = FastembedBm25(settings.embed_sparse_language, settings.index_dir / "models")
        index = ReportIndex(
            open_local_client(settings.qdrant_path),
            dense,
            sparse,
            settings.manifest_path,
            chunk_max_chars=settings.chunk_max_chars,
            chunk_overlap=settings.chunk_overlap,
        )
        return cls(index, dense, sparse)

    @property
    def available(self) -> bool:
        return self.index.exists() and self.index.count() > 0

    def stats(self) -> CorpusStatus:
        reports = self.index.list_reports()
        indexed_at: datetime | None = max((r.indexed_at for r in reports), default=None)
        return CorpusStatus(
            available=self.available,
            reports=len(reports),
            chunks=self.index.count(),
            indexed_at=indexed_at,
        )

    def list_reports(self) -> list[ReportDocument]:
        return self.index.list_reports()

    def search(self, query: str, k: int) -> list[ReportChunk]:
        if not self.available:
            return []
        dense_vec = self.dense.embed_query(query)
        sparse_vec = self.sparse.embed_query(query)
        candidates = max(k * 3, 10)
        fused = self.index.client.query_points(
            self.index.collection,
            prefetch=[
                models.Prefetch(query=dense_vec, using=DENSE, limit=candidates),
                models.Prefetch(
                    query=models.SparseVector(indices=sparse_vec.indices, values=sparse_vec.values),
                    using=SPARSE,
                    limit=candidates,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=k,
            with_payload=True,
        )
        dense_only = self.index.client.query_points(
            self.index.collection,
            query=dense_vec,
            using=DENSE,
            limit=candidates,
            with_payload=["chunk_id"],
        )
        dense_scores: dict[str, float] = {}
        for point in dense_only.points:
            dense_payload = point.payload or {}
            dense_scores[str(dense_payload.get("chunk_id"))] = float(point.score)
        results: list[ReportChunk] = []
        for point in fused.points:
            payload: dict[str, Any] = dict(point.payload or {})
            chunk_id = str(payload["chunk_id"])
            results.append(
                ReportChunk(
                    chunk_id=chunk_id,
                    report_id=str(payload["report_id"]),
                    title=str(payload["title"]),
                    file=str(payload["file"]),
                    page=int(payload["page"]),
                    index=int(payload["index"]),
                    text=str(payload["text"]),
                    score=float(point.score),
                    dense_score=dense_scores.get(chunk_id),
                )
            )
        return results


def build_index_tools(
    settings: Settings,
) -> tuple[QdrantHybridRetriever, CachedExtractor, ReportsCatalog]:
    retriever = QdrantHybridRetriever.from_settings(settings)
    extractor = CachedExtractor(
        settings.ocr_cache_dir,
        ocr_backend=TesseractOcrBackend(lang=settings.ocr_lang, dpi=settings.ocr_dpi),
    )
    catalog = ReportsCatalog.load(settings.reports_catalog)
    return retriever, extractor, catalog
