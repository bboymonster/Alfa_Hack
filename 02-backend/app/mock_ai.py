"""Временная замена 03-ai-service. Сетевых запросов и вызовов LLM здесь нет."""

from app.schemas import Company, Insight, News, Role, Traceability

ROLE_FOCUS = {
    Role.CEO: "рынки сбыта и устойчивость бизнеса",
    Role.CFO: "денежный поток и стоимость финансирования",
    Role.ACCOUNTANT: "документы, учёт и сроки обязательств",
}


def generate_feed_insight(news_item: News, company_context: Company, role: Role) -> Insight:
    """Сигнатура повторяет договорённость из README AI-команды."""
    if news_item.category == "Финансы и макроэкономика":
        if company_context.cl_product_loa_mark:
            impact = "есть кредитные продукты: стоит проверить условия обслуживания долга"
            risks = ["В демонстрационном сценарии расходы на заёмные средства могут вырасти."]
        else:
            impact = "нет кредитных продуктов: прямой эффект на обслуживание долга не показан"
            risks = ["В демонстрационном сценарии изменение ставок может затронуть контрагентов."]
        features = ["CL_PRODUCT_LOA_MARK", "REVENUE_COMPANY"]
        action = "Сравнить сценарии денежных потоков и обсудить их с финансовой командой."
    elif news_item.category == "Логистика":
        if company_context.fts_flag:
            impact = "есть внешнеторговая деятельность: возможны изменения сроков поставок"
            risks = ["В демонстрационном сценарии импортная поставка может задержаться."]
        else:
            impact = "нет признака внешнеторговой деятельности: проверить косвенные зависимости"
            risks = ["В демонстрационном сценарии задержка возможна у поставщика компании."]
        features = ["FTS_FLAG", "MAINOKVED_CODE"]
        action = "Проверить сроки ближайших поставок и наличие альтернативных поставщиков."
    else:
        impact = "изменение отчётности требует проверки применимости к вашей отрасли"
        risks = ["В демонстрационном сценарии могут потребоваться изменения документов."]
        features = ["MAINOKVED_CODE", "REGION"]
        action = "Передать сообщение ответственному за учёт и проверить первоисточник."

    return Insight(
        why_it_matters=(
            f"Демо: для {company_context.name} ({company_context.synthetic_u}) {impact}. "
            f"Фокус роли {role.value}: {ROLE_FOCUS[role]}."
        ),
        risks=risks,
        opportunities=[f"Заранее оценить влияние на {ROLE_FOCUS[role]} компании."],
        action_item=f"Демо-рекомендация для {role.value}: {action}",
        # Реальных отчётов пока нет: не придумываем позицию банка и ссылки на PDF.
        traceability=Traceability(matched_company_features=features, verified_sources=[]),
    )


def answer_news_question(news_item: News, insight: Insight, user_question: str) -> str:
    return (
        f"Демо-ответ по карточке «{news_item.title}». Ваш вопрос: «{user_question}». "
        f"Контекст: {insight.why_it_matters} Следующий шаг: {insight.action_item} "
        "AI-сервис ещё не подключён; это заранее подготовленная заглушка, а не ответ модели."
    )
