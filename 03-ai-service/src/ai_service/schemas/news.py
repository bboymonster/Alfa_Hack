from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from ai_service.schemas.common import NewsCategory, ensure_tz_aware

TzDatetime = Annotated[datetime, AfterValidator(ensure_tz_aware)]


class NewsItem(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    summary_facts: str = Field(min_length=1, max_length=4000)
    full_text: str | None = Field(default=None, max_length=20000)
    source: str = Field(min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    published_at: TzDatetime
    category: str = Field(min_length=1, max_length=100)
    topic: NewsCategory | None = None

    @property
    def text_for_analysis(self) -> str:
        parts = [self.title, self.summary_facts]
        if self.full_text:
            parts.append(self.full_text)
        return "\n".join(parts)
