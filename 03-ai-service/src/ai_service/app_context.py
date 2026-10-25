"""Контекст приложения: настройки, генератор, ретривер, датасеты."""

from dataclasses import dataclass

from ai_service.config import Settings
from ai_service.datasets.store import Datasets
from ai_service.llm.generator import InsightGenerator
from ai_service.rag.retriever import Retriever
from ai_service.schemas.common import Mode


@dataclass
class AppContext:
    settings: Settings
    generator: InsightGenerator
    retriever: Retriever
    datasets: Datasets

    @property
    def mode(self) -> Mode:
        return self.generator.mode
