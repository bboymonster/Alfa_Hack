"""Offline-шаблоны инсайта и ответа чата. Детерминированы, уважают признаки профиля,
позицию банка берут только из переданных фрагментов отчётов."""

import re

from ai_service.agent.context import ChatContext, DraftContext
from ai_service.agent.rules import ROLE_FOCUS
from ai_service.schemas.chat import ChatDraft
from ai_service.schemas.common import MatchedFeature, NewsCategory, Role
from ai_service.schemas.company import CompanyProfile
from ai_service.schemas.insight import BankPosition, SixQuestions
from ai_service.schemas.reports import ReportChunk

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def first_sentences(text: str, limit: int = 2, max_chars: int = 600) -> str:
    sentences = _SENTENCE_END.split(text.strip())
    result = " ".join(sentences[:limit]).strip()
    return result[:max_chars].rstrip()


def make_quote(chunk: ReportChunk, max_chars: int = 320) -> str:
    """Дословная подстрока текста фрагмента, обрезанная по границе предложения."""
    text = chunk.text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if boundary > max_chars // 2:
        return cut[: boundary + 1]
    space = cut.rfind(" ")
    return cut[:space] if space > 0 else cut


def bank_position_from_chunk(chunk: ReportChunk) -> BankPosition:
    quote = make_quote(chunk)
    return BankPosition(
        statement=(
            f"В отчёте «{chunk.title}» (стр. {chunk.page}) аналитики Альфа-Банка отмечают: "
            f"«{quote}»"
        ),
        report_title=chunk.title,
        report_file=chunk.file,
        page=chunk.page,
        chunk_id=chunk.chunk_id,
        quote=quote,
        score=chunk.score or 0.0,
    )


def _has(triggers: list[MatchedFeature], feature: str, value: str = "1") -> bool:
    return any(t.feature == feature and t.value == value for t in triggers)


def _why_matters(ctx: DraftContext) -> str:
    company = ctx.company
    topic = ctx.plan.topic
    focus = ROLE_FOCUS[ctx.role]
    parts = [
        f"Для {company.name} (отрасль {company.mainokved_code} — {company.mainokved_name}, "
        f"выручка {company.revenue_human}) новость важна по теме «{_topic_ru(topic)}»."
    ]
    if topic == NewsCategory.MONETARY_POLICY:
        if _has(ctx.triggers, "CL_PRODUCT_LOA_MARK"):
            parts.append(
                "У компании есть кредитные продукты (CL_PRODUCT_LOA_MARK=1): уровень ключевой "
                "ставки напрямую определяет стоимость обслуживания долга и условия "
                "рефинансирования."
            )
        else:
            parts.append(
                "Кредитных продуктов у компании нет (CL_PRODUCT_LOA_MARK=0): прямого эффекта "
                "на долговую нагрузку нет, влияние идёт через стоимость денег у контрагентов "
                "и покупателей."
            )
        if _has(ctx.triggers, "CL_PRODUCT_DEP_MARK"):
            parts.append(
                "Есть депозиты (CL_PRODUCT_DEP_MARK=1): доходность размещения свободной "
                "ликвидности остаётся высокой."
            )
    elif topic == NewsCategory.LOGISTICS_TRADE:
        if _has(ctx.triggers, "FTS_FLAG"):
            countries = f" ({company.fts_country_name})" if company.fts_country_name else ""
            parts.append(
                f"Компания ведёт внешнеторговую деятельность (FTS_FLAG=1{countries}): сроки "
                "и стоимость поставок влияют на оборотный капитал и товарные запасы."
            )
        else:
            parts.append(
                "Внешнеторговой деятельности у компании нет (FTS_FLAG=0): эффект возможен "
                "только косвенно — через поставщиков и логистических партнёров."
            )
    elif topic == NewsCategory.LABOR_MARKET:
        if company.workers_label:
            parts.append(
                f"Численность персонала «{company.workers_label}» делает компанию "
                "чувствительной к росту зарплат и дефициту кадров."
            )
        if _has(ctx.triggers, "CL_PRODUCT_ZPP_MARK"):
            parts.append(
                "Есть зарплатный проект (CL_PRODUCT_ZPP_MARK=1): изменения ФОТ сразу "
                "отражаются на выплатах и страховых взносах."
            )
    elif topic == NewsCategory.INFLATION:
        parts.append(
            "Динамика цен влияет на закупочные цены поставщиков и на переговорную позицию "
            "в контрактах."
        )
        if _has(ctx.triggers, "FTS_FLAG"):
            parts.append("Импортная составляющая (FTS_FLAG=1) усиливает чувствительность к ценам.")
    elif topic == NewsCategory.REGULATION_TAX:
        parts.append(
            "Регуляторные изменения затрагивают отчётность, налоговую нагрузку и порядок "
            "проверок компании."
        )
    elif topic == NewsCategory.COMMODITIES:
        parts.append("Цены на сырьё и материалы определяют себестоимость и маржинальность заказов.")
    elif topic == NewsCategory.CONSUMER_DEMAND:
        parts.append(
            "Потребительский спрос определяет динамику выручки и загрузку торговых и "
            "логистических мощностей."
        )
    else:
        parts.append("Событие затрагивает деловую среду отрасли компании.")
    if ctx.counterparties:
        parts.append(
            f"Среди ключевых контрагентов — {len(ctx.counterparties)} компаний с заметным "
            "платёжным оборотом, на которых событие может отразиться."
        )
    parts.append(f"Фокус {focus.title}: {focus.description}.")
    return " ".join(parts)


