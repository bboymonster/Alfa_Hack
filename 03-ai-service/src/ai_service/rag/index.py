"""Индекс корпуса отчётов в embedded Qdrant: именованные векторы dense + sparse (BM25)."""

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models

from ai_service.logging import get_logger
from ai_service.rag.catalog import ReportsCatalog
from ai_service.rag.chunk import normalize_page_text, split_page
from ai_service.rag.embedders import DenseEmbedder, SparseEmbedder
from ai_service.rag.extract import CachedExtractor, ExtractError
from ai_service.rag.quality import clean_page_text, is_clean_text
from ai_service.schemas.reports import IndexedFile, IndexReport, ReportDocument

log = get_logger(__name__)

COLLECTION = "alfa_reports"
DENSE = "dense"
SPARSE = "sparse"


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"alfa-reports/{chunk_id}"))


class ReportIndex:
    def __init__(
        self,
        client: QdrantClient,
        dense: DenseEmbedder,
        sparse: SparseEmbedder,
        manifest_path: Path,
        collection: str = COLLECTION,
        chunk_max_chars: int = 800,
        chunk_overlap: int = 150,
    ) -> None:
        self.client = client
        self.dense = dense
        self.sparse = sparse
        self.manifest_path = manifest_path
        self.collection = collection
        self.chunk_max_chars = chunk_max_chars
        self.chunk_overlap = chunk_overlap

    # ------------------------------------------------------------------ collection
    def ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                DENSE: models.VectorParams(size=self.dense.dim, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )

    def exists(self) -> bool:
        return bool(self.client.collection_exists(self.collection))

    def count(self) -> int:
        if not self.exists():
            return 0
        return int(self.client.count(self.collection, exact=True).count)

    # ------------------------------------------------------------------ manifest
    def _read_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {"reports": {}}
        try:
            data: dict[str, Any] = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            data.setdefault("reports", {})
            return data
        except json.JSONDecodeError:
            return {"reports": {}}

    def _write_manifest(self, data: dict[str, Any]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data["updated_at"] = datetime.now(UTC).isoformat()
        self.manifest_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def list_reports(self) -> list[ReportDocument]:
        reports = self._read_manifest()["reports"]
        docs = [ReportDocument.model_validate(item) for item in reports.values()]
        return sorted(docs, key=lambda d: d.title)

    # ------------------------------------------------------------------ indexing
    def delete_report(self, report_id: str) -> None:
        if not self.exists():
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="report_id", match=models.MatchValue(value=report_id)
                        )
                    ]
                )
            ),
        )

    def index_report(
        self, pdf_path: Path, extractor: CachedExtractor, catalog: ReportsCatalog, *, force: bool
    ) -> ReportDocument:
        extracted = extractor.extract(pdf_path, force=force)
        report_id = extracted.sha256[:16]
        first_page = next((p.text for p in extracted.pages if p.text), "")
        title = catalog.title_for(pdf_path.name, first_page)
        topics = list(catalog.topics_for(pdf_path.name))

        texts: list[str] = []
        payloads: list[dict[str, Any]] = []
        skipped_noise = 0
        for page in extracted.pages:
            cleaned = normalize_page_text(clean_page_text(page.text))
            for index, text in enumerate(
                split_page(cleaned, self.chunk_max_chars, self.chunk_overlap)
            ):
                if not is_clean_text(text):
                    skipped_noise += 1
                    continue
                chunk_id = f"{report_id}:{page.page}:{index}"
                texts.append(text)
                payloads.append(
                    {
                        "chunk_id": chunk_id,
                        "report_id": report_id,
                        "title": title,
                        "file": pdf_path.name,
                        "page": page.page,
                        "index": index,
                        "text": text,
                        "topics": topics,
                        "source": page.source,
                    }
                )
        if not texts:
            raise ExtractError(f"{pdf_path.name}: после разбиения не осталось фрагментов")

        self.ensure_collection()
        # Переиндексация заменяет старые точки: удаляем по report_id и по имени файла.
        self.delete_report(report_id)
        manifest = self._read_manifest()
        previous = manifest["reports"].get(pdf_path.name)
        if previous and previous.get("report_id") != report_id:
            self.delete_report(str(previous["report_id"]))

        # Контекстуальные эмбеддинги: название отчёта добавляется к тексту фрагмента, чтобы
        # тема документа учитывалась и dense-, и BM25-поиском; в payload хранится чистый текст.
        embed_texts = [f"{title}. {text}" for text in texts]
        dense_vectors = self.dense.embed(embed_texts)
        sparse_vectors = self.sparse.embed(embed_texts)
        points = [
            models.PointStruct(
                id=point_id(str(payload["chunk_id"])),
                vector={
                    DENSE: dense_vec,
                    SPARSE: models.SparseVector(indices=sparse.indices, values=sparse.values),
                },
                payload=payload,
            )
            for payload, dense_vec, sparse in zip(
                payloads, dense_vectors, sparse_vectors, strict=True
            )
        ]
        for start in range(0, len(points), 64):
            self.client.upsert(self.collection, points=points[start : start + 64])

        doc = ReportDocument(
            report_id=report_id,
            title=title,
            file=pdf_path.name,
            pages=extracted.page_count,
            chunks=len(points),
            indexed_at=datetime.now(UTC),
            extractor=extracted.extractor,
        )
        manifest["reports"][pdf_path.name] = doc.model_dump(mode="json")
        manifest["dense_model"] = self.dense.model_name
        manifest["sparse_model"] = self.sparse.model_name
        self._write_manifest(manifest)
        log.info(
            "index.report",
            file=pdf_path.name,
            pages=doc.pages,
            chunks=doc.chunks,
            skipped_noise=skipped_noise,
        )
        return doc

    def index_directory(
        self, directory: Path, extractor: CachedExtractor, catalog: ReportsCatalog, *, force: bool
    ) -> IndexReport:
        files: list[IndexedFile] = []
        for pdf_path in sorted(directory.glob("*.pdf")):
            started = time.perf_counter()
            try:
                doc = self.index_report(pdf_path, extractor, catalog, force=force)
                files.append(
                    IndexedFile(
                        file=pdf_path.name,
                        ok=True,
                        report=doc,
                        seconds=round(time.perf_counter() - started, 1),
                    )
                )
            except ExtractError as exc:
                log.warning("index.skip", file=pdf_path.name, error=str(exc))
                files.append(
                    IndexedFile(
                        file=pdf_path.name,
                        ok=False,
                        error=str(exc),
                        seconds=round(time.perf_counter() - started, 1),
                    )
                )
            except Exception as exc:
                log.warning("index.skip", file=pdf_path.name, error=type(exc).__name__)
                files.append(
                    IndexedFile(
                        file=pdf_path.name,
                        ok=False,
                        error=f"{type(exc).__name__}: {exc}",
                        seconds=round(time.perf_counter() - started, 1),
                    )
                )
        reports = self.list_reports()
        return IndexReport(files=files, reports=len(reports), chunks=sum(r.chunks for r in reports))
