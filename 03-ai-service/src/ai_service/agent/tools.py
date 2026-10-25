"""Инструменты агента. Вызываются нодой gather_context явно; ошибки возвращаются в state,
а не роняют граф."""

import asyncio
from dataclasses import dataclass, field

from ai_service.datasets.store import Datasets
from ai_service.logging import get_logger
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
        self, retriever: Retriever, queries: list[str], top_k: int, min_score: float
    ) -> tuple[list[ReportChunk], bool, ToolTrace]:
        trace = ToolTrace()
        if not retriever.available:
            trace.steps.append(f"{self.name}: corpus unavailable — позиция банка не формируется")
            return [], False, trace
        merged: dict[str, ReportChunk] = {}
        for query in queries[:4]:
            try:
                found = await asyncio.to_thread(retriever.search, query, top_k)
            except Exception as exc:
                trace.errors.append(f"{self.name}: {type(exc).__name__}")
                log.warning("rag.search_failed", error=type(exc).__name__)
                continue
            for chunk in found:
                current = merged.get(chunk.chunk_id)
                if current is None or (chunk.score or 0.0) > (current.score or 0.0):
                    merged[chunk.chunk_id] = chunk
        ranked = sorted(merged.values(), key=lambda c: c.score or 0.0, reverse=True)
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


def _relevance(chunk: ReportChunk) -> float | None:
    return chunk.dense_score if chunk.dense_score is not None else chunk.score


def _passes(chunk: ReportChunk, min_score: float) -> bool:
    relevance = _relevance(chunk)
    return relevance is None or relevance >= min_score
