"""CLI: демо-инсайт по сэмплам, индексация отчётов, поиск, сбор новостей."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from ai_service.config import get_settings
from ai_service.logging import configure_logging, new_request_id
from ai_service.main import build_context
from ai_service.resources import load_sample
from ai_service.schemas.common import Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.insight import InsightRequest
from ai_service.schemas.news import NewsItem


def _dump(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_insight(args: argparse.Namespace) -> int:
    companies: dict[str, Any] = load_sample("companies")
    news: dict[str, Any] = load_sample("news")
    if args.company not in companies:
        print(f"Неизвестная компания {args.company}; есть: {', '.join(companies)}", file=sys.stderr)
        return 2
    if args.sample not in news:
        print(f"Неизвестный сэмпл {args.sample}; есть: {', '.join(news)}", file=sys.stderr)
        return 2
    settings = get_settings()
    configure_logging(settings)
    ctx = build_context(settings)
    request = InsightRequest(
        news=NewsItem.model_validate(news[args.sample]),
        company=CompanyProfile.model_validate(companies[args.company]),
        role=Role(args.role),
    )
    response = asyncio.run(ctx.insight.run(request, new_request_id()))
    payload = response.model_dump(mode="json")
    _dump(payload if not args.card_only else payload["card"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-service", description="Alfa News Insights AI-service")
    sub = parser.add_subparsers(dest="command", required=True)

    p_insight = sub.add_parser("insight", help="Сгенерировать инсайт по демо-сэмплу")
    p_insight.add_argument(
        "--sample",
        default="key-rate",
        help="ключ новости из resources/sample/news.json (key-rate, inflation, labor, ...)",
    )
    p_insight.add_argument("--company", default="U_1595", help="synthetic_u из sample/companies")
    p_insight.add_argument("--role", default="CFO", choices=[r.value for r in Role])
    p_insight.add_argument("--card-only", action="store_true", help="печатать только card")
    p_insight.set_defaults(func=cmd_insight)

    _register_rag_commands(sub)
    _register_ingest_commands(sub)
    return parser


def _register_rag_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    try:
        from ai_service.rag.cli import register
    except ImportError:  # Phase 4 ещё не реализована
        return
    register(sub)


def _register_ingest_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    try:
        from ai_service.ingest.cli import register
    except ImportError:  # Phase 7 ещё не реализована
        return
    register(sub)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
