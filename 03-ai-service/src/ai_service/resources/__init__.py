"""Ресурсы пакета: каталог отчётов и демо-сэмплы (компании и новости из сидов 04-infra-db)."""

import json
from pathlib import Path
from typing import Any

RESOURCES_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = RESOURCES_DIR / "sample"


def load_sample(name: str) -> Any:
    with (SAMPLE_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        return json.load(handle)
