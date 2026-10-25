from pydantic import BaseModel, Field

from ai_service.schemas.common import MatchedFeature, Mode, NewsCategory, Role, SourceRef
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.news import NewsItem
from ai_service.schemas.score import ImportanceScore


class NewsPlan(BaseModel):
    """Результат шага планирования: тема, ключевые слова, запросы к корпусу."""

    topic: NewsCategory
    keywords: list[str] = Field(default_factory=list, max_length=12)
    queries: list[str] = Field(default_factory=list, max_length=4)


class BankPosition(BaseModel):
    statement: str = Field(min_length=1, max_length=1500)
    report_title: str
    report_file: str
    page: int = Field(ge=1)
    chunk_id: str
    quote: str = Field(min_length=1, max_length=400)
    score: float = 0.0


class SixQuestions(BaseModel):
    """Шесть обязательных вопросов интерпретации (стр. 14 ТЗ)."""

    q1_what_happened: str = Field(min_length=1, max_length=2000)
    q2_why_matters_for_company: str = Field(min_length=1, max_length=2000)
    q3_risks: list[str] = Field(default_factory=list, max_length=5)
    q3_opportunities: list[str] = Field(default_factory=list, max_length=5)
    q4_relevant_actions: list[str] = Field(min_length=1, max_length=5)
    q5_alfa_bank_position: BankPosition | None = None
    q6_basis: str = Field(min_length=1, max_length=1500)


class CheckReport(BaseModel):
    passed: bool
    violations: list[str] = []
    attempts: int = 0
    fixed: list[str] = []


class Traceability(BaseModel):
    matched_company_features: list[MatchedFeature]
    verified_sources: list[SourceRef]
    agent_steps: list[str]
    self_check: CheckReport
    confidence: float = Field(ge=0.0, le=1.0)
    corpus_available: bool
    truncated_inputs: list[str] = []
    mode: Mode
    prompt_version: str
    models: dict[str, str] = {}


class CardTraceability(BaseModel):
    matched_company_features: list[str]
    verified_sources: list[str]


class Card(BaseModel):
    """Публичный формат backend `Insight` (02-backend/app/schemas.py).

    Не менять без согласования с владельцем backend.
    """

    why_it_matters: str
    risks: list[str]
    opportunities: list[str]
    action_item: str
    alfa_bank_position: str | None = None
    alfa_report_name: str | None = None
    alfa_report_page: int | None = None
    alfa_report_url: str | None = None
    traceability: CardTraceability


class InsightOptions(BaseModel):
    top_k: int = Field(default=5, ge=1, le=10)
    enrich_from_datasets: bool = True


class InsightRequest(BaseModel):
    news: NewsItem
    company: CompanyProfile
    role: Role
    options: InsightOptions = InsightOptions()


class InsightResponse(BaseModel):
    request_id: str
    mode: Mode
    insight: SixQuestions
    card: Card
    importance: ImportanceScore
    traceability: Traceability
    latency_ms: int
