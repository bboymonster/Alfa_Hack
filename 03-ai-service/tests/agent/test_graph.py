from collections.abc import Callable
from typing import Any

import pytest

from ai_service.agent.graph import InsightPipeline
from ai_service.config import Settings
from ai_service.datasets.store import NullDatasetStore
from ai_service.errors import ApiError, ErrorCode
from ai_service.llm.generator import OfflineGenerator
from ai_service.rag.retriever import NullRetriever
from ai_service.schemas.common import Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.insight import BankPosition, InsightRequest, SixQuestions
from ai_service.schemas.news import NewsItem
from ai_service.schemas.reports import ReportChunk


def _pipeline(settings: Settings, generator: Any, retriever: Any) -> InsightPipeline:
    return InsightPipeline(generator, retriever, NullDatasetStore(), settings)


async def test_happy_path_cfo_with_corpus(
    settings: Settings,
    offline_generator: OfflineGenerator,
    fake_retriever: Any,
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    pipeline = _pipeline(settings, offline_generator, fake_retriever)
    response = await pipeline.run(
        InsightRequest(news=news_key_rate, company=company_u1595, role=Role.CFO), "req-1"
    )
    six = response.insight
    assert six.q1_what_happened and six.q2_why_matters_for_company and six.q6_basis
    assert six.q3_risks and six.q3_opportunities and six.q4_relevant_actions
    assert six.q5_alfa_bank_position is not None
    assert six.q5_alfa_bank_position.page == 2
    assert six.q5_alfa_bank_position.quote in fake_retriever.chunks[0].text
    assert "CL_PRODUCT_LOA_MARK=1" in response.card.traceability.matched_company_features
    assert response.card.alfa_report_page == 2
    assert response.card.alfa_report_url.endswith("#page=2")
    steps = " ".join(response.traceability.agent_steps)
    for node in (
        "plan:",
        "CompanyProfileTool",
        "AlfaRAGTool",
        "draft:",
        "self_check:",
        "finalize:",
    ):
        assert node in steps
    assert response.traceability.self_check.passed
    assert response.traceability.corpus_available
    assert response.mode == "offline"
    assert response.importance.score >= 8
    assert fake_retriever.queries  # RAG вызывался


async def test_company_without_credit_and_trade(
    settings: Settings,
    offline_generator: OfflineGenerator,
    fake_retriever: Any,
    company_demo_local: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    pipeline = _pipeline(settings, offline_generator, fake_retriever)
    response = await pipeline.run(
        InsightRequest(news=news_key_rate, company=company_demo_local, role=Role.CEO), "req-2"
    )
    features = response.card.traceability.matched_company_features
    assert "CL_PRODUCT_LOA_MARK=0" in features
    assert not any(f.startswith("FTS_FLAG=1") for f in features)
    for risk in response.insight.q3_risks:
        assert "импорт" not in risk.lower()
        assert "обслуживания долга" not in risk.lower()
    assert response.traceability.self_check.passed


async def test_without_corpus_position_is_null(
    settings: Settings,
    offline_generator: OfflineGenerator,
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    pipeline = _pipeline(settings, offline_generator, NullRetriever())
    response = await pipeline.run(
        InsightRequest(news=news_key_rate, company=company_u1595, role=Role.CFO), "req-3"
    )
    assert response.insight.q5_alfa_bank_position is None
    assert response.card.alfa_bank_position is None
    assert response.card.alfa_report_name is None
    assert response.traceability.corpus_available is False
    assert any("corpus unavailable" in s for s in response.traceability.agent_steps)
    assert "не найдено" in response.insight.q6_basis


async def test_offline_is_deterministic(
    settings: Settings,
    offline_generator: OfflineGenerator,
    fake_retriever: Any,
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    pipeline = _pipeline(settings, offline_generator, fake_retriever)
    request = InsightRequest(news=news_key_rate, company=company_u1595, role=Role.CFO)
    first = await pipeline.run(request, "same")
    second = await pipeline.run(request, "same")
    assert first.model_dump(exclude={"latency_ms"}) == second.model_dump(exclude={"latency_ms"})


def _bad_draft(chunk: ReportChunk | None = None) -> SixQuestions:
    position = None
    if chunk is not None:
        position = BankPosition(
            statement="Банк ожидает ставку 12,0% к концу года",  # числа нет во фрагменте
            report_title=chunk.title,
            report_file=chunk.file,
            page=chunk.page,
            chunk_id=chunk.chunk_id,
            quote=chunk.text[:60],
            score=0.5,
        )
    return SixQuestions(
        q1_what_happened="Банк России сохранил ключевую ставку 14,0%.",
        q2_why_matters_for_company=(
            "Компания закупает товары за рубежом, поэтому импортные поставки подорожают. "
            "Выручка 240 млн ₽ делает компанию чувствительной к спросу."
        ),
        q3_risks=[
            "Задержки импортных поставок увеличат товарные запасы.",
            "Снижение спроса со стороны клиентов.",
        ],
        q3_opportunities=["Рост спроса на локальные ИТ-услуги."],
        q4_relevant_actions=["Проверить контракты с клиентами."],
        q5_alfa_bank_position=position,
        q6_basis="Тестовый черновик.",
    )


async def test_contradiction_triggers_redraft_then_sanitize(
    settings: Settings,
    fake_generator_factory: Callable[..., Any],
    fake_retriever: Any,
    chunk_key_rate: ReportChunk,
    company_demo_local: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    generator = fake_generator_factory(
        drafts=[_bad_draft(chunk_key_rate), _bad_draft(chunk_key_rate)]
    )
    pipeline = _pipeline(settings, generator, fake_retriever)
    response = await pipeline.run(
        InsightRequest(news=news_key_rate, company=company_demo_local, role=Role.CEO), "req-5"
    )
    # две попытки черновика, вторая — с замечаниями
    assert len(generator.draft_calls) == 2
    assert generator.draft_calls[1]  # feedback передан
    check = response.traceability.self_check
    assert check.attempts == 2
    assert check.violations
    assert check.fixed
    # зачистка: риск про импорт удалён, предложение про зарубежные закупки удалено, q5 снята
    assert all("импорт" not in r.lower() for r in response.insight.q3_risks)
    assert "за рубежом" not in response.insight.q2_why_matters_for_company
    assert "Выручка 240 млн" in response.insight.q2_why_matters_for_company
    assert response.insight.q5_alfa_bank_position is None
    assert check.passed  # после зачистки нарушений не осталось
    assert response.traceability.confidence < 0.5


async def test_good_llm_draft_passes_first_time(
    settings: Settings,
    fake_generator_factory: Callable[..., Any],
    fake_retriever: Any,
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    generator = fake_generator_factory()  # черновики offline-шаблонов, проверки passed
    pipeline = _pipeline(settings, generator, fake_retriever)
    response = await pipeline.run(
        InsightRequest(news=news_key_rate, company=company_u1595, role=Role.CFO), "req-6"
    )
    assert len(generator.draft_calls) == 1
    assert generator.check_calls == 1
    assert response.mode == "llm"
    assert response.traceability.models["main"] == "fake-main"


async def test_generator_failure_becomes_llm_error(
    settings: Settings,
    fake_generator_factory: Callable[..., Any],
    fake_retriever: Any,
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    generator = fake_generator_factory(fail_draft=RuntimeError("provider down"))
    pipeline = _pipeline(settings, generator, fake_retriever)
    with pytest.raises(ApiError) as excinfo:
        await pipeline.run(
            InsightRequest(news=news_key_rate, company=company_u1595, role=Role.CFO), "req-7"
        )
    assert excinfo.value.code == ErrorCode.LLM_ERROR
    assert excinfo.value.status == 502


async def test_timeout_becomes_llm_timeout(
    settings: Settings,
    fake_generator_factory: Callable[..., Any],
    fake_retriever: Any,
    company_u1595: CompanyProfile,
    news_key_rate: NewsItem,
) -> None:
    slow_settings = settings.model_copy(update={"insight_timeout_s": 0.05})
    generator = fake_generator_factory(delay_s=0.5)
    pipeline = _pipeline(slow_settings, generator, fake_retriever)
    with pytest.raises(ApiError) as excinfo:
        await pipeline.run(
            InsightRequest(news=news_key_rate, company=company_u1595, role=Role.CFO), "req-8"
        )
    assert excinfo.value.code == ErrorCode.LLM_TIMEOUT
    assert excinfo.value.status == 504
