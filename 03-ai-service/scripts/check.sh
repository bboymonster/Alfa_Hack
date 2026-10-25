#!/usr/bin/env bash
# Единственный источник правды о гейтах качества 03-ai-service (= CI).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== ruff check"
uv run ruff check .
echo "== ruff format --check"
uv run ruff format --check .
echo "== mypy"
uv run mypy
echo "== pytest"
uv run pytest -q
echo "== OK"
