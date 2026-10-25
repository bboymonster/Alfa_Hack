from ai_service.agent.mapping import compute_confidence, to_card
from ai_service.llm.offline import bank_position_from_chunk
from ai_service.schemas.common import MatchedFeature, Mode
from ai_service.schemas.insight import CheckReport, SixQuestions
from ai_service.schemas.news import NewsItem
from ai_service.schemas.reports import ReportChunk

TRIGGERS = [
    MatchedFeature(feature="CL_PRODUCT_LOA_MARK", value="1", why="кредиты"),
    MatchedFeature(feature="REVENUE_COMPANY", value="16,46 млрд ₽", why="масштаб"),
]


def _six(position: object = None) -> SixQuestions:
    return SixQuestions(
        q1_what_happened="Факт.",
        q2_why_matters_for_company="Важно.",
        q3_risks=["Риск 1"],
        q3_opportunities=["Возможность 1"],
        q4_relevant_actions=["Шаг 1", "Шаг 2"],
        q5_alfa_bank_position=position,  # type: ignore[arg-type]
        q6_basis="Основание.",
    )


def test_card_with_position(news_key_rate: NewsItem, chunk_key_rate: ReportChunk) -> None:
    position = bank_position_from_chunk(chunk_key_rate)
    card = to_card(_six(position), news_key_rate, TRIGGERS)
    assert card.action_item == "Шаг 1; Шаг 2"
    assert card.alfa_report_name == chunk_key_rate.title
    assert card.alfa_report_page == 2
    assert card.alfa_report_url == "/articles/ALFA-Macro_Insights-Policy_Rate_11Sep.pdf#page=2"
    assert card.alfa_bank_position is not None and position.quote in card.alfa_bank_position
    assert card.traceability.matched_company_features == [
        "CL_PRODUCT_LOA_MARK=1",
        "REVENUE_COMPANY=16,46 млрд ₽",
    ]
    assert any(", стр. 2" in s for s in card.traceability.verified_sources)
    assert news_key_rate.source_url in card.traceability.verified_sources


def test_card_without_position(news_key_rate: NewsItem) -> None:
    card = to_card(_six(None), news_key_rate, TRIGGERS)
    assert card.alfa_bank_position is None
    assert card.alfa_report_name is None
    assert card.alfa_report_page is None
    assert card.alfa_report_url is None
    assert len(card.traceability.verified_sources) == 1


def test_confidence_bounds(chunk_key_rate: ReportChunk) -> None:
    good = compute_confidence(
        _six(bank_position_from_chunk(chunk_key_rate)),
        TRIGGERS,
        CheckReport(passed=True),
        True,
        Mode.LLM,
    )
    bad = compute_confidence(
        _six(None), [], CheckReport(passed=False, violations=["x"], fixed=["y"]), True, Mode.OFFLINE
    )
    assert 0.0 <= bad < good <= 1.0
