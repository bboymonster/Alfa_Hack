"""Маппинг внутренних шести вопросов в публичную карточку backend и сборка трассировки."""

from ai_service.schemas.common import MatchedFeature, Mode, SourceRef
from ai_service.schemas.insight import (
    Card,
    CardTraceability,
    CheckReport,
    SixQuestions,
    Traceability,
)
from ai_service.schemas.news import NewsItem
from ai_service.schemas.reports import ReportChunk


def report_url(file: str, page: int) -> str:
    return f"/articles/{file}#page={page}"


def verified_sources(
    six: SixQuestions, news: NewsItem, chunks: list[ReportChunk]
) -> list[SourceRef]:
    sources: list[SourceRef] = [
        SourceRef(kind="news", title=f"{news.source}: {news.title}", url=news.source_url)
    ]
    position = six.q5_alfa_bank_position
    if position is not None:
        sources.append(
            SourceRef(
                kind="report",
                title=position.report_title,
                url=report_url(position.report_file, position.page),
                page=position.page,
                chunk_id=position.chunk_id,
            )
        )
    return sources


def to_card(six: SixQuestions, news: NewsItem, triggers: list[MatchedFeature]) -> Card:
    position = six.q5_alfa_bank_position
    why = six.q2_why_matters_for_company
    return Card(
        why_it_matters=why,
        risks=list(six.q3_risks),
        opportunities=list(six.q3_opportunities),
        action_item="; ".join(six.q4_relevant_actions),
        alfa_bank_position=position.statement if position else None,
        alfa_report_name=position.report_title if position else None,
        alfa_report_page=position.page if position else None,
        alfa_report_url=report_url(position.report_file, position.page) if position else None,
        traceability=CardTraceability(
            matched_company_features=[t.as_text() for t in triggers],
            verified_sources=[s.as_text() for s in verified_sources(six, news, [])],
        ),
    )


def compute_confidence(
    six: SixQuestions,
    triggers: list[MatchedFeature],
    check: CheckReport,
    corpus_available: bool,
    mode: Mode,
) -> float:
    confidence = 0.5
    if six.q5_alfa_bank_position is not None:
        confidence += 0.2
    elif corpus_available:
        confidence -= 0.05
    if len([t for t in triggers if t.value == "1"]) >= 2:
        confidence += 0.1
    if check.fixed:
        confidence -= 0.2
    elif check.violations:
        confidence -= 0.1
    if mode == Mode.OFFLINE:
        confidence -= 0.1
    return round(max(0.0, min(1.0, confidence)), 2)


def build_traceability(
    *,
    six: SixQuestions,
    news: NewsItem,
    triggers: list[MatchedFeature],
    chunks: list[ReportChunk],
    steps: list[str],
    check: CheckReport,
    corpus_available: bool,
    truncated: list[str],
    mode: Mode,
    prompt_version: str,
    models: dict[str, str],
) -> Traceability:
    return Traceability(
        matched_company_features=triggers,
        verified_sources=verified_sources(six, news, chunks),
        agent_steps=steps,
        self_check=check,
        confidence=compute_confidence(six, triggers, check, corpus_available, mode),
        corpus_available=corpus_available,
        truncated_inputs=truncated,
        mode=mode,
        prompt_version=prompt_version,
        models=models,
    )
