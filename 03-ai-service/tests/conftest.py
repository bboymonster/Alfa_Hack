"""Фикстуры: настройки без ключа, профили и новости из сидов, фейки генератора,
ретривера, датасетов и HTTP-клиент. Сеть и загрузка моделей в тестах запрещены."""

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import Field

from ai_service.agent.context import ChatContext, DraftContext
from ai_service.config import Settings
from ai_service.datasets.store import NullDatasetStore
from ai_service.llm.generator import NewsClassification, OfflineGenerator, plan_offline
from ai_service.main import create_app
from ai_service.rag.retriever import NullRetriever
from ai_service.schemas.chat import ChatDraft
from ai_service.schemas.common import CorpusStatus, Mode, Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.insight import CheckReport, NewsPlan, SixQuestions
from ai_service.schemas.news import NewsItem
from ai_service.schemas.reports import ReportChunk, ReportDocument
from ai_service.schemas.score import AdjustmentList, ImportanceScore

# ----------------------------------------------------------------------------- settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        llm_api_key="",
        articles_dir=tmp_path / "articles",
        datasets_dir=tmp_path / "datasets",
        index_dir=tmp_path / "index",
        log_format="console",
        _env_file=None,  # type: ignore[call-arg]
    )


# ----------------------------------------------------------------------------- companies


def _company(**overrides: Any) -> CompanyProfile:
    base: dict[str, Any] = {
        "synthetic_u": "U_1595",
        "name": 'ООО "Модный Стиль Ритейл"',
        "org_type": "ООО",
        "okfs_name": "Частная собственность",
        "company_age_years_gradation": "11-15",
        "eco_mark_label": "Зрелый бизнес",
        "mainokved_code": "47.71",
        "mainokved_name": "Торговля розничная одеждой в специализированных магазинах",
        "negativemark": 0.0,
        "amount_workers_fns_gradation": "более 1000",
        "cl_type": "CLIENT",
        "cl_product_rko_mark": 1.0,
        "cl_product_gar_mark": 1.0,
        "cl_product_loa_mark": 1.0,
        "cl_product_lea_mark": 0.0,
        "cl_product_dep_mark": 1.0,
        "cl_product_zpp_mark": 1.0,
        "fts_flag": 1.0,
        "fts_country_name": "Китай, Турция",
        "factoring_mark": 0.0,
        "revenue_company": 16_461_800_000.0,
        "city": "Москва",
        "region": "Москва",
    }
    base.update(overrides)
    return CompanyProfile.model_validate(base)


@pytest.fixture
def company_u1595() -> CompanyProfile:
    return _company()


@pytest.fixture
def company_demo_local() -> CompanyProfile:
    return _company(
        synthetic_u="DEMO_LOCAL",
        name='ООО "Демо Локальный Сервис"',
        mainokved_code="62.01",
        mainokved_name="Разработка программного обеспечения",
        amount_workers_fns_gradation="101-250",
        cl_product_gar_mark=0.0,
        cl_product_loa_mark=0.0,
        cl_product_dep_mark=0.0,
        cl_product_zpp_mark=0.0,
        fts_flag=0.0,
        fts_country_name="",
        revenue_company=240_000_000.0,
        city="Казань",
        region="Республика Татарстан",
    )


@pytest.fixture
def company_u80() -> CompanyProfile:
    return _company(
        synthetic_u="U_80",
        name='ООО "УралМеталлОбработка"',
        mainokved_code="25.61",
        mainokved_name="Обработка металлов и нанесение покрытий на металлы",
        amount_workers_fns_gradation="101-250",
        cl_product_gar_mark=0.0,
        cl_product_lea_mark=1.0,
        cl_product_dep_mark=0.0,
        fts_flag=0.0,
        fts_country_name="",
        revenue_company=1_423_218_000.0,
        city="Екатеринбург",
        region="Свердловская область",
    )


# ----------------------------------------------------------------------------- news


def _news(**overrides: Any) -> NewsItem:
    base: dict[str, Any] = {
        "id": "news-key-rate",
        "title": "Совет директоров Банка России сохранил ключевую ставку на уровне 14,0% годовых",
        "summary_facts": (
            "11 сентября 2026 года совет директоров Банка России принял решение сохранить "
            "ключевую ставку на уровне 14,00% годовых. Это первая пауза в цикле смягчения ДКП. "
            "Регулятор отметил, что инфляционные ожидания остаются повышенными."
        ),
        "source": "Пресс-служба Банка России",
        "source_url": "https://cbr.ru/press/pr/?file=11092026_key_rate.htm",
        "published_at": datetime(2026, 9, 11, 13, 30, tzinfo=UTC),
        "category": "Финансы и ДКП",
    }
    base.update(overrides)
    return NewsItem.model_validate(base)


