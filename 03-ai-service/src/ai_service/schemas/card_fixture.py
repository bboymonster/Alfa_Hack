"""Пример `Insight` из заглушки backend (02-backend/app/mock_ai.py) — контрактный образец."""

BACKEND_MOCK_INSIGHT: dict[str, object] = {
    "why_it_matters": (
        'Демо: для ООО "Модный Стиль Ритейл" (U_1595) есть кредитные продукты: стоит проверить '
        "условия обслуживания долга. Фокус роли CFO: денежный поток и стоимость финансирования."
    ),
    "risks": ["В демонстрационном сценарии расходы на заёмные средства могут вырасти."],
    "opportunities": ["Заранее оценить влияние на денежный поток и стоимость финансирования."],
    "action_item": (
        "Демо-рекомендация для CFO: Сравнить сценарии денежных потоков и обсудить их с "
        "финансовой командой."
    ),
    "alfa_bank_position": None,
    "alfa_report_name": None,
    "alfa_report_page": None,
    "alfa_report_url": None,
    "traceability": {
        "matched_company_features": ["CL_PRODUCT_LOA_MARK", "REVENUE_COMPANY"],
        "verified_sources": [],
    },
}
