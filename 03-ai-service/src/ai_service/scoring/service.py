"""Пакетный скоринг важности: правила + опциональная поправка LLM (±1) с объяснением."""

from datetime import UTC, datetime

from ai_service.agent.rules import classify_topic_offline, match_triggers
from ai_service.config import Settings
from ai_service.llm.generator import InsightGenerator
from ai_service.logging import get_logger
from ai_service.schemas.common import Mode
from ai_service.schemas.score import ImportanceScore, ScoreFactor, ScoreRequest, ScoreResponse
from ai_service.scoring.scorer import score_news

log = get_logger(__name__)


class ScoringService:
    def __init__(self, generator: InsightGenerator, settings: Settings) -> None:
        self.generator = generator
        self.settings = settings

    async def score_batch(self, request: ScoreRequest, request_id: str) -> ScoreResponse:
        now = datetime.now(UTC)
        scores: list[ImportanceScore] = []
        for news in request.news:
            topic = news.topic or classify_topic_offline(news.text_for_analysis)
            triggers = match_triggers(request.company, topic)
            scores.append(score_news(request.company, request.role, news, topic, triggers, now=now))

        if self.generator.mode == Mode.LLM and self.settings.score_llm_adjust:
            scores = await self._adjust(request, scores)

        log.info("score.done", items=len(scores), mode=self.generator.mode.value)
        return ScoreResponse(request_id=request_id, mode=self.generator.mode, scores=scores)

    async def _adjust(
        self, request: ScoreRequest, scores: list[ImportanceScore]
    ) -> list[ImportanceScore]:
        pairs = list(zip(request.news, scores, strict=True))
        try:
            result = await self.generator.adjust_scores(request.company, request.role, pairs)
        except Exception as exc:
            log.warning("score.adjust_failed", error=type(exc).__name__)
            return scores
        by_id = {adj.news_id: adj for adj in result.adjustments}
        adjusted: list[ImportanceScore] = []
        for score in scores:
            adj = by_id.get(score.news_id)
            if adj is None or adj.delta == 0:
                adjusted.append(score)
                continue
            new_value = max(1, min(10, score.score + adj.delta))
            factors = [
                *score.factors,
                ScoreFactor(name="llm_adjustment", delta=adj.delta, explanation=adj.reason),
            ]
            adjusted.append(
                ImportanceScore(news_id=score.news_id, score=new_value, factors=factors)
            )
        return adjusted
