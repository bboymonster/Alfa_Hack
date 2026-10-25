from datetime import datetime
from enum import StrEnum
from math import isnan
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class Role(StrEnum):
    CEO = "CEO"
    CFO = "CFO"
    ACCOUNTANT = "ACCOUNTANT"


class Mode(StrEnum):
    LLM = "llm"
    OFFLINE = "offline"


class NewsCategory(StrEnum):
    MONETARY_POLICY = "monetary_policy"
    INFLATION = "inflation"
    LABOR_MARKET = "labor_market"
    REGULATION_TAX = "regulation_tax"
    LOGISTICS_TRADE = "logistics_trade"
    INDUSTRY_MARKETS = "industry_markets"
    CONSUMER_DEMAND = "consumer_demand"
    COMMODITIES = "commodities"
    OTHER = "other"


CATEGORY_LABELS_RU: dict[NewsCategory, str] = {
    NewsCategory.MONETARY_POLICY: "Финансы и ДКП",
    NewsCategory.INFLATION: "Инфляция и цены",
    NewsCategory.LABOR_MARKET: "Рынок труда и кадры",
    NewsCategory.REGULATION_TAX: "Регулирование и налоги",
    NewsCategory.LOGISTICS_TRADE: "Логистика и внешняя торговля",
    NewsCategory.INDUSTRY_MARKETS: "Отрасль и рынки",
    NewsCategory.CONSUMER_DEMAND: "Торговля и ритейл",
    NewsCategory.COMMODITIES: "Промышленность и сырьё",
    NewsCategory.OTHER: "Прочее",
}


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, int | float):
        return not (isinstance(value, float) and isnan(value)) and value != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"", "0", "0.0", "false", "нет", "no", "nan"}:
            return False
        if text in {"1", "1.0", "true", "да", "yes"}:
            return True
    raise ValueError(f"Ожидался признак 0/1 или bool, получено: {value!r}")


def _nan_to_none(value: Any) -> Any:
    if isinstance(value, float) and isnan(value):
        return None
    if isinstance(value, str) and value.strip().lower() in {"", "nan", "none", "null"}:
        return None
    return value


Mark = Annotated[bool, BeforeValidator(_to_bool)]
OptStr = Annotated[str | None, BeforeValidator(_nan_to_none)]
StrippedText = Annotated[
    str, Field(min_length=1), BeforeValidator(lambda v: v.strip() if isinstance(v, str) else v)
]


def ensure_tz_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("published_at должен содержать часовой пояс")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(BaseModel):
    kind: Literal["news", "report"]
    title: str
    url: str | None = None
    page: int | None = Field(default=None, ge=1)
    chunk_id: str | None = None

    def as_text(self) -> str:
        if self.kind == "report" and self.page is not None:
            return f"{self.title}, стр. {self.page}"
        return self.url or self.title


class MatchedFeature(BaseModel):
    feature: str = Field(description="Имя поля датасета, например CL_PRODUCT_LOA_MARK")
    value: str
    why: str

    def as_text(self) -> str:
        return f"{self.feature}={self.value}"


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[dict[str, Any]] = []


class ErrorResponse(BaseModel):
    error: ErrorBody


class CorpusStatus(BaseModel):
    available: bool
    reports: int = 0
    chunks: int = 0
    indexed_at: datetime | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Mode
    version: str
    models: dict[str, str] = {}
    corpus: CorpusStatus
    ocr_available: bool
