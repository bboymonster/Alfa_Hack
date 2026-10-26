#!/usr/bin/env bash
# Единственный источник правды о гейтах качества 03-ai-service (= CI).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== ruff check"
uv run --frozen ruff check .
echo "== ruff format --check"
uv run --frozen ruff format --check .
echo "== mypy"
uv run --frozen mypy
echo "== pytest"
uv run --frozen pytest -q
echo "== OK"