def _topic_ru(topic: NewsCategory) -> str:
    from ai_service.schemas.common import CATEGORY_LABELS_RU

    return CATEGORY_LABELS_RU[topic]


def _consequences(ctx: DraftContext) -> tuple[list[str], list[str]]:
    topic = ctx.plan.topic
    t = ctx.triggers
    risks: list[str] = []
    opps: list[str] = []
    if topic == NewsCategory.MONETARY_POLICY:
        if _has(t, "CL_PRODUCT_LOA_MARK"):
            risks.append("Сохранение высокой стоимости обслуживания кредитов и рефинансирования.")
            risks.append("Давление процентных расходов на маржинальность.")
            opps.append("Пересмотр структуры финансирования: факторинг, оборотные лимиты.")
        else:
            risks.append("Удорожание денег у покупателей и контрагентов может замедлить спрос.")
            opps.append(
                "Отсутствие долговой нагрузки — преимущество перед закредитованными конкурентами."
            )
        if _has(t, "CL_PRODUCT_DEP_MARK"):
            opps.append("Фиксация высокой доходности по депозитам и овернайт-размещениям.")
        if _has(t, "FACTORING_MARK"):
            risks.append("Рост стоимости факторингового финансирования дебиторской задолженности.")
    elif topic == NewsCategory.LOGISTICS_TRADE:
        if _has(t, "FTS_FLAG"):
            risks.append("Задержки и удорожание импортных или экспортных поставок.")
            risks.append("Рост потребности в оборотном капитале под товарные запасы.")
            opps.append("Диверсификация маршрутов и поставщиков, пересмотр условий контрактов.")
        else:
            risks.append("Косвенные задержки поставок у поставщиков и логистических партнёров.")
            opps.append("Укрепление позиции за счёт локальной цепочки поставок.")
        if _has(t, "CL_PRODUCT_GAR_MARK"):
            opps.append("Использование банковских гарантий для защиты контрактных обязательств.")
    elif topic == NewsCategory.LABOR_MARKET:
        risks.append("Рост ФОТ и страховых взносов при дефиците кадров.")
        if _has(t, "CL_PRODUCT_ZPP_MARK"):
            risks.append("Расхождения в численности между отчётностью и зарплатным реестром.")
            opps.append("Автоматизация выплат через зарплатный проект для снижения издержек.")
        opps.append("Нематериальная мотивация и удержание ключевых сотрудников.")
    elif topic == NewsCategory.INFLATION:
        risks.append("Попытки поставщиков индексировать цены выше фактической инфляции.")
        if _has(t, "FTS_FLAG"):
            risks.append("Рост импортной составляющей себестоимости.")
        opps.append("Аргументированные переговоры о ценах с опорой на официальные данные.")
    elif topic == NewsCategory.REGULATION_TAX:
        risks.append("Дополнительная нагрузка на бухгалтерию и риск штрафов за несоответствие.")
        opps.append("Ранняя адаптация процессов до вступления изменений в силу.")
    elif topic == NewsCategory.COMMODITIES:
        risks.append("Колебания себестоимости из-за цен на сырьё и материалы.")
        opps.append("Фиксация цен закупок на период стабилизации рынка.")
        if _has(t, "CL_PRODUCT_LEA_MARK"):
            opps.append("Обновление оборудования через лизинг при стабильных ценах.")
    elif topic == NewsCategory.CONSUMER_DEMAND:
        risks.append("Кассовые разрывы при резком росте оборота и расчётов с поставщиками.")
        opps.append("Рост выручки при сохранении спроса; расширение ассортимента.")
    else:
        risks.append("Неопределённость условий ведения бизнеса в отрасли.")
        opps.append("Своевременная реакция на изменение рыночной среды.")
    return risks[:5], opps[:5]


