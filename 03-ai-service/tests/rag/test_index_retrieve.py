from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from ai_service.rag import extract as extract_module
from ai_service.rag.catalog import ReportsCatalog, guess_title
from ai_service.rag.extract import CachedExtractor
from ai_service.rag.index import ReportIndex
from ai_service.rag.qdrant_retriever import QdrantHybridRetriever
from tests.rag.fakes import FakeDenseEmbedder, FakeOcrBackend, FakeSparseEmbedder, FakeTextBackend

RATE_PAGE_1 = (
    "Центр макроэкономического анализа\n11 сентября 2026 г.\nКлючевая ставка ЦБ РФ\n"
    "Ставка без изменения на 14,0%, риторика стала жестче. ЦБ РФ принял решение оставить "
    "ключевую ставку неизменной на уровне 14,0%. Регулятор обсуждал только вариант паузы. "
)
RATE_PAGE_2 = (
    "Мы корректируем прогноз средней ключевой ставки на 2026 год до 14,5% годовых. "
    "Ожидаем длительного удержания жестких денежно-кредитных условий и роста доходности ОФЗ. "
)
INFL_PAGE_1 = (
    "Инфляция 25-31 августа: основные выводы. За прошедшую неделю Росстат зафиксировал "
    "дефляцию на 0,01% н/н. Цены на плодоовощную продукцию снизились, инфляция замедляется. "
)
INFL_PAGE_2 = (
    "Недельная инфляция остаётся низкой, годовая инфляция замедлилась до 8,85%. "
    "Дезинфляционный тренд в продовольствии не транслируется в базовую инфляцию. "
)


@pytest.fixture
def corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ReportIndex, QdrantHybridRetriever, CachedExtractor, ReportsCatalog, Path]:
    monkeypatch.setattr(extract_module, "page_count", lambda path: 2)
    articles = tmp_path / "articles"
    articles.mkdir()
    (articles / "rate.pdf").write_bytes(b"rate-v1")
    (articles / "inflation.pdf").write_bytes(b"inflation-v1")
    (articles / "broken.pdf").write_bytes(b"broken")
    text_backend = FakeTextBackend(
        {
            "rate.pdf": {1: RATE_PAGE_1 * 2, 2: RATE_PAGE_2 * 2},
            "inflation.pdf": {1: INFL_PAGE_1 * 2, 2: INFL_PAGE_2 * 2},
        }
    )
    extractor = CachedExtractor(tmp_path / "ocr", text_backend, FakeOcrBackend({}))
    catalog = ReportsCatalog(entries={})
    dense, sparse = FakeDenseEmbedder(), FakeSparseEmbedder()
    index = ReportIndex(
        QdrantClient(path=str(tmp_path / "qdrant")),
        dense,
        sparse,
        tmp_path / "manifest.json",
        chunk_max_chars=300,
        chunk_overlap=60,
    )
    retriever = QdrantHybridRetriever(index, dense, sparse)
    return index, retriever, extractor, catalog, articles


def test_index_directory_and_stats(corpus: tuple) -> None:  # type: ignore[type-arg]
    index, retriever, extractor, catalog, articles = corpus
    assert not retriever.available
    report = index.index_directory(articles, extractor, catalog, force=False)
    ok = {f.file for f in report.files if f.ok}
    assert ok == {"rate.pdf", "inflation.pdf"}
    broken = next(f for f in report.files if f.file == "broken.pdf")
    assert not broken.ok and broken.error
    assert report.reports == 2
    assert report.chunks == index.count() > 2
    stats = retriever.stats()
    assert stats.available and stats.reports == 2 and stats.chunks == report.chunks
    titles = {r.title for r in retriever.list_reports()}
    assert "Ключевая ставка ЦБ РФ" in titles  # заголовок угадан из первой страницы


def test_search_returns_relevant_chunk_with_page(corpus: tuple) -> None:  # type: ignore[type-arg]
    index, retriever, extractor, catalog, articles = corpus
    index.index_directory(articles, extractor, catalog, force=False)
    results = retriever.search("ключевая ставка 14,0% риторика", k=3)
    assert results
    assert results[0].file == "rate.pdf"
    assert results[0].page in (1, 2)
    assert results[0].dense_score is not None
    assert results[0].score is not None
    assert "ставк" in results[0].text.lower()

    results = retriever.search("недельная инфляция плодоовощная продукция", k=3)
    assert results[0].file == "inflation.pdf"


def test_reindex_replaces_points_without_duplicates(corpus: tuple) -> None:  # type: ignore[type-arg]
    index, retriever, extractor, catalog, articles = corpus
    first = index.index_directory(articles, extractor, catalog, force=False)
    second = index.index_directory(articles, extractor, catalog, force=True)
    assert second.chunks == first.chunks == index.count()
    # файл изменился → новый report_id, старые точки удалены
    (articles / "rate.pdf").write_bytes(b"rate-v2")
    third = index.index_directory(articles, extractor, catalog, force=True)
    assert third.chunks == first.chunks == index.count()
    assert len(retriever.list_reports()) == 2


def test_catalog_title_and_fallback(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_text(
        "reports:\n  a.pdf:\n    title: Официальное название\n    topics: [inflation]\n",
        encoding="utf-8",
    )
    catalog = ReportsCatalog.load(path)
    assert catalog.title_for("a.pdf", "мусор") == "Официальное название"
    assert catalog.title_for("b.pdf", RATE_PAGE_1) == "Ключевая ставка ЦБ РФ"
    assert catalog.title_for("c.pdf", "") == "c"
    assert (
        guess_title("Центр макроэкономического анализа\n5 августа 2026 г.\nПотребление на пике")
        == "Потребление на пике"
    )
    assert ReportsCatalog.load(tmp_path / "missing.yaml").entries == {}
