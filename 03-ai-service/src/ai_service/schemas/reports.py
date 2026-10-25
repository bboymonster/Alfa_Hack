from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReportDocument(BaseModel):
    report_id: str
    title: str
    file: str
    pages: int = Field(ge=0)
    chunks: int = Field(ge=0)
    indexed_at: datetime
    extractor: Literal["text", "ocr", "mixed"]


class ReportChunk(BaseModel):
    chunk_id: str
    report_id: str
    title: str
    file: str
    page: int = Field(ge=1)
    index: int = Field(ge=0)
    text: str
    score: float | None = None
    dense_score: float | None = None

    @property
    def url(self) -> str:
        return f"/articles/{self.file}#page={self.page}"


class SearchResponse(BaseModel):
    query: str
    results: list[ReportChunk]
    corpus_available: bool


class ReportsResponse(BaseModel):
    corpus_available: bool
    reports: list[ReportDocument]


class IndexedFile(BaseModel):
    file: str
    ok: bool
    report: ReportDocument | None = None
    error: str | None = None
    seconds: float = 0.0


class IndexReport(BaseModel):
    files: list[IndexedFile]
    reports: int
    chunks: int