def _actions(ctx: DraftContext) -> list[str]:
    topic = ctx.plan.topic
    role = ctx.role
    t = ctx.triggers
    actions: list[str] = []
    if topic == NewsCategory.MONETARY_POLICY:
        if role == Role.CFO:
            if _has(t, "CL_PRODUCT_LOA_MARK"):
                actions.append(
                    "Пересчитать график обслуживания долга при текущей ставке и оценить "
                    "хеджирование процентного риска."
                )
            actions.append(
                "Разместить свободные остатки в краткосрочные депозиты на период высокой ставки."
            )
        elif role == Role.CEO:
            actions.append(
                "Пересмотреть инвестиционную программу с учётом стоимости заёмных средств."
            )
            actions.append(
                "Оценить устойчивость ключевых покупателей и поставщиков к дорогим деньгам."
            )
        else:
            actions.append(
                "Проверить отражение процентных расходов и условий кредитных договоров в учёте."
            )
    elif topic == NewsCategory.LOGISTICS_TRADE:
        if _has(t, "FTS_FLAG"):
            actions.append("Проверить сроки ближайших поставок и запас по ключевым позициям.")
            actions.append("Согласовать с поставщиками альтернативные маршруты и условия оплаты.")
        else:
            actions.append("Запросить у поставщиков подтверждение сроков и зависимость от импорта.")
    elif topic == NewsCategory.LABOR_MARKET:
        if role == Role.ACCOUNTANT:
            actions.append("Провести сверку штатного расписания и численности в отчётности.")
            actions.append("Пересчитать бюджет ФОТ и страховых взносов до конца года.")
        else:
            actions.append("Пересмотреть систему удержания ключевых сотрудников и план найма.")
    elif topic == NewsCategory.INFLATION:
        actions.append(
            "Использовать официальные данные для отклонения необоснованной индексации цен "
            "поставщиками."
        )
        if role == Role.CFO:
            actions.append("Обновить бюджет закупок с учётом фактической динамики цен.")
    elif topic == NewsCategory.REGULATION_TAX:
        actions.append(
            "Передать материал ответственному за учёт и проверить применимость к компании."
        )
        actions.append("Оценить необходимость изменений в документообороте и сроках отчётности.")
    elif topic == NewsCategory.COMMODITIES:
        actions.append("Зафиксировать цены ключевых закупок на ближайший период.")
        if role == Role.CEO:
            actions.append("Оценить спрос со стороны отраслей-потребителей и загрузку мощностей.")
    elif topic == NewsCategory.CONSUMER_DEMAND:
        actions.append("Подготовить товарные запасы и расчётную инфраструктуру к росту оборота.")
        if role == Role.CFO:
            actions.append("Проверить лимиты эквайринга и платёжный календарь с поставщиками.")
    else:
        actions.append("Обсудить влияние события с профильной командой и проверить первоисточник.")
    return actions[:5]


def offline_draft(ctx: DraftContext) -> SixQuestions:
    risks, opps = _consequences(ctx)
    position = bank_position_from_chunk(ctx.chunks[0]) if ctx.chunks else None
    sources = [f"новость «{ctx.news.title}» ({ctx.news.source})"]
    if position:
        sources.append(f"отчёт «{position.report_title}», стр. {position.page}")
    features = ", ".join(f"{t.feature}={t.value}" for t in ctx.triggers)
    basis = (
        f"Вывод основан на признаках компании ({features}) и источниках: {'; '.join(sources)}. "
        "Режим offline: шаблонная интерпретация без вызова языковой модели."
    )
    if not position:
        basis += " Релевантной позиции Альфа-Банка в корпусе отчётов не найдено."
    return SixQuestions(
        q1_what_happened=first_sentences(f"{ctx.news.title}. {ctx.news.summary_facts}", limit=3),
        q2_why_matters_for_company=_why_matters(ctx),
        q3_risks=risks,
        q3_opportunities=opps,
        q4_relevant_actions=_actions(ctx),
        q5_alfa_bank_position=position,
        q6_basis=basis,
    )


def offline_answer(ctx: ChatContext) -> ChatDraft:
    if not ctx.on_topic_hint:
        return ChatDraft(
            answer=(
                "Я отвечаю только по текущей карточке: новости «"
                f"{ctx.news.title}» и её влиянию на {ctx.company.name}. "
                "Переформулируйте вопрос в этом контексте, и я помогу."
            ),
            used_chunk_ids=[],
            on_topic=False,
        )
    parts = [f"По карточке «{ctx.news.title}»: {first_sentences(ctx.card.why_it_matters, 2)}"]
    if ctx.card.risks:
        parts.append(f"Ключевой риск: {ctx.card.risks[0]}")
    if ctx.card.opportunities:
        parts.append(f"Возможность: {ctx.card.opportunities[0]}")
    used: list[str] = []
    if ctx.chunks:
        chunk = ctx.chunks[0]
        parts.append(
            f"Позиция Альфа-Банка («{chunk.title}», стр. {chunk.page}): «{make_quote(chunk, 240)}»"
        )
        used.append(chunk.chunk_id)
    elif ctx.card.alfa_bank_position:
        parts.append(f"Позиция банка: {first_sentences(ctx.card.alfa_bank_position, 1)}")
    parts.append(f"Рекомендуемый шаг: {ctx.card.action_item}")
    parts.append("Это демо-ответ без языковой модели; он собран из карточки и отчётов банка.")
    return ChatDraft(answer=" ".join(parts), used_chunk_ids=used, on_topic=True)


def describe_profile(company: CompanyProfile) -> str:
    return f"{company.name}, {company.mainokved_name}, выручка {company.revenue_human}"
