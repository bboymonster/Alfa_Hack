from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Role(StrEnum):
    CEO = "CEO"
    CFO = "CFO"
    ACCOUNTANT = "ACCOUNTANT"


class Company(BaseModel):
    synthetic_u: str
    name: str
    mainokved_code: str
    mainokved_name: str
    revenue_company: float
    cl_product_loa_mark: bool
    fts_flag: bool
    city: str
    region: str


class User(BaseModel):
    id: str
    email: str
    full_name: str
    role: Role
    current_company_id: str
    allowed_company_ids: list[str]


class RequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(RequestBody):
    # Тестовый логин alfa-hack-2026 не является email, поэтому здесь обычная строка.
    email: NonEmptyText = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(RequestBody):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: NonEmptyText = Field(max_length=100)
    role: Role = Role.CEO
    company_id: str = "U_1595"


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: User


class News(BaseModel):
    id: str
    title: str
    summary_facts: str
    source: str
    source_url: str | None = None
    published_at: datetime
    category: str


class Traceability(BaseModel):
    matched_company_features: list[str]
    verified_sources: list[str]


class SelfCheckReport(BaseModel):
    """Результат самопроверки агента (03-ai-service)."""

    passed: bool
    violations: list[str] = []
    attempts: int = 0
    fixed: list[str] = []


class Insight(BaseModel):
    why_it_matters: str
    risks: list[str]
    opportunities: list[str]
    action_item: str
    alfa_bank_position: str | None = None
    alfa_report_name: str | None = None
    alfa_report_page: int | None = None
    alfa_report_url: str | None = None
    traceability: Traceability
    # Агентная трассировка из 03-ai-service (шаги, самопроверка, уверенность, режим).
    agent_steps: list[str] | None = None
    self_check: SelfCheckReport | None = None
    confidence: float | None = None
    mode: str | None = None


class FeedItem(BaseModel):
    id: str
    company_id: str
    role: Role
    news: News
    insight: Insight
    importance_score: int = Field(ge=1, le=10)
    is_favorite: bool = False
    is_demo: bool = True


class FeedResponse(BaseModel):
    items: list[FeedItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    is_demo: bool = True


class FavoriteRequest(RequestBody):
    is_favorite: bool = Field(strict=True)


class FavoriteResponse(BaseModel):
    id: str
    is_favorite: bool


class AskRequest(RequestBody):
    question: NonEmptyText = Field(max_length=2000)


class AskResponse(BaseModel):
    feed_item_id: str
    answer: str
    is_demo: bool = True


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: str = "demo"
    storage: str = "memory"
    ai: str = "mock"
