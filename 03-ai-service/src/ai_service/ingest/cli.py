"""CLI-команда collect-news."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime

from ai_service.config import get_settings
from ai_service.logging import configure_logging, new_request_id
from ai_service.main import build_context
from ai_service.schemas.ingest import CollectRequest


def cmd_collect_news(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings)
    ctx = build_context(settings)
    request = CollectRequest(
        sources=args.sources.split(",") if args.sources else None,
        since=datetime.fromisoformat(args.since) if args.since else None,
        limit=args.limit,
    )
    response = asyncio.run(ctx.collector.collect(request, new_request_id()))
    if args.json:
        print(json.dumps(response.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0
    for status in response.report.sources:
        mark = "✓" if status.ok else "✗"
        detail = f"{status.fetched} записей" if status.ok else status.error
        print(f"{mark} {status.name}: {detail} ({status.latency_ms} мс)")
    report = response.report
    print(
        f"Возвращено {report.returned}; дубликатов {report.duplicates_dropped}; "
        f"нерелевантных {report.irrelevant_dropped}; старых/исключённых {report.older_dropped}"
    )
    for item in response.items:
        print(f"- [{item.category}] {item.published_at:%d.%m %H:%M} {item.title} — {item.source}")
    return 0


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("collect-news", help="Собрать новости из RSS-источников")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--since", help="ISO-дата: вернуть только новости новее")
    parser.add_argument("--sources", help="имена источников через запятую")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(func=cmd_collect_news)
