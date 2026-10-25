"""Eval-гейт инсайтов: golden.jsonl → метрики → сравнение с baseline.json (exit 1 при регрессии).

Запуск: `uv run python evals/run_eval.py [--update-baseline] [--json]`.
Использует текущие настройки (режим offline/llm, реальный индекс, если построен).
Изменение промптов, моделей, retrieval-параметров или корпуса = прогон eval до мержа.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_service.config import get_settings
from ai_service.logging import configure_logging
from ai_service.main import build_context
from ai_service.resources import load_sample
from ai_service.schemas.common import Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.insight import InsightRequest, InsightResponse
from ai_service.schemas.news import NewsItem

EVALS_DIR = Path(__file__).resolve().parent
GOLDEN = EVALS_DIR / "golden.jsonl"
BASELINE = EVALS_DIR / "baseline.json"

# Метрики, падение которых ниже baseline блокирует мерж (абсолютная терпимость).
GATED_METRICS: dict[str, float] = {
    "six_blocks_coverage": 0.0,
    "profile_clean_rate": 0.0,
    "required_features_rate": 0.0,
    "topic_accuracy": 0.0,
    "role_focus_hit": 0.05,
    "source_hit_rate": 0.05,
}


def load_golden() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with GOLDEN.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def evaluate_case(case: dict[str, Any], response: InsightResponse) -> dict[str, Any]:
    six = response.insight
    features = set(response.card.traceability.matched_company_features)
    text_for_role = " ".join(
        [
            six.q2_why_matters_for_company,
            *six.q3_risks,
            *six.q3_opportunities,
            *six.q4_relevant_actions,
        ]
    ).lower()
    six_blocks = all(
        [
            six.q1_what_happened.strip(),
            six.q2_why_matters_for_company.strip(),
            six.q3_risks or six.q3_opportunities,
            six.q4_relevant_actions,
            six.q6_basis.strip(),
            six.q5_alfa_bank_position is not None or "не найдено" in six.q6_basis.lower(),
        ]
    )
    required_ok = all(f in features for f in case.get("required_features", []))
    forbidden_ok = not any(f in features for f in case.get("forbidden_features", []))
    profile_clean = forbidden_ok and response.traceability.self_check.passed
    topic_ok = any(
        step.startswith("plan: тема " + case["topic"]) for step in response.traceability.agent_steps
    )
    role_ok = any(k.lower() in text_for_role for k in case.get("role_keywords", []))
    expect_report = case.get("expect_report")
    source_hit: bool | None = None
    if expect_report and response.traceability.corpus_available:
        rag_steps = " ".join(s for s in response.traceability.agent_steps if "AlfaRAGTool" in s)
        position = six.q5_alfa_bank_position
        source_hit = expect_report.lower() in rag_steps.lower() or (
            position is not None and expect_report.lower() in position.report_title.lower()
        )
    return {
        "id": case["id"],
        "six_blocks": six_blocks,
        "required_ok": required_ok,
        "profile_clean": profile_clean,
        "topic_ok": topic_ok,
        "role_ok": role_ok,
        "source_hit": source_hit,
        "has_position": six.q5_alfa_bank_position is not None,
        "score": response.importance.score,
        "confidence": response.traceability.confidence,
        "latency_ms": response.latency_ms,
        "violations": response.traceability.self_check.violations,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, float]:
    n = len(rows)
    sourced = [r for r in rows if r["source_hit"] is not None]
    return {
        "cases": n,
        "six_blocks_coverage": sum(r["six_blocks"] for r in rows) / n,
        "required_features_rate": sum(r["required_ok"] for r in rows) / n,
        "profile_clean_rate": sum(r["profile_clean"] for r in rows) / n,
        "topic_accuracy": sum(r["topic_ok"] for r in rows) / n,
        "role_focus_hit": sum(r["role_ok"] for r in rows) / n,
        "source_hit_rate": (sum(r["source_hit"] for r in sourced) / len(sourced))
        if sourced
        else -1.0,
        "position_rate": sum(r["has_position"] for r in rows) / n,
        "latency_p95_ms": float(
            statistics.quantiles([r["latency_ms"] for r in rows], n=20)[-1]
            if n >= 2
            else rows[0]["latency_ms"]
        ),
    }


async def run(
    cases: list[dict[str, Any]],
) -> tuple[dict[str, float], list[dict[str, Any]], dict[str, Any]]:
    settings = get_settings()
    configure_logging(settings)
    ctx = build_context(settings)
    companies: dict[str, Any] = load_sample("companies")
    news: dict[str, Any] = load_sample("news")
    rows: list[dict[str, Any]] = []
    for case in cases:
        request = InsightRequest(
            news=NewsItem.model_validate(news[case["news"]]),
            company=CompanyProfile.model_validate(companies[case["company"]]),
            role=Role(case["role"]),
        )
        response = await ctx.insight.run(request, f"eval-{case['id']}")
        rows.append(evaluate_case(case, response))
    meta = {
        "mode": ctx.mode.value,
        "corpus_available": ctx.retriever.available,
        "prompt_version": ctx.generator.prompt_version,
        "models": ctx.generator.models,
        "run_at": datetime.now(UTC).isoformat(),
    }
    return aggregate(rows), rows, meta


def compare(metrics: dict[str, float], baseline: dict[str, Any]) -> list[str]:
    regressions: list[str] = []
    base_metrics: dict[str, float] = baseline.get("metrics", {})
    for name, tolerance in GATED_METRICS.items():
        current = metrics.get(name, -1.0)
        previous = base_metrics.get(name, -1.0)
        if previous < 0 or current < 0:
            continue
        if current + tolerance < previous:
            regressions.append(
                f"{name}: {current:.3f} < baseline {previous:.3f} (−{tolerance:.2f} допуск)"
            )
    return regressions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval инсайтов против golden-набора")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--json", action="store_true", help="вывести метрики JSON")
    args = parser.parse_args(argv)

    cases = load_golden()
    started = time.perf_counter()
    metrics, rows, meta = asyncio.run(run(cases))
    elapsed = time.perf_counter() - started

    if args.json:
        print(
            json.dumps(
                {"metrics": metrics, "meta": meta, "rows": rows}, ensure_ascii=False, indent=1
            )
        )
    else:
        print(
            f"Eval: {metrics['cases']} кейсов, режим {meta['mode']}, корпус "
            f"{'есть' if meta['corpus_available'] else 'нет'}, {elapsed:.1f} с"
        )
        for name, value in metrics.items():
            if name != "cases":
                print(
                    f"  {name:24s} {value:.3f}"
                    if isinstance(value, float)
                    else f"  {name}: {value}"
                )
        failed = [
            r
            for r in rows
            if not (r["six_blocks"] and r["required_ok"] and r["profile_clean"] and r["topic_ok"])
        ]
        for row in failed:
            print(
                f"  ✗ {row['id']}: six={row['six_blocks']} req={row['required_ok']} "
                f"clean={row['profile_clean']} topic={row['topic_ok']} "
                f"violations={row['violations']}"
            )

    if args.update_baseline or not BASELINE.exists():
        BASELINE.write_text(
            json.dumps({"metrics": metrics, "meta": meta}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"Baseline записан: {BASELINE}")
        return 0

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    regressions = compare(metrics, baseline)
    if regressions:
        print("РЕГРЕССИЯ относительно baseline:", file=sys.stderr)
        for item in regressions:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print("Регрессий нет.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
