"""Контексты для генераторов и общие форматтеры блоков промптов."""

import json
from dataclasses import dataclass, field

from ai_service.agent.rules import ROLE_FOCUS
from ai_service.schemas.common import MatchedFeature, Role
from ai_service.schemas.company import CompanyProfile, Counterparty
from ai_service.schemas.insight import Card, NewsPlan
from ai_service.schemas.news import NewsItem
from ai_service.schemas.reports import ReportChunk


@dataclass
class DraftContext:
    news: NewsItem
    company: CompanyProfile
    role: Role
    plan: NewsPlan
    triggers: list[MatchedFeature]
    counterparties: list[Counterparty] = field(default_factory=list)
    chunks: list[ReportChunk] = field(default_factory=list)
    truncated: list[str] = field(default_factory=list)
    news_text: str = ""


@dataclass
class ChatContext:
    news: NewsItem
    card: Card
    company: CompanyProfile
    role: Role
    question: str
    chunks: list[ReportChunk] = field(default_factory=list)
    on_topic_hint: bool = True


def role_focus_text(role: Role) -> str:
    focus = ROLE_FOCUS[role]
    return f"{focus.title}: {focus.description}"


def company_block(company: CompanyProfile) -> str:
    lines = [
        f"Название: {company.name} ({company.synthetic_u})",
        f"ОКВЭД: {company.mainokved_code} — {company.mainokved_name}",
        f"Выручка: {company.revenue_human}",
    ]
    if company.region:
        lines.append(f"Регион: {company.region}")
    if company.workers_label:
        lines.append(f"Численность: {company.workers_label}")
    if company.company_age_years_gradation:
        lines.append(f"Возраст компании (лет): {company.company_age_years_gradation}")
    return "\n".join(lines)


def features_block(triggers: list[MatchedFeature]) -> str:
    if not triggers:
        return "(признаков нет)"
    return "\n".join(f"- {t.feature} = {t.value}: {t.why}" for t in triggers)


def counterparties_block(items: list[Counterparty]) -> str:
    if not items:
        return "(нет данных)"
    lines = []
    for cp in items[:5]:
        direction = "платит компании" if cp.direction == "payer" else "получает от компании"
        industry = f", {cp.mainokved_name}" if cp.mainokved_name else ""
        lines.append(
            f"- {cp.synthetic_u} {direction}: {cp.pay_amt / 1_000_000:.1f} млн ₽, "
            f"{cp.pay_cnt} платежей{industry}"
        )
    return "\n".join(lines)


def chunks_block(chunks: list[ReportChunk], max_chars: int = 1200) -> str:
    if not chunks:
        return "(фрагментов нет — позицию банка не формулировать)"
    lines = []
    for chunk in chunks:
        text = chunk.text[:max_chars]
        lines.append(f"{chunk.chunk_id} | {chunk.title} | стр. {chunk.page} | {text}")
    return "\n\n".join(lines)


def card_json(card: Card) -> str:
    return json.dumps(card.model_dump(), ensure_ascii=False, indent=1)
