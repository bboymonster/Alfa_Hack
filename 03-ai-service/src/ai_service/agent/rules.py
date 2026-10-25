"""Детерминированные правила: темы новостей, ролевой фокус, триггеры профиля компании.

Значения триггеров берутся строго из профиля (принцип II конституции): модель не
придумывает признаки, она получает готовый список `MatchedFeature`.
"""

from dataclasses import dataclass

from ai_service.schemas.common import MatchedFeature, NewsCategory, Role
from ai_service.schemas.company import CompanyProfile


@dataclass(frozen=True)
class RoleFocus:
    title: str
    description: str
    primary_topics: tuple[NewsCategory, ...]
    secondary_topics: tuple[NewsCategory, ...]
    keywords: tuple[str, ...]


ROLE_FOCUS: dict[Role, RoleFocus] = {
    Role.CEO: RoleFocus(
        title="генерального директора / собственника",
        description="рыночные возможности, экспансия, конкуренты, устойчивость бизнеса",
        primary_topics=(
            NewsCategory.INDUSTRY_MARKETS,
            NewsCategory.CONSUMER_DEMAND,
            NewsCategory.COMMODITIES,
        ),
        secondary_topics=(
            NewsCategory.MONETARY_POLICY,
            NewsCategory.LOGISTICS_TRADE,
            NewsCategory.REGULATION_TAX,
        ),
        keywords=("рынок", "спрос", "конкурент", "экспанси", "доля рынка", "стратеги"),
    ),
    Role.CFO: RoleFocus(
        title="финансового директора / казначея",
        description="маржинальность, кредитная нагрузка, процентные ставки, ликвидность",
        primary_topics=(NewsCategory.MONETARY_POLICY, NewsCategory.INFLATION),
        secondary_topics=(
            NewsCategory.LOGISTICS_TRADE,
            NewsCategory.INDUSTRY_MARKETS,
            NewsCategory.COMMODITIES,
        ),
        keywords=("ставк", "кредит", "ликвидност", "маржин", "долг", "депозит", "факторинг"),
    ),
    Role.ACCOUNTANT: RoleFocus(
        title="главного бухгалтера",
        description="налоговые риски, кадры и ФОТ, отчётность и регуляторные изменения",
        primary_topics=(NewsCategory.LABOR_MARKET, NewsCategory.REGULATION_TAX),
        secondary_topics=(NewsCategory.INFLATION, NewsCategory.MONETARY_POLICY),
        keywords=("налог", "ФОТ", "зарплат", "отчётност", "проверк", "взнос", "НДФЛ"),
    ),
}

# Ключевые «основы» слов в нижнем регистре; совпадение — по вхождению подстроки.
TOPIC_KEYWORDS: dict[NewsCategory, tuple[str, ...]] = {
    NewsCategory.MONETARY_POLICY: (
        "ключевая ставка",
        "ключевой ставк",
        "ставку",
        "банк россии",
        "цб рф",
        "дкп",
        "денежно-кредитн",
        "офз",
        "доходность",
        "облигац",
        "рефинансир",
        "заимствован",
        "кредитован",
    ),
    NewsCategory.INFLATION: (
        "инфляци",
        "индекс потребительских цен",
        "ипц",
        "рост цен",
        "дефляци",
        "удорожан",
        "подорожал",
        "цены на",
    ),
    NewsCategory.LABOR_MARKET: (
        "безработиц",
        "рынок труда",
        "рынка труда",
        "зарплат",
        "заработн",
        "фот",
        "кадров",
        "дефицит кадров",
        "сотрудник",
        "вакансий",
        "занятост",
    ),
    NewsCategory.REGULATION_TAX: (
        "налог",
        "ндс",
        "ндфл",
        "страховые взносы",
        "законопроект",
        "федеральный закон",
        "госдум",
        "регулирован",
        "отчётност",
        "отчетност",
        "фнс",
        "проверк",
        "лицензи",
        "штраф",
    ),
    NewsCategory.LOGISTICS_TRADE: (
        "логистик",
        "поставк",
        "импорт",
        "экспорт",
        "таможн",
        "фтс",
        "пошлин",
        "контейнер",
        "перевозк",
        "санкци",
        "валютн",
        "курс рубля",
        "курс доллара",
    ),
    NewsCategory.INDUSTRY_MARKETS: (
        "отрасл",
        "рынок",
        "производств",
        "ввп",
        "деловая активност",
        "pmi",
        "инвестиц",
        "компани",
        "конкурент",
    ),
    NewsCategory.CONSUMER_DEMAND: (
        "потребительск",
        "потреблени",
        "розничн",
        "ритейл",
        "товарооборот",
        "спрос",
        "покупател",
        "торговл",
        "магазин",
    ),
    NewsCategory.COMMODITIES: (
        "металл",
        "прокат",
        "стал",
        "сырь",
        "нефт",
        "золот",
        "уголь",
        "удобрен",
        "зерн",
        "цены на металл",
    ),
    NewsCategory.OTHER: (),
}

