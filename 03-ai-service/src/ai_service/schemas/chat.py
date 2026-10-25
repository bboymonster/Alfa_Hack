from pydantic import BaseModel, Field

from ai_service.schemas.common import Mode, Role, SourceRef, StrippedText
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.insight import Card
from ai_service.schemas.news import NewsItem


class AskRequest(BaseModel):
    news: NewsItem
    card: Card
    company: CompanyProfile
    role: Role
    question: StrippedText = Field(max_length=2000)


class ChatDraft(BaseModel):
    """Structured output модели для чата."""

    answer: str = Field(min_length=1, max_length=3000)
    used_chunk_ids: list[str] = []
    on_topic: bool = True


class AskResponse(BaseModel):
    request_id: str
    mode: Mode
    answer: str
    sources: list[SourceRef]
    on_topic: bool