@pytest.fixture
def news_key_rate() -> NewsItem:
    return _news()


@pytest.fixture
def news_logistics() -> NewsItem:
    return _news(
        id="news-logistics",
        title="Сроки доставки контейнеров из Китая выросли на две недели из-за ограничений",
        summary_facts=(
            "Логистические операторы сообщили об увеличении сроков импортных поставок по "
            "морским маршрутам из Китая на 10–14 дней. Ставки фрахта выросли, таможенное "
            "оформление замедлилось."
        ),
        source="Интерфакс",
        source_url="https://www.interfax.ru/business/logistics-2026",
        published_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
        category="Логистика",
    )


@pytest.fixture
def news_labor() -> NewsItem:
    return _news(
        id="news-labor",
        title=(
            "Рынок труда 7М26: безработица на историческом минимуме 2,4%, "
            "давление на ФОТ сохраняется"
        ),
        summary_facts=(
            "По итогам семи месяцев 2026 года уровень безработицы удержался на уровне 2,4%. "
            "Реальные заработные платы выросли на 8,9% в годовом выражении. Дефицит кадров "
            "наблюдается в промышленности, логистике и ритейле."
        ),
        source="Министерство труда",
        source_url="https://mintrud.gov.ru/labour/7m26",
        published_at=datetime(2026, 8, 28, 11, 0, tzinfo=UTC),
        category="Рынок труда и кадры",
    )


@pytest.fixture
def news_steel() -> NewsItem:
    return _news(
        id="news-steel",
        title="Рынок металлопроката: цены на горячекатаный прокат стабилизировались",
        summary_facts=(
            "Цены на горячекатаный прокат на внутреннем рынке стабилизировались около "
            "62 000 ₽ за тонну. Спрос смещается в сторону инфраструктурного строительства и "
            "машиностроения на фоне удорожания импортных сплавов. Металлургические комбинаты "
            "сообщают о стабильной загрузке мощностей."
        ),
        source="Металл-Бюллетень",
        source_url="https://metalinfo.ru/news/steel-2026",
        published_at=datetime(2026, 8, 15, 15, 45, tzinfo=UTC),
        category="Промышленность и сырьё",
    )


# ----------------------------------------------------------------------------- corpus


@pytest.fixture
def chunk_key_rate() -> ReportChunk:
    return ReportChunk(
        chunk_id="rate11sep:2:0",
        report_id="rate11sep",
        title="Ключевая ставка ЦБ РФ: ставка без изменения на 14,0%, риторика стала жестче",
        file="ALFA-Macro_Insights-Policy_Rate_11Sep.pdf",
        page=2,
        index=0,
        text=(
            "ЦБ РФ принял решение оставить ставку неизменной на уровне 14,0%. Риторика "
            "регулятора стала жестче: вариант снижения ставки не рассматривался. Мы "
            "корректируем прогноз средней ставки на 2026 год до 14,5% и ожидаем длительного "
            "удержания жестких условий."
        ),
        score=0.9,
        dense_score=0.78,
    )


class FakeRetriever:
    def __init__(self, chunks: list[ReportChunk]) -> None:
        self.chunks = chunks
        self.queries: list[str] = []

    @property
    def available(self) -> bool:
        return True

    def stats(self) -> CorpusStatus:
        return CorpusStatus(
            available=True,
            reports=len({c.report_id for c in self.chunks}),
            chunks=len(self.chunks),
            indexed_at=datetime(2026, 10, 25, tzinfo=UTC),
        )

    def search(self, query: str, k: int) -> list[ReportChunk]:
        self.queries.append(query)
        return self.chunks[:k]

    def list_reports(self) -> list[ReportDocument]:
        return [
            ReportDocument(
                report_id=chunk.report_id,
                title=chunk.title,
                file=chunk.file,
                pages=4,
                chunks=1,
                indexed_at=datetime(2026, 10, 25, tzinfo=UTC),
                extractor="ocr",
            )
            for chunk in self.chunks
        ]


