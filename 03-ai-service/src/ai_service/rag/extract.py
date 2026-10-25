"""Извлечение текста страниц PDF: текстовый слой PyMuPDF → OCR Tesseract; кэш по sha256."""

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

from ai_service.logging import get_logger

log = get_logger(__name__)

Extractor = Literal["text", "ocr", "mixed"]


class ExtractError(Exception):
    pass


@dataclass(frozen=True)
class PageText:
    page: int
    text: str
    source: Literal["text", "ocr", "empty"]


@dataclass(frozen=True)
class Extracted:
    pages: list[PageText]
    extractor: Extractor
    sha256: str

    @property
    def page_count(self) -> int:
        return len(self.pages)


class PageTextBackend(Protocol):
    name: str

    def available(self) -> bool: ...

    def extract(self, pdf_path: Path, pages: list[int] | None) -> dict[int, str]:
        """Текст по номерам страниц (с 1). pages=None → все страницы."""
        ...


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def page_count(pdf_path: Path) -> int:
    import pymupdf

    try:
        with pymupdf.open(str(pdf_path)) as doc:  # type: ignore[no-untyped-call]
            return len(doc)
    except Exception as exc:
        raise ExtractError(f"Не удалось открыть PDF {pdf_path.name}: {exc}") from exc


class PyMuPdfTextBackend:
    name = "text"

    def available(self) -> bool:
        return True

    def extract(self, pdf_path: Path, pages: list[int] | None) -> dict[int, str]:
        import pymupdf

        result: dict[int, str] = {}
        try:
            with pymupdf.open(str(pdf_path)) as doc:  # type: ignore[no-untyped-call]
                numbers = pages or list(range(1, len(doc) + 1))
                for number in numbers:
                    result[number] = str(doc[number - 1].get_text()).strip()
        except Exception as exc:
            raise ExtractError(f"Не удалось прочитать PDF {pdf_path.name}: {exc}") from exc
        return result


class TesseractOcrBackend:
    name = "ocr"

    def __init__(self, lang: str = "rus+eng", dpi: int = 200) -> None:
        self.lang = lang
        self.dpi = dpi

    def available(self) -> bool:
        return shutil.which("tesseract") is not None

    def extract(self, pdf_path: Path, pages: list[int] | None) -> dict[int, str]:
        import pymupdf
        import pytesseract
        from PIL import Image

        result: dict[int, str] = {}
        with pymupdf.open(str(pdf_path)) as doc:  # type: ignore[no-untyped-call]
            numbers = pages or list(range(1, len(doc) + 1))
            for number in numbers:
                pix = doc[number - 1].get_pixmap(dpi=self.dpi)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                result[number] = str(pytesseract.image_to_string(image, lang=self.lang)).strip()
        return result


MIN_TEXT_CHARS = 40


class CachedExtractor:
    """Текстовый слой → OCR для пустых страниц; результат кэшируется в cache_dir/<sha>.json."""

    def __init__(
        self,
        cache_dir: Path,
        text_backend: PageTextBackend | None = None,
        ocr_backend: PageTextBackend | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.text_backend = text_backend or PyMuPdfTextBackend()
        self.ocr_backend = ocr_backend or TesseractOcrBackend()

    def _cache_path(self, sha: str) -> Path:
        return self.cache_dir / f"{sha}.json"

    def _load_cache(self, sha: str) -> Extracted | None:
        path = self._cache_path(sha)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            pages = [PageText(**p) for p in raw["pages"]]
            return Extracted(pages=pages, extractor=raw["extractor"], sha256=sha)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _save_cache(self, extracted: Extracted, file: str) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "file": file,
            "sha256": extracted.sha256,
            "extractor": extracted.extractor,
            "cached_at": datetime.now(UTC).isoformat(),
            "pages": [p.__dict__ for p in extracted.pages],
        }
        self._cache_path(extracted.sha256).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def extract(self, pdf_path: Path, *, force: bool = False) -> Extracted:
        if not pdf_path.exists():
            raise ExtractError(f"Файл не найден: {pdf_path}")
        sha = file_sha256(pdf_path)
        if not force:
            cached = self._load_cache(sha)
            if cached is not None:
                log.info("extract.cache_hit", file=pdf_path.name, pages=cached.page_count)
                return cached

        total = page_count(pdf_path)
        text_pages = self.text_backend.extract(pdf_path, None)
        needs_ocr = [n for n in range(1, total + 1) if len(text_pages.get(n, "")) < MIN_TEXT_CHARS]
        ocr_pages: dict[int, str] = {}
        if needs_ocr:
            if self.ocr_backend.available():
                log.info("extract.ocr", file=pdf_path.name, pages=len(needs_ocr))
                ocr_pages = self.ocr_backend.extract(pdf_path, needs_ocr)
            else:
                log.warning("extract.ocr_unavailable", file=pdf_path.name, pages=len(needs_ocr))

        pages: list[PageText] = []
        used_text = used_ocr = False
        for number in range(1, total + 1):
            text = text_pages.get(number, "")
            if len(text) >= MIN_TEXT_CHARS:
                pages.append(PageText(page=number, text=text, source="text"))
                used_text = True
            elif len(ocr_pages.get(number, "")) >= MIN_TEXT_CHARS:
                pages.append(PageText(page=number, text=ocr_pages[number], source="ocr"))
                used_ocr = True
            else:
                pages.append(PageText(page=number, text="", source="empty"))

        if not any(p.text for p in pages):
            raise ExtractError(
                f"В {pdf_path.name} не удалось извлечь текст ни с одной страницы"
                + ("" if self.ocr_backend.available() else " (OCR недоступен)")
            )
        extractor: Extractor = (
            "mixed" if used_text and used_ocr else ("ocr" if used_ocr else "text")
        )
        extracted = Extracted(pages=pages, extractor=extractor, sha256=sha)
        self._save_cache(extracted, pdf_path.name)
        return extracted
