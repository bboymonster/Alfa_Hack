from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ai_service.schemas.common import Mode, NewsCategory
from ai_service.schemas.news import NewsItem


class NewsSource(BaseModel):
    name: str = Field(min_length=1)
    url: str
    kind: Literal["rss"] = "rss"
    enabled: bool = True
    source_title: str = Field(min_length=1, description="Как подписывать источник в карточке")
    default_category: NewsCategory | None = None


class CollectRequest(BaseModel):
    sources: list[str] | None = None
    since: datetime | None = None
    exclude_urls: list[str] = Field(default_factory=list, max_length=5000)
    limit: int = Field(default=100, ge=1, le=500)


class SourceStatus(BaseModel):
    name: str
    ok: bool
    fetched: int = 0
    error: str | None = None
    latency_ms: int = 0


class CollectReport(BaseModel):
    sources: list[SourceStatus]
    returned: int
    duplicates_dropped: int
    irrelevant_dropped: int
    older_dropped: int


class CollectResponse(BaseModel):
    request_id: str
    mode: Mode
    items: list[NewsItem]
    report: CollectReport