# Приоритет при равном числе совпадений: специфичные темы раньше общих.
_TOPIC_PRIORITY: tuple[NewsCategory, ...] = (
    NewsCategory.MONETARY_POLICY,
    NewsCategory.LABOR_MARKET,
    NewsCategory.REGULATION_TAX,
    NewsCategory.LOGISTICS_TRADE,
    NewsCategory.INFLATION,
    NewsCategory.COMMODITIES,
    NewsCategory.CONSUMER_DEMAND,
    NewsCategory.INDUSTRY_MARKETS,
)

# Отраслевые словари по первым двум цифрам ОКВЭД.
INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "10": ("пищев", "продукт", "продовольств"),
    "11": ("напитк", "алкогол", "пив"),
    "21": ("фарм", "лекарств", "медикамент"),
    "24": ("металлург", "сталь", "прокат", "металл"),
    "25": ("металл", "прокат", "сталь", "металлообработ", "конструкц"),
    "41": ("строительств", "застройщ", "жиль"),
    "42": ("строительств", "инфраструктур", "дорог"),
    "45": ("автомобил", "автодилер", "авторынок"),
    "46": ("оптов", "дистрибь", "импорт", "поставщик"),
    "47": ("розничн", "ритейл", "магазин", "торгов", "одежд", "потребительск"),
    "49": ("перевоз", "логист", "транспорт", "грузов", "автоперевоз"),
    "52": ("логист", "склад", "перевоз", "транспорт"),
    "62": ("it", "программн", "разработк", "софт", "цифров"),
    "68": ("недвижим", "аренд", "коммерческ"),
    "86": ("медицин", "клиник", "здравоохран"),
}

# Уточнения по полному коду ОКВЭД.
INDUSTRY_KEYWORDS_BY_CODE: dict[str, tuple[str, ...]] = {
    "46.34": ("напитк", "алкогол", "вин", "импорт"),
    "46.46": ("фарм", "лекарств", "аптек"),
    "47.71": ("одежд", "fashion", "ритейл одежд", "торговые центр"),
}

MAGNITUDE_KEYWORDS: tuple[str, ...] = (
    "ключевая ставка",
    "ключевую ставку",
    "федеральный закон",
    "законопроект",
    "правительств",
    "минфин",
    "банк россии",
    "санкци",
    "запрет",
    "мораторий",
    "рекорд",
    "историческ",
)


def classify_topic_offline(text: str) -> NewsCategory:
    lowered = text.lower()
    best = NewsCategory.OTHER
    best_hits = 0
    for topic in _TOPIC_PRIORITY:
        hits = sum(lowered.count(keyword) for keyword in TOPIC_KEYWORDS[topic])
        if hits > best_hits:
            best, best_hits = topic, hits
    return best


def extract_keywords(text: str, topic: NewsCategory, limit: int = 8) -> list[str]:
    lowered = text.lower()
    found = [keyword for keyword in TOPIC_KEYWORDS[topic] if keyword in lowered]
    return found[:limit]


def industry_keywords(company: CompanyProfile) -> tuple[str, ...]:
    by_code = INDUSTRY_KEYWORDS_BY_CODE.get(company.mainokved_code, ())
    by_prefix = INDUSTRY_KEYWORDS.get(company.industry_prefix, ())
    return by_code + by_prefix


def industry_match(company: CompanyProfile, text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in industry_keywords(company))


def has_magnitude(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in MAGNITUDE_KEYWORDS)


def _mark(value: bool) -> str:
    return "1" if value else "0"


def _base_features(company: CompanyProfile) -> list[MatchedFeature]:
    segment = "крупный бизнес (≥ 15 млрд ₽)" if company.is_large_business else "средний бизнес"
    return [
        MatchedFeature(
            feature="MAINOKVED_CODE",
            value=company.mainokved_code,
            why=f"отрасль: {company.mainokved_name}",
        ),
        MatchedFeature(
            feature="REVENUE_COMPANY",
            value=company.revenue_human,
            why=f"масштаб: {segment}",
        ),
    ]


def _credit(company: CompanyProfile) -> MatchedFeature:
    if company.cl_product_loa_mark:
        why = "есть кредитные продукты: ставка влияет на стоимость обслуживания долга"
    else:
        why = "нет кредитных продуктов: прямого эффекта на обслуживание долга нет"
    return MatchedFeature(
        feature="CL_PRODUCT_LOA_MARK", value=_mark(company.cl_product_loa_mark), why=why
    )


def _trade(company: CompanyProfile) -> MatchedFeature:
    if company.fts_flag:
        countries = f" ({company.fts_country_name})" if company.fts_country_name else ""
        why = f"есть внешнеторговая деятельность{countries}: зависимость от поставок и курса"
    else:
        why = "нет внешнеторговой деятельности: только косвенное влияние через контрагентов"
    return MatchedFeature(feature="FTS_FLAG", value=_mark(company.fts_flag), why=why)