@pytest.fixture
def fake_retriever(chunk_key_rate: ReportChunk) -> FakeRetriever:
    return FakeRetriever([chunk_key_rate])


@pytest.fixture
def null_retriever() -> NullRetriever:
    return NullRetriever()


# ----------------------------------------------------------------------------- generators


class FakeGenerator:
    """Генератор с заранее заданной очередью черновиков/проверок и учётом вызовов."""

    mode = Mode.LLM
    prompt_version = "test"

    @property
    def models(self) -> dict[str, str]:
        return {"fast": "fake-fast", "main": "fake-main", "checker": "fake-checker"}

    def __init__(
        self,
        drafts: list[SixQuestions] | None = None,
        checks: list[CheckReport] | None = None,
        *,
        fail_draft: Exception | None = None,
        delay_s: float = 0.0,
    ) -> None:
        self.drafts = list(drafts or [])
        self.checks = list(checks or [])
        self.fail_draft = fail_draft
        self.delay_s = delay_s
        self.draft_calls: list[list[str]] = []
        self.check_calls = 0
        self._offline = OfflineGenerator()

    async def plan(self, news: NewsItem) -> NewsPlan:
        return plan_offline(news)

    async def draft(self, ctx: DraftContext, feedback: list[str]) -> SixQuestions:
        self.draft_calls.append(list(feedback))
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        if self.fail_draft:
            raise self.fail_draft
        if self.drafts:
            return self.drafts.pop(0)
        return await self._offline.draft(ctx, feedback)

    async def check(self, ctx: DraftContext, draft: SixQuestions) -> CheckReport:
        self.check_calls += 1
        if self.checks:
            return self.checks.pop(0)
        return CheckReport(passed=True)

    async def answer(self, ctx: ChatContext) -> ChatDraft:
        return await self._offline.answer(ctx)

    async def classify_news(self, items: list[NewsItem]) -> list[NewsClassification]:
        return await self._offline.classify_news(items)

    async def adjust_scores(
        self,
        company: CompanyProfile,
        role: Role,
        items: list[tuple[NewsItem, ImportanceScore]],
    ) -> AdjustmentList:
        return AdjustmentList(adjustments=[])


@pytest.fixture
def offline_generator() -> OfflineGenerator:
    return OfflineGenerator()


@pytest.fixture
def fake_generator_factory() -> Callable[..., FakeGenerator]:
    return FakeGenerator


class FakeStructuredModel(BaseChatModel):
    """Chat-модель, у которой with_structured_output отдаёт фиксированные объекты по очереди."""

    outputs: list[Any] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake-structured"

    def _generate(self, messages: Any, stop: Any = None, run_manager: Any = None, **kw: Any) -> Any:
        raise NotImplementedError("Используется только with_structured_output")

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Runnable[Any, Any]:
        def _run(_: Any) -> Any:
            return self.outputs.pop(0)

        return RunnableLambda(_run)


@pytest.fixture
def fake_structured_model() -> Callable[[list[Any]], FakeStructuredModel]:
    def _make(outputs: list[Any]) -> FakeStructuredModel:
        return FakeStructuredModel(outputs=list(outputs))

    return _make


# ----------------------------------------------------------------------------- app client


@pytest.fixture
async def app_client(
    settings: Settings, offline_generator: OfflineGenerator, fake_retriever: FakeRetriever
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        settings,
        generator=offline_generator,
        retriever=fake_retriever,
        datasets=NullDatasetStore(),
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
def make_client(settings: Settings) -> Callable[..., Any]:
    """Фабрика клиента с произвольными генератором/ретривером/настройками."""

    def _make(**kwargs: Any) -> Any:
        app_settings = kwargs.pop("settings", settings)
        app = create_app(
            app_settings,
            generator=kwargs.pop("generator", OfflineGenerator()),
            retriever=kwargs.pop("retriever", NullRetriever()),
            datasets=kwargs.pop("datasets", NullDatasetStore()),
        )

        class _Client:
            async def __aenter__(self) -> httpx.AsyncClient:
                self._lifespan = app.router.lifespan_context(app)
                await self._lifespan.__aenter__()
                self._client = httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                )
                return self._client

            async def __aexit__(self, *exc: Any) -> None:
                await self._client.aclose()
                await self._lifespan.__aexit__(*exc)

        return _Client()

    return _make
