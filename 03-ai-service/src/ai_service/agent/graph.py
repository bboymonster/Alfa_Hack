"""Сборка LangGraph-графа инсайта и запуск с таймаутом и структурированными ошибками."""

import asyncio
import time
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from ai_service.agent.mapping import build_traceability, to_card
from ai_service.agent.nodes import InsightNodes
from ai_service.agent.state import InsightState
from ai_service.config import Settings
from ai_service.datasets.store import Datasets
from ai_service.errors import ApiError, ErrorCode
from ai_service.llm.generator import InsightGenerator
from ai_service.logging import get_logger
from ai_service.rag.retriever import Retriever
from ai_service.schemas.common import NewsCategory
from ai_service.schemas.insight import CheckReport, InsightRequest, InsightResponse, NewsPlan
from ai_service.scoring.scorer import score_news

log = get_logger(__name__)

RECURSION_LIMIT = 12


class InsightPipeline:
    def __init__(
        self,
        generator: InsightGenerator,
        retriever: Retriever,
        datasets: Datasets,
        settings: Settings,
    ) -> None:
        self.generator = generator
        self.settings = settings
        self.nodes = InsightNodes(generator, retriever, datasets, settings)
        self.graph = self._build()

    def _build(self) -> Any:
        retry = RetryPolicy(
            max_attempts=self.settings.llm_max_retries, initial_interval=0.5, backoff_factor=2.0
        )
        builder: StateGraph[InsightState] = StateGraph(InsightState)
        builder.add_node("plan", self.nodes.plan, retry_policy=retry)
        builder.add_node("gather_context", self.nodes.gather_context)
        builder.add_node("draft", self.nodes.draft, retry_policy=retry)
        builder.add_node("self_check", self.nodes.self_check, retry_policy=retry)
        builder.add_node("finalize", self.nodes.finalize)
        builder.add_edge(START, "plan")
        builder.add_edge("plan", "gather_context")
        builder.add_edge("gather_context", "draft")
        builder.add_edge("draft", "self_check")
        builder.add_conditional_edges(
            "self_check",
            self.nodes.route_after_check,
            {"draft": "draft", "finalize": "finalize"},
        )
        builder.add_edge("finalize", END)
        return builder.compile()

    async def run(self, request: InsightRequest, request_id: str) -> InsightResponse:
        started = time.perf_counter()
        initial: InsightState = {
            "request_id": request_id,
            "news": request.news,
            "company": request.company,
            "role": request.role,
            "options": request.options,
            "plan": None,
            "matched_triggers": [],
            "counterparties": [],
            "chunks": [],
            "corpus_available": False,
            "truncated": [],
            "draft": None,
            "check": None,
            "attempts": 0,
            "fixed": [],
            "steps": [],
            "errors": [],
        }
        try:
            async with asyncio.timeout(self.settings.insight_timeout_s):
                state: InsightState = await self.graph.ainvoke(
                    initial, config={"recursion_limit": RECURSION_LIMIT}
                )
        except TimeoutError as exc:
            raise ApiError(
                ErrorCode.LLM_TIMEOUT,
                f"Генерация инсайта не уложилась в {self.settings.insight_timeout_s:.0f} с.",
            ) from exc
        except ApiError:
            raise
        except Exception as exc:
            log.warning("insight.failed", error=type(exc).__name__)
            raise ApiError(
                ErrorCode.LLM_ERROR,
                f"Сбой генерации инсайта: {type(exc).__name__}.",
                details=[{"error": str(exc)[:300]}],
            ) from exc

        six = state["draft"]
        plan = state["plan"] or NewsPlan(topic=request.news.topic or NewsCategory.OTHER)
        assert six is not None
        triggers = state.get("matched_triggers", [])
        check = state.get("check") or CheckReport(passed=True)
        importance = score_news(state["company"], request.role, request.news, plan.topic, triggers)
        traceability = build_traceability(
            six=six,
            news=request.news,
            triggers=triggers,
            chunks=state.get("chunks", []),
            steps=list(state.get("steps", [])) + [f"errors: {e}" for e in state.get("errors", [])],
            check=check,
            corpus_available=state.get("corpus_available", False),
            truncated=state.get("truncated", []),
            mode=self.generator.mode,
            prompt_version=self.generator.prompt_version,
            models=self.generator.models,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "insight.done",
            mode=self.generator.mode.value,
            topic=plan.topic.value,
            triggers=len(triggers),
            chunks=len(state.get("chunks", [])),
            passed=check.passed,
            attempts=check.attempts,
            latency_ms=latency_ms,
        )
        return InsightResponse(
            request_id=request_id,
            mode=self.generator.mode,
            insight=six,
            card=to_card(six, request.news, triggers),
            importance=importance,
            traceability=traceability,
            latency_ms=latency_ms,
        )