def _payroll(company: CompanyProfile) -> MatchedFeature:
    if company.cl_product_zpp_mark:
        why = "есть зарплатный проект: изменения ФОТ отражаются на выплатах и взносах"
    else:
        why = "нет зарплатного проекта в банке: учёт ФОТ ведётся вне банка"
    return MatchedFeature(
        feature="CL_PRODUCT_ZPP_MARK", value=_mark(company.cl_product_zpp_mark), why=why
    )


def _workers(company: CompanyProfile) -> MatchedFeature | None:
    label = company.workers_label
    if not label:
        return None
    return MatchedFeature(
        feature="AMOUNT_WORKERS_FNS_GRADATION",
        value=label,
        why="численность персонала определяет чувствительность к рынку труда и ФОТ",
    )


def _optional_mark(
    company: CompanyProfile, feature: str, value: bool, why: str
) -> MatchedFeature | None:
    return MatchedFeature(feature=feature, value=_mark(value), why=why) if value else None


def match_triggers(company: CompanyProfile, topic: NewsCategory) -> list[MatchedFeature]:
    """Сработавшие признаки профиля для темы новости (всегда с фактическими значениями)."""
    features: list[MatchedFeature | None] = list(_base_features(company))
    if topic == NewsCategory.MONETARY_POLICY:
        features += [
            _credit(company),
            _optional_mark(
                company,
                "CL_PRODUCT_DEP_MARK",
                company.cl_product_dep_mark,
                "есть депозиты: ставка определяет доходность размещения ликвидности",
            ),
            _optional_mark(
                company,
                "CL_PRODUCT_LEA_MARK",
                company.cl_product_lea_mark,
                "есть лизинг: ставка влияет на лизинговые платежи",
            ),
            _optional_mark(
                company,
                "FACTORING_MARK",
                company.factoring_mark,
                "используется факторинг: стоимость финансирования дебиторки зависит от ставки",
            ),
        ]
    elif topic == NewsCategory.INFLATION:
        features += [
            _optional_mark(
                company,
                "FTS_FLAG",
                company.fts_flag,
                "есть внешнеторговая деятельность: импортная составляющая себестоимости",
            ),
            _optional_mark(
                company,
                "CL_PRODUCT_DEP_MARK",
                company.cl_product_dep_mark,
                "есть депозиты: реальная доходность размещения зависит от инфляции",
            ),
        ]
    elif topic == NewsCategory.LABOR_MARKET:
        features += [_payroll(company), _workers(company)]
    elif topic == NewsCategory.REGULATION_TAX:
        features += [
            _workers(company),
            _optional_mark(
                company,
                "NEGATIVEMARK",
                company.negativemark,
                "есть негативный признак: повышенное внимание регуляторов и проверок",
            ),
        ]
    elif topic == NewsCategory.LOGISTICS_TRADE:
        features += [
            _trade(company),
            _optional_mark(
                company,
                "CL_PRODUCT_GAR_MARK",
                company.cl_product_gar_mark,
                "есть банковские гарантии: инструменты обеспечения контрактов доступны",
            ),
            _optional_mark(
                company,
                "FACTORING_MARK",
                company.factoring_mark,
                "используется факторинг: можно сгладить кассовые разрывы при задержках поставок",
            ),
        ]
    elif topic == NewsCategory.COMMODITIES:
        features += [
            _optional_mark(
                company,
                "FTS_FLAG",
                company.fts_flag,
                "есть внешнеторговая деятельность: цены на сырьё влияют на закупки",
            ),
            _optional_mark(
                company,
                "CL_PRODUCT_LEA_MARK",
                company.cl_product_lea_mark,
                "есть лизинг оборудования: инвестиционные решения зависят от цен на сырьё",
            ),
        ]
    elif topic == NewsCategory.CONSUMER_DEMAND:
        features += [
            _optional_mark(
                company,
                "CL_PRODUCT_RKO_MARK",
                company.cl_product_rko_mark,
                "есть РКО в банке: расчётная инфраструктура для роста оборота",
            ),
        ]
    if company.eco_mark_label and topic in {
        NewsCategory.INDUSTRY_MARKETS,
        NewsCategory.CONSUMER_DEMAND,
    }:
        features.append(
            MatchedFeature(
                feature="ECO_MARK_LABEL",
                value=company.eco_mark_label,
                why="стадия развития бизнеса определяет реакцию на рыночные изменения",
            )
        )
    return [feature for feature in features if feature is not None]


def positive_product_triggers(triggers: list[MatchedFeature]) -> list[MatchedFeature]:
    """Триггеры по продуктам/признакам со значением «1» (для скоринга)."""
    return [
        trigger
        for trigger in triggers
        if trigger.value == "1" and trigger.feature not in {"MAINOKVED_CODE", "REVENUE_COMPANY"}
    ]
