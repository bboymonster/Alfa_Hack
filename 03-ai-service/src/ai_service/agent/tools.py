"""Инструменты агента. Вызываются нодой gather_context явно; ошибки возвращаются в state,
а не роняют граф."""

import asyncio
import re
from dataclasses import dataclass, field

from ai_service.datasets.store import Datasets
from ai_service.logging import get_logger
from ai_service.rag.quality import is_clean_text
from ai_service.rag.retriever import Retriever
from ai_service.schemas.company import CompanyProfile, Counterparty
from ai_service.schemas.reports import ReportChunk

log = get_logger(__name__)


@dataclass
class ToolTrace:
    steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class CompanyProfileTool:
    """Читает профиль из запроса и, если разрешено, дополняет пустые поля из датасета."""

    name = "CompanyProfileTool"

    def run(
        self, company: CompanyProfile, datasets: Datasets, enrich: bool
    ) -> tuple[CompanyProfile, ToolTrace]:
        trace = ToolTrace()
        if not enrich or not datasets.available:
            trace.steps.append(f"{self.name}: профиль из запроса ({company.synthetic_u})")
            return company, trace
        try:
            merged, filled = datasets.merge_missing(company)
        except Exception as exc:
            trace.errors.append(f"{self.name}: {type(exc).__name__}")
            trace.steps.append(f"{self.name}: датасет недоступен, профиль из запроса")
            return company, trace
        if filled:
            trace.steps.append(f"{self.name}: дополнено из датасета: {', '.join(filled)}")
        else:
            trace.steps.append(f"{self.name}: профиль из запроса, датасет без дополнений")
        return merged, trace


class CounterpartyTool:
    """Контрагенты из запроса или из df_Uid_payment_hack.csv."""

    name = "CounterpartyTool"

    def run(
        self, company: CompanyProfile, datasets: Datasets, enrich: bool, top_n: int = 5
    ) -> tuple[list[Counterparty], ToolTrace]:
        trace = ToolTrace()
        if company.counterparties:
            items = company.counterparties[:top_n]
            trace.steps.append(f"{self.name}: {len(items)} контрагентов из запроса")
            return items, trace
        if not enrich or not datasets.available:
            trace.steps.append(f"{self.name}: данных о контрагентах нет")
            return [], trace
        try:
            items = datasets.top_counterparties(company.synthetic_u, n=top_n)
        except Exception as exc:
            trace.errors.append(f"{self.name}: {type(exc).__name__}")
            trace.steps.append(f"{self.name}: датасет платежей недоступен")
            return [], trace
        trace.steps.append(f"{self.name}: {len(items)} контрагентов из датасета платежей")
        return items, trace


class AlfaRAGTool:
    """Гибридный поиск по отчётам банка с гейтом слабой релевантности."""

    name = "AlfaRAGTool"

    async def run(
        self,
        retriever: Retriever,
        queries: list[str],
        top_k: int,
        min_score: float,
        keywords: list[str] | None = None,
        query_text: str = "",
        topic: str | None = None,
    ) -> tuple[list[ReportChunk], bool, ToolTrace]:
        trace = ToolTrace()
        if not retriever.available:
            trace.steps.append(f"{self.name}: corpus unavailable — позиция банка не формируется")
            return [], False, trace
        merged: dict[str, ReportChunk] = {}
        # Широкий пул кандидатов: ре-ранк и лимит на отчёт работают поверх него.
        candidates = max(top_k * CANDIDATE_MULTIPLIER, MIN_CANDIDATES)
        for query in queries[:4]:
            try:
                found = await asyncio.to_thread(retriever.search, query, candidates)
            except Exception as exc:
                trace.errors.append(f"{self.name}: {type(exc).__name__}")
                log.warning("rag.search_failed", error=type(exc).__name__)
                continue
            for chunk in found:
                current = merged.get(chunk.chunk_id)
                if current is None or (chunk.score or 0.0) > (current.score or 0.0):
                    merged[chunk.chunk_id] = chunk
        ranked = rerank(list(merged.values()), keywords or [], query_text, topic)
        kept = [c for c in ranked if _passes(c, min_score)]
        best = max((_relevance(c) or 0.0 for c in ranked), default=0.0)
        if not kept:
            trace.steps.append(
                f"{self.name}: weak retrieval (best {best:.2f} < {min_score:.2f}) — "
                "позиция банка не формируется"
            )
            return [], True, trace
        trace.steps.append(
            f"{self.name}: {len(queries[:4])} запросов → {len(kept)} фрагментов "
            f"(best {best:.2f}); отчёты: " + ", ".join(sorted({c.title for c in kept}))
        )
        return kept[:top_k], True, trace


TITLE_MATCH_BOOST = 0.3
NOISE_PENALTY = 0.2
CANDIDATE_MULTIPLIER = 4
MIN_CANDIDATES = 20


_STEM_TOKEN = re.compile(r"[а-яёa-z]{5,}", re.IGNORECASE)


def _stems(text: str) -> set[str]:
    return {t.lower()[:5] for t in _STEM_TOKEN.findall(text)}


TEXT_OVERLAP_BOOST = 0.4
TOPIC_MATCH_BOOST = 0.2
MAX_CHUNKS_PER_REPORT = 2


def rerank(
    chunks: list[ReportChunk],
    keywords: list[str],
    query_text: str = "",
    topic: str | None = None,
) -> list[ReportChunk]:
    """Поверх RRF: бонус за совпадение основ ключевых слов темы с названием отчёта, бонус за
    лексическое пересечение текста новости с фрагментом, штраф за «шумный» OCR-текст,
    не больше MAX_CHUNKS_PER_REPORT фрагментов одного отчёта (длинные отчёты не вытесняют
    короткие профильные записки)."""
    keyword_stems = _stems(" ".join(keywords))
    query_stems = _stems(query_text) | keyword_stems
    reranked: list[ReportChunk] = []
    for chunk in chunks:
        score = chunk.score or 0.0
        if keyword_stems and keyword_stems & _stems(chunk.title):
            score += TITLE_MATCH_BOOST
        if topic and topic in chunk.topics:
            score += TOPIC_MATCH_BOOST
        if query_stems:
            overlap = len(query_stems & _stems(chunk.text)) / len(query_stems)
            score += TEXT_OVERLAP_BOOST * overlap
        if not is_clean_text(chunk.text):
            score -= NOISE_PENALTY
        reranked.append(chunk.model_copy(update={"score": round(score, 4)}))
    reranked.sort(key=lambda c: c.score or 0.0, reverse=True)
    per_report: dict[str, int] = {}
    capped: list[ReportChunk] = []
    for chunk in reranked:
        if per_report.get(chunk.report_id, 0) >= MAX_CHUNKS_PER_REPORT:
            continue
        per_report[chunk.report_id] = per_report.get(chunk.report_id, 0) + 1
        capped.append(chunk)
    return capped


def _relevance(chunk: ReportChunk) -> float | None:
    return chunk.dense_score if chunk.dense_score is not None else chunk.score


def _passes(chunk: ReportChunk, min_score: float) -> bool:
    # Без косинусной оценки гейт слабой релевантности не пройден: RRF-скор с бонусами
    # ре-ранка не сравним с порогом и пропускал бы лексические совпадения с заголовком.
    relevance = _relevance(chunk)
    return relevance is not None and relevance >= min_score
