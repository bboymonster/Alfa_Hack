import operator
from typing import Annotated, TypedDict

from ai_service.schemas.common import MatchedFeature, Role
from ai_service.schemas.company import CompanyProfile, Counterparty
from ai_service.schemas.insight import CheckReport, InsightOptions, NewsPlan, SixQuestions
from ai_service.schemas.news import NewsItem
from ai_service.schemas.reports import ReportChunk


class InsightState(TypedDict, total=False):
    request_id: str
    news: NewsItem
    company: CompanyProfile
    role: Role
    options: InsightOptions
    plan: NewsPlan | None
    matched_triggers: list[MatchedFeature]
    counterparties: list[Counterparty]
    chunks: list[ReportChunk]
    corpus_available: bool
    news_text: str
    truncated: list[str]
    draft: SixQuestions | None
    check: CheckReport | None
    attempts: int
    fixed: list[str]
    steps: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
