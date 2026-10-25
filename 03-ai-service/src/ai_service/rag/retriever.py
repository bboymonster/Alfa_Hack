"""Протокол ретривера и NullRetriever (корпус не подключён). Реализация на Qdrant —
`ai_service.rag.qdrant_retriever` (создаётся фабрикой `build_retriever`)."""

from typing import Protocol

from ai_service.config import Settings
from ai_service.logging import get_logger
from ai_service.schemas.common import CorpusStatus
from ai_service.schemas.reports import ReportChunk, ReportDocument

log = get_logger(__name__)


class Retriever(Protocol):
    @property
    def available(self) -> bool: ...

    def stats(self) -> CorpusStatus: ...

    def search(self, query: str, k: int) -> list[ReportChunk]: ...

    def list_reports(self) -> list[ReportDocument]: ...


class NullRetriever:
    """Корпус отсутствует: поиск всегда пуст, сервис продолжает работать."""

    @property
    def available(self) -> bool:
        return False

    def stats(self) -> CorpusStatus:
        return CorpusStatus(available=False)

    def search(self, query: str, k: int) -> list[ReportChunk]:
        return []

    def list_reports(self) -> list[ReportDocument]:
        return []


def build_retriever(settings: Settings) -> Retriever:
    """Qdrant-ретривер, если индекс существует; иначе NullRetriever."""
    if not settings.manifest_path.exists():
        log.info("retriever.null", reason="index not found", index_dir=str(settings.index_dir))
        return NullRetriever()
    try:
        from ai_service.rag.qdrant_retriever import QdrantHybridRetriever

        retriever: Retriever = QdrantHybridRetriever.from_settings(settings)
        return retriever
    except Exception as exc:
        log.warning("retriever.null", reason="failed to open index", error=type(exc).__name__)
        return NullRetriever()
