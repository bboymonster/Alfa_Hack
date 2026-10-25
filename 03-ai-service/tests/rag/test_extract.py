from pathlib import Path

import pytest

from ai_service.rag import extract as extract_module
from ai_service.rag.extract import CachedExtractor, ExtractError
from tests.rag.fakes import FakeOcrBackend, FakeTextBackend

LONG = "Это содержательный текст страницы, которого достаточно для текстового слоя. " * 2


@pytest.fixture
def pdf_dir(tmp_path: Path) -> Path:
    for name in ("text.pdf", "scan.pdf", "mixed.pdf", "broken.pdf", "blank.pdf"):
        (tmp_path / name).write_bytes(b"%PDF-1.4 fake " + name.encode())
    return tmp_path


@pytest.fixture(autouse=True)
def _patch_page_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(extract_module, "page_count", lambda path: 2)


def _extractor(
    tmp_path: Path,
    text_pages: dict[str, dict[int, str]],
    ocr_pages: dict[str, dict[int, str]],
    ocr_available: bool = True,
) -> tuple[CachedExtractor, FakeTextBackend, FakeOcrBackend]:
    text = FakeTextBackend(text_pages)
    ocr = FakeOcrBackend(ocr_pages, available=ocr_available)
    return CachedExtractor(tmp_path / "cache", text_backend=text, ocr_backend=ocr), text, ocr


def test_text_layer_used_without_ocr(pdf_dir: Path) -> None:
    extractor, _, ocr = _extractor(pdf_dir, {"text.pdf": {1: LONG, 2: LONG}}, {})
    result = extractor.extract(pdf_dir / "text.pdf")
    assert result.extractor == "text"
    assert [p.source for p in result.pages] == ["text", "text"]
    assert ocr.calls == []


def test_ocr_only_for_empty_pages_and_cached(pdf_dir: Path) -> None:
    extractor, text, ocr = _extractor(
        pdf_dir,
        {"mixed.pdf": {1: LONG, 2: ""}},
        {"mixed.pdf": {2: "OCR " + LONG}},
    )
    result = extractor.extract(pdf_dir / "mixed.pdf")
    assert result.extractor == "mixed"
    assert ocr.calls == [("mixed.pdf", [2])]
    assert result.pages[1].source == "ocr"

    again = extractor.extract(pdf_dir / "mixed.pdf")
    assert again == result
    assert text.calls == ["mixed.pdf"]  # второй раз — из кэша
    assert len(list((pdf_dir / "cache").glob("*.json"))) == 1

    forced = extractor.extract(pdf_dir / "mixed.pdf", force=True)
    assert forced.pages == result.pages
    assert text.calls == ["mixed.pdf", "mixed.pdf"]


def test_full_scan_is_ocr(pdf_dir: Path) -> None:
    extractor, _, _ = _extractor(pdf_dir, {"scan.pdf": {}}, {"scan.pdf": {1: LONG, 2: LONG}})
    result = extractor.extract(pdf_dir / "scan.pdf")
    assert result.extractor == "ocr"


def test_broken_pdf_raises(pdf_dir: Path) -> None:
    extractor, _, _ = _extractor(pdf_dir, {}, {})
    with pytest.raises(ExtractError):
        extractor.extract(pdf_dir / "broken.pdf")


def test_no_text_anywhere_raises_with_ocr_hint(pdf_dir: Path) -> None:
    extractor, _, _ = _extractor(pdf_dir, {"blank.pdf": {}}, {}, ocr_available=False)
    with pytest.raises(ExtractError, match="OCR недоступен"):
        extractor.extract(pdf_dir / "blank.pdf")


def test_missing_file_raises(tmp_path: Path) -> None:
    extractor, _, _ = _extractor(tmp_path, {}, {})
    with pytest.raises(ExtractError):
        extractor.extract(tmp_path / "nope.pdf")
