"""Клиент 03-ai-service с graceful fallback на ``mock_ai``.

Контракт описан в ``specs/001-ai-service/contracts/backend-integration.md`` и
``specs/001-ai-service/contracts/openapi.yaml``. Любая сетевая ошибка, 5xx или
таймаут возвращают заранее подготовленную заглушку с ``is_demo=True``, поэтому
лента и чат работают даже без AI-сервиса. Зависимостей, кроме stdlib, нет.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

from app.config import Settings
from app.mock_ai import answer_news_question
from app.schemas import Company, Insight, News, Role

log = logging.getLogger(__name__)


def _company_payload(company: Company) -> dict[str, Any]:
    """Минимально необходимые поля ``CompanyProfile`` из openapi.yaml."""
    return {
        "synthetic_u": company.synthetic_u,
        "name": company.name,
        "mainokved_code": company.mainokved_code,
        "mainokved_name": company.mainokved_name,
        "revenue_company": company.revenue_company,
        "cl_product_loa_mark": company.cl_product_loa_mark,
        "fts_flag": company.fts_flag,
        "city": company.city,
        "region": company.region,
        "counterparties": [],
    }


def _news_payload(news: News) -> dict[str, Any]:
    return {
        "id": news.id,
        "title": news.title,
        "summary_facts": news.summary_facts,
        "source": news.source,
        "source_url": news.source_url,
        "published_at": news.published_at.isoformat(),
        "category": news.category,
    }


def _card_payload(insight: Insight) -> dict[str, Any]:
    """``card`` в формате openapi.yaml: публичные поля backend ``Insight``."""
    return {
        "why_it_matters": insight.why_it_matters,
        "risks": insight.risks,
        "opportunities": insight.opportunities,
        "action_item": insight.action_item,
        "alfa_bank_position": insight.alfa_bank_position,
        "alfa_report_name": insight.alfa_report_name,
        "alfa_report_page": insight.alfa_report_page,
        "alfa_report_url": insight.alfa_report_url,
        "traceability": insight.traceability.model_dump(mode="json"),
    }


class AiClient:
    """Единая точка обращения к 03-ai-service. Stateless: весь контекст в запросе."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.ai_service_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return self._settings.ai_service_enabled

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url=f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._settings.ai_service_timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate_insight(
        self, news: News, company: Company, role: Role
    ) -> tuple[Insight, int, bool] | None:
        """Генерирует инсайт через ``POST /v1/insight``.

        Возвращает ``(insight, importance_score, is_demo)`` либо ``None``, когда
        AI-сервис отключён или недоступен (в этом случае вызывающий код оставляет
        уже подготовленную заглушку).
        """
        if not self.enabled:
            return None
        try:
            data = self._post_json(
                "/v1/insight",
                {
                    "news": _news_payload(news),
                    "company": _company_payload(company),
                    "role": role.value,
                },
            )
        except Exception as exc:  # noqa: BLE001 — недоступный AI → оставить заглушку
            log.warning("ai.insight.fallback", error=type(exc).__name__, detail=str(exc))
            return None

        card = data.get("card", {})
        importance = data.get("importance", {})
        trace = data.get("traceability", {})
        insight = Insight.model_validate(
            {
                **card,
                "agent_steps": trace.get("agent_steps"),
                "self_check": trace.get("self_check"),
                "confidence": trace.get("confidence"),
                "mode": data.get("mode"),
            }
        )
        try:
            score = int(importance.get("score", 5))
        except (TypeError, ValueError):
            score = 5
        return insight, max(1, min(10, score)), data.get("mode") != "llm"

    def answer_question(
        self,
        news: News,
        insight: Insight,
        company: Company,
        role: Role,
        question: str,
    ) -> tuple[str, bool]:
        """Отвечает на вопрос через ``POST /v1/ask``. Возвращает ``(answer, is_demo)``."""
        if not self.enabled:
            return answer_news_question(news, insight, question), True
        try:
            data = self._post_json(
                "/v1/ask",
                {
                    "news": _news_payload(news),
                    "card": _card_payload(insight),
                    "company": _company_payload(company),
                    "role": role.value,
                    "question": question,
                },
            )
            return data.get("answer", ""), data.get("mode") != "llm"
        except Exception as exc:  # noqa: BLE001 — любая ошибка AI → честный fallback
            log.warning("ai.ask.fallback", error=type(exc).__name__, detail=str(exc))
            return answer_news_question(news, insight, question), True
