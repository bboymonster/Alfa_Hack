"""CLI-команды корпуса: index-reports, search."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from ai_service.config import get_settings
from ai_service.logging import configure_logging
from ai_service.rag.qdrant_retriever import build_index_tools


def cmd_index_reports(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings)
    directory = Path(args.dir) if args.dir else settings.articles_dir
    if not directory.exists():
        print(f"Папка с отчётами не найдена: {directory}", file=sys.stderr)
        return 2
    retriever, extractor, catalog = build_index_tools(settings)
    if not extractor.ocr_backend.available():
        print(
            "Внимание: tesseract не найден — страницы без текстового слоя будут пропущены.",
            file=sys.stderr,
        )
    started = time.perf_counter()
    report = retriever.index.index_directory(directory, extractor, catalog, force=args.force)
    for item in report.files:
        if item.ok and item.report:
            doc = item.report
            print(
                f"✓ {item.file}: {doc.pages} стр., {doc.chunks} фрагментов, "
                f"{doc.extractor}, {item.seconds:.1f} с — «{doc.title}»"
            )
        else:
            print(f"✗ {item.file}: {item.error}")
    print(
        f"Итого: отчётов {report.reports}, фрагментов {report.chunks}, "
        f"время {time.perf_counter() - started:.1f} с, индекс {settings.index_dir}"
    )
    return 0 if any(f.ok for f in report.files) else 1


def cmd_search(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings)
    retriever, _, _ = build_index_tools(settings)
    if not retriever.available:
        print("Индекс пуст: сначала выполните `ai-service index-reports`.", file=sys.stderr)
        return 1
    results = retriever.search(args.query, args.k)
    if args.json:
        print(json.dumps([r.model_dump() for r in results], ensure_ascii=False, indent=2))
        return 0
    for rank, chunk in enumerate(results, start=1):
        dense = f"{chunk.dense_score:.2f}" if chunk.dense_score is not None else "-"
        print(f"{rank}. [{chunk.score:.3f} | dense {dense}] {chunk.title} — стр. {chunk.page}")
        print(f"   {chunk.text[:300]}{'…' if len(chunk.text) > 300 else ''}")
    return 0


def register(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    p_index = sub.add_parser("index-reports", help="Проиндексировать PDF-отчёты банка")
    p_index.add_argument("--dir", help="папка с PDF (по умолчанию AI_ARTICLES_DIR)")
    p_index.add_argument("--force", action="store_true", help="игнорировать OCR-кэш")
    p_index.set_defaults(func=cmd_index_reports)

    p_search = sub.add_parser("search", help="Поиск по корпусу отчётов")
    p_search.add_argument("query")
    p_search.add_argument("-k", type=int, default=5)
    p_search.add_argument("--json", action="store_true")
    p_search.set_defaults(func=cmd_search)
