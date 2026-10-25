"""Каталог отчётов: имя файла → официальное название (fallback — первая строка OCR)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_HEADER_NOISE = re.compile(
    r"^(центр макроэконом\w+ анализа|альфа[- ]банк|\d{1,2}\s+\w+\s+\d{4}\s*г?\.?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CatalogEntry:
    title: str
    author: str | None = None
    date: str | None = None
    topics: tuple[str, ...] = ()


@dataclass
class ReportsCatalog:
    entries: dict[str, CatalogEntry] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "ReportsCatalog":
        if not path.exists():
            return cls()
        with path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        entries: dict[str, CatalogEntry] = {}
        for file, meta in (raw.get("reports") or {}).items():
            if not isinstance(meta, dict) or "title" not in meta:
                continue
            entries[str(file)] = CatalogEntry(
                title=str(meta["title"]),
                author=str(meta["author"]) if meta.get("author") else None,
                date=str(meta["date"]) if meta.get("date") else None,
                topics=tuple(str(t) for t in meta.get("topics") or ()),
            )
        return cls(entries=entries)

    def title_for(self, file: str, first_page_text: str = "") -> str:
        entry = self.entries.get(file)
        if entry:
            return entry.title
        return guess_title(first_page_text) or Path(file).stem.replace("_", " ")


def guess_title(first_page_text: str, max_len: int = 160) -> str:
    """Первая содержательная строка первой страницы без служебных шапок и дат."""
    for line in first_page_text.splitlines():
        candidate = line.strip(" \t-—_|•")
        if len(candidate) < 8 or _HEADER_NOISE.match(candidate):
            continue
        return candidate[:max_len]
    return ""
