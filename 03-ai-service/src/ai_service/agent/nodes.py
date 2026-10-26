"""Ноды графа инсайта. Каждая возвращает частичное обновление InsightState."""

import asyncio
from typing import Literal

from ai_service.agent.checks import rule_violations, sanitize
from ai_service.agent.context import DraftContext
from ai_service.agent.rules import match_triggers
from ai_service.agent.state import InsightState
from ai_service.agent.tools import AlfaRAGTool, CompanyProfileTool, CounterpartyTool
from ai_service.config import Settings
from ai_service.datasets.store import Datasets
from ai_service.llm.generator import InsightGenerator, plan_offline
from ai_service.logging import get_logger
from ai_service.rag.retriever import Retriever
from ai_service.schemas.common import NewsCategory
from ai_service.schemas.insight import CheckReport, NewsPlan

log = get_logger(__name__)

MAX_DRAFT_ATTEMPTS = 2


class InsightNodes:
    def __init__(
        self,
        generator: InsightGenerator,
        retriever: Retriever,
        datasets: Datasets,
        settings: Settings,
    ) -> None:
        self.generator = generator
        self.retriever = retriever
        self.datasets = datasets
        self.settings = settings
        self.profile_tool = CompanyProfileTool()
        self.counterparty_tool = CounterpartyTool()
        self.rag_tool = AlfaRAGTool()

    # ------------------------------------------------------------------ helpers
    def _ctx(self, state: InsightState) -> DraftContext:
        plan = state.get("plan") or NewsPlan(topic=state["news"].topic or NewsCategory.OTHER)
        return DraftContext(
            news=state["news"],
            company=state["company"],
            role=state["role"],
            plan=plan,
            triggers=state.get("matched_triggers", []),
            counterparties=state.get("counterparties", []),
            chunks=state.get("chunks", []),
            truncated=state.get("truncated", []),
            news_text=state.get("news_text", state["news"].text_for_analysis),
        )

    # ------------------------------------------------------------------ nodes
    async def plan(self, state: InsightState) -> dict[str, object]:
        note = ""
        try:
            plan = await self.generator.plan(state["news"])
        except Exception as exc:
            # Планирование — вспомогательный шаг: при сбое fast-модели берём детерминированный
            # план вместо того, чтобы ронять весь инсайт.
            log.warning("plan.fallback", error=type(exc).__name__)
            plan = plan_offline(state["news"])
            note = f"; LLM-план недоступен ({type(exc).__name__}), применён офлайн-план"
        return {
            "plan": plan,
            "steps": [
                f"plan: тема {plan.topic.value}, запросов к корпусу — {len(plan.queries)}{note}"
            ],
        }

    async def gather_context(self, state: InsightState) -> dict[str, object]:
        plan = state["plan"]
        assert plan is not None
        options = state["options"]
        steps: list[str] = []
        errors: list[str] = []

        # Инструменты датасетов читают pandas-фреймы синхронно — выносим из event loop.
        company, trace = await asyncio.to_thread(
            self.profile_tool.run, state["company"], self.datasets, options.enrich_from_datasets
        )
        steps += trace.steps
        errors += trace.errors

        triggers = match_triggers(company, plan.topic)
        steps.append(
            "match_triggers: " + ", ".join(t.as_text() for t in triggers)
            if triggers
            else "match_triggers: признаков не найдено"
        )

        counterparties, trace = await asyncio.to_thread(
            self.counterparty_tool.run, company, self.datasets, options.enrich_from_datasets
        )
        steps += trace.steps
        errors += trace.errors

        chunks, corpus_available, trace = await self.rag_tool.run(
            self.retriever,
            plan.queries,
            options.top_k,
            self.settings.rag_min_score,
            keywords=plan.keywords,
            query_text=f"{state['news'].title} {state['news'].summary_facts}",
            topic=plan.topic.value,
        )
        steps += trace.steps
        errors += trace.errors

        truncated: list[str] = []
        news_text = state["news"].text_for_analysis
        limit = self.settings.max_full_text_chars
        if len(news_text) > limit:
            news_text = news_text[:limit]
            truncated.append(f"news.full_text усечён до {limit} символов")
            steps.append(f"truncate: текст новости усечён до {limit} символов")

        return {
            "company": company,
            "matched_triggers": triggers,
            "counterparties": counterparties,
            "chunks": chunks,
            "corpus_available": corpus_available,
            "news_text": news_text,
            "truncated": truncated,
            "steps": steps,
            "errors": errors,
        }

    async def draft(self, state: InsightState) -> dict[str, object]:
        attempts = state.get("attempts", 0) + 1
        previous = state.get("check")
        feedback = list(previous.violations) if previous is not None else []
        draft = await self.generator.draft(self._ctx(state), feedback)
        label = "повторный черновик с замечаниями" if feedback else "черновик"
        return {
            "draft": draft,
            "attempts": attempts,
            "steps": [f"draft: {label} (попытка {attempts}, режим {self.generator.mode.value})"],
        }

    async def self_check(self, state: InsightState) -> dict[str, object]:
        draft = state["draft"]
        assert draft is not None
        ctx = self._ctx(state)
        violations = [v.as_text() for v in rule_violations(ctx, draft)]
        note = ""
        try:
            generator_report = await self.generator.check(ctx, draft)
        except Exception as exc:
            # Правила уже посчитаны локально; сбой checker-модели не должен ронять инсайт.
            log.warning("self_check.fallback", error=type(exc).__name__)
            generator_report = CheckReport(passed=True)
            note = f"; LLM-проверка недоступна ({type(exc).__name__}), применены правила"
        violations += [v for v in generator_report.violations if v not in violations]
        report = CheckReport(
            passed=not violations, violations=violations, attempts=state.get("attempts", 0)
        )
        status = "ok" if report.passed else f"нарушений — {len(violations)}"
        return {"check": report, "steps": [f"self_check: {status}{note}"]}

    def route_after_check(self, state: InsightState) -> Literal["draft", "finalize"]:
        check = state.get("check")
        if check is not None and not check.passed and state.get("attempts", 0) < MAX_DRAFT_ATTEMPTS:
            return "draft"
        return "finalize"

    async def finalize(self, state: InsightState) -> dict[str, object]:
        draft = state["draft"]
        check = state.get("check") or CheckReport(passed=True)
        assert draft is not None
        ctx = self._ctx(state)
        fixed: list[str] = []
        if not check.passed:
            violations = rule_violations(ctx, draft)
            draft, fixed = sanitize(draft, violations, ctx)
            if fixed:
                remaining = [v.as_text() for v in rule_violations(ctx, draft)]
                check = CheckReport(
                    passed=not remaining,
                    violations=check.violations,
                    attempts=check.attempts,
                    fixed=fixed,
                )
        step = "finalize: " + ("без правок" if not fixed else "зачистка — " + "; ".join(fixed))
        return {"draft": draft, "check": check, "fixed": fixed, "steps": [step]}
