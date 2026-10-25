from typing import Literal

from pydantic import BaseModel, Field

from ai_service.schemas.common import Mode, Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.news import NewsItem


class ScoreFactor(BaseModel):
    name: str
    delta: int
    explanation: str


class ImportanceScore(BaseModel):
    news_id: str
    score: int = Field(ge=1, le=10)
    factors: list[ScoreFactor] = []


class ScoreRequest(BaseModel):
    company: CompanyProfile
    role: Role
    news: list[NewsItem] = Field(min_length=1, max_length=200)


class ScoreResponse(BaseModel):
    request_id: str
    mode: Mode
    scores: list[ImportanceScore]


class Adjustment(BaseModel):
    """Поправка LLM к rule-based оценке: только ±1 с объяснением."""

    news_id: str
    delta: Literal[-1, 0, 1]
    reason: str = Field(max_length=300)


class AdjustmentList(BaseModel):
    adjustments: list[Adjustment]
