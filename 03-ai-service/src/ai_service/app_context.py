"""Контекст приложения: настройки, генератор, ретривер, датасеты, сервисы."""

from dataclasses import dataclass

from ai_service.agent.chat import ChatService
from ai_service.agent.graph import InsightPipeline
from ai_service.config import Settings
from ai_service.datasets.store import Datasets
from ai_service.ingest.collector import NewsCollector
from ai_service.llm.generator import InsightGenerator
from ai_service.rag.retriever import Retriever
from ai_service.schemas.common import Mode
from ai_service.scoring.service import ScoringService


@dataclass
class AppContext:
    settings: Settings
    generator: InsightGenerator
    retriever: Retriever
    datasets: Datasets
    insight: InsightPipeline
    chat: ChatService
    scoring: ScoringService
    collector: NewsCollector

    @property
    def mode(self) -> Mode:
        return self.generator.mode
