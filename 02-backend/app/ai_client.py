"""HTTP-клиент 03-ai-service. Проверяет ответы и сохраняет рабочий API при сбое AI."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from threading import Lock, local
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, Field

from app.config import Settings
from app.mock_ai import answer_news_question
from app.schemas import AskResponse, Company, Insight, News, Role, SelfCheckReport, SourceRef

log = logging.getLogger(__name__)
AiMode = Literal["offline", "llm"]
AiStatus = Literal["disabled", "not_checked", "available", "unavailable"]
MAX_RESPONSE_BYTES = 1024 * 1024
CATEGORY_TOPICS = {
    "Финансы и ДКП": "monetary_policy",
    "Финансы и макроэкономика": "monetary_policy",
    "Инфляция и цены": "inflation",
    "Рынок труда и кадры": "labor_market",
    "Регулирование и налоги": "regulation_tax",
    "Регулирование": "regulation_tax",
    "Логистика и внешняя торговля": "logistics_trade",
    "Логистика": "logistics_trade",
    "Отрасль и рынки": "industry_markets",
    "Торговля и ритейл": "consumer_demand",
    "Промышленность и сырьё": "commodities",
    "Прочее": "other",
}


class _Reply(BaseModel):
    request_id: str = Field(min_length=1)
    mode: AiMode


class _Importance(BaseModel):
    news_id: str
    score: int = Field(ge=1, le=10)


class _AgentTrace(BaseModel):
    agent_steps: list[str]
    self_check: SelfCheckReport
    confidence: float = Field(ge=0, le=1)


class _InsightReply(_Reply):
    card: Insight
    importance: _Importance
    traceability: _AgentTrace
    latency_ms: int = Field(ge=0)


class _ChatReply(_Reply):
    answer: str = Field(min_length=1)
    sources: list[SourceRef]
    on_topic: bool


ReplyT = TypeVar("ReplyT", bound=_Reply)


def _company_payload(company: Company) -> dict[str, Any]:
    return {**company.model_dump(mode="json"), "counterparties": []}


def _news_payload(news: News) -> dict[str, Any]:
    payload = news.model_dump(mode="json")
    # Сохраняем известную тему, включая старые названия категорий наших демо-новостей.
    if topic := CATEGORY_TOPICS.get(news.category):
        payload["topic"] = topic
    return payload


def _card_payload(insight: Insight) -> dict[str, Any]:
    # Агентная трассировка — расширение backend. В AI отправляем только его Card.
    return insight.model_dump(
        mode="json", exclude={"agent_steps", "self_check", "confidence", "mode"}
    )


class AiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.ai_service_url.rstrip("/")
        self._lock = Lock()
        self._status: AiStatus = "not_checked" if self.enabled else "disabled"
        self._mode: Literal["mock", "offline", "llm"] = "mock"
        self._request_state = local()

    @property
    def enabled(self) -> bool:
        return self._settings.ai_service_enabled

    @property
    def retry_interval_s(self) -> float:
        return self._settings.ai_service_retry_interval_s

    def runtime_status(self) -> tuple[AiStatus, Literal["mock", "offline", "llm"]]:
        """Результат последнего вызова; /health сам не обращается в сеть."""
        with self._lock:
            return self._status, self._mode

    @property
    def retryable(self) -> bool:
        # Ошибка параллельного чата не должна менять решение фонового worker о повторе.
        return getattr(self._request_state, "retryable", True)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(
            request, timeout=self._settings.ai_service_timeout_s
        ) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("AI response exceeds size limit")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("AI response must be an object")
        return data

    def _failure(self, path: str, exc: Exception) -> None:
        code = type(exc).__name__
        request_id = None
        if isinstance(exc, urllib.error.HTTPError):
            code = f"http_{exc.code}"
            try:
                data = json.loads(exc.read(MAX_RESPONSE_BYTES))
                request_id = data.get("error", {}).get("request_id")
            except (ValueError, AttributeError, OSError):
                pass
        self._request_state.retryable = isinstance(exc, OSError) and (
            not isinstance(exc, urllib.error.HTTPError) or exc.code >= 500 or exc.code == 429
        )
        with self._lock:
            self._status, self._mode = "unavailable", "mock"
        # stdlib logging не принимает error= / detail=. Тексты запросов не логируем.
        log.warning("ai.fallback path=%s code=%s request_id=%s", path, code, request_id)

    def _request(
        self, path: str, payload: dict[str, Any], response_type: type[ReplyT]
    ) -> ReplyT | None:
        if not self.enabled:
            return None
        try:
            response = response_type.model_validate(self._post_json(path, payload))
        except (OSError, ValueError, TypeError) as exc:
            self._failure(path, exc)
            return None
        with self._lock:
            self._status, self._mode = "available", response.mode
        log.info(
            "ai.success path=%s request_id=%s mode=%s latency_ms=%s",
            path,
            response.request_id,
            response.mode,
            getattr(response, "latency_ms", None),
        )
        return response

    def generate_insight(
        self, news: News, company: Company, role: Role
    ) -> tuple[Insight, int, bool] | None:
        response = self._request(
            "/v1/insight",
            {"news": _news_payload(news), "company": _company_payload(company), "role": role.value},
            _InsightReply,
        )
        if response is None:
            return None
        if response.importance.news_id != news.id:
            self._failure("/v1/insight", ValueError("AI returned a different news_id"))
            return None
        insight = response.card.model_copy(
            update={
                "agent_steps": response.traceability.agent_steps,
                "self_check": response.traceability.self_check,
                "confidence": response.traceability.confidence,
                "mode": response.mode,
            }
        )
        return insight, response.importance.score, response.mode != "llm"

    def answer_question(
        self,
        news: News,
        insight: Insight,
        company: Company,
        role: Role,
        question: str,
        *,
        item_id: str,
    ) -> AskResponse:
        response = self._request(
            "/v1/ask",
            {
                "news": _news_payload(news),
                "card": _card_payload(insight),
                "company": _company_payload(company),
                "role": role.value,
                "question": question,
            },
            _ChatReply,
        )
        if response is None:
            return AskResponse(
                feed_item_id=item_id, answer=answer_news_question(news, insight, question)
            )
        return AskResponse(
            feed_item_id=item_id,
            answer=response.answer,
            is_demo=response.mode != "llm",
            mode=response.mode,
            sources=response.sources,
            on_topic=response.on_topic,
            request_id=response.request_id,
        )
