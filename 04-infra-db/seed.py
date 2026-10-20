#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04-infra-db: Database Seeding Engine
Заполнение базы данных демонстрационными и эталонными данными:
- Компании из датасета df_Uid_data_hack.csv (с выручкой > 15 млрд руб. и средний бизнес)
- Тестовые учетные записи для жюри (alfa-hack-2026) и пользователей с ролями CEO, CFO, Главбух
- Спаренные карточки «Новость-Инсайт» на базе официальных аналитических отчетов Альфа-Банка
- Платежные связи контрагентов для проверки цепочек поставок

Работает как с PostgreSQL (через DATABASE_URL), так и с SQLite (в качестве локального фолбэка).
"""

import os
import sys
import json
import uuid
import sqlite3
from datetime import datetime, timezone

# Обеспечиваем корректный вывод UTF-8 в консоли Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SCHEMA_SQL_PATH = os.path.join(SCRIPT_DIR, "schema.sql")
SQLITE_DB_PATH = os.path.join(SCRIPT_DIR, "alfa_business.db")

# Загружаем переменные из .env если установлен python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_db_connection():
    """Возвращает соединение с PostgreSQL (если настроено и доступно) либо с SQLite."""
    if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            print(f"[DB] Подключено к PostgreSQL: {DATABASE_URL.split('@')[-1]}")
            return conn, "postgres"
        except Exception as e:
            print(f"[DB] Не удалось подключиться к PostgreSQL ({e}). Переключаемся на SQLite: {SQLITE_DB_PATH}")
    
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    print(f"[DB] Подключено к локальной SQLite БД: {SQLITE_DB_PATH}")
    return conn, "sqlite"


def init_schema(conn, db_type):
    """Инициализирует структуру таблиц из schema.sql."""
    cursor = conn.cursor()
    with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
        sql_script = f.read()
    
    if db_type == "sqlite":
        cursor.executescript(sql_script)
    else:
        cursor.execute(sql_script)
    
    print("[DB] Схема таблиц успешно проверена / создана.")


# --------------------------------------------------------------------------
# Эталонные компании из df_Uid_data_hack.csv
# --------------------------------------------------------------------------
SAMPLE_COMPANIES = [
    {
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
        "amount_workers_spark_gradation": "более 1000",
        "cl_type": "ACTIVE",
        "cl_product_rko_mark": 1.0,
        "cl_product_gar_mark": 1.0,
        "cl_product_loa_mark": 1.0,
        "cl_product_lea_mark": 0.0,
        "cl_product_dep_mark": 1.0,
        "cl_product_zpp_mark": 1.0,
        "fts_flag": 1.0,
        "fts_country_name": "Китай, Турция",
        "factoring_mark": 0.0,
        "revenue_company": 16461800000.0,  # 16.46 млрд руб. (Крупный бизнес > 15 млрд)
        "group_id": "group_fashion_retail",
        "city": "Москва",
        "region": "Москва"
    },
    {
        "synthetic_u": "U_1465",
        "name": 'АО "Премиум Напитки Импорт"',
        "org_type": "АО",
        "okfs_name": "Частная собственность",
        "company_age_years_gradation": "16-25",
        "eco_mark_label": "Крупнейший лидер",
        "mainokved_code": "46.34",
        "mainokved_name": "Торговля оптовая напитками",
        "negativemark": 0.0,
        "amount_workers_fns_gradation": "501-1000",
        "amount_workers_spark_gradation": "501-1000",
        "cl_type": "ACTIVE",
        "cl_product_rko_mark": 1.0,
        "cl_product_gar_mark": 1.0,
        "cl_product_loa_mark": 1.0,
        "cl_product_lea_mark": 1.0,
        "cl_product_dep_mark": 1.0,
        "cl_product_zpp_mark": 1.0,
        "fts_flag": 1.0,
        "fts_country_name": "Италия, Грузия, Чили",
        "factoring_mark": 1.0,
        "revenue_company": 44401190000.0,  # 44.40 млрд руб.
        "group_id": "group_beverage_holding",
        "city": "Москва",
        "region": "Москва"
    },
    {
        "synthetic_u": "U_3263",
        "name": 'ООО "ВолгаТрансЛогистик"',
        "org_type": "ООО",
        "okfs_name": "Частная собственность",
        "company_age_years_gradation": "6-10",
        "eco_mark_label": "Растущий флагман",
        "mainokved_code": "49.41.2",
        "mainokved_name": "Перевозка грузов неспециализированными автотранспортными средствами",
        "negativemark": 0.0,
        "amount_workers_fns_gradation": "501-1000",
        "amount_workers_spark_gradation": "501-1000",
        "cl_type": "ACTIVE",
        "cl_product_rko_mark": 1.0,
        "cl_product_gar_mark": 0.0,
        "cl_product_loa_mark": 0.0,
        "cl_product_lea_mark": 1.0,
        "cl_product_dep_mark": 1.0,
        "cl_product_zpp_mark": 1.0,
        "fts_flag": 1.0,
        "fts_country_name": "Казахстан, Беларусь",
        "factoring_mark": 0.0,
        "revenue_company": 32250370000.0,  # 32.25 млрд руб.
        "group_id": "group_volga_transport",
        "city": "Казань",
        "region": "Республика Татарстан"
    },
    {
        "synthetic_u": "U_80",
        "name": 'ООО "УралМеталлОбработка"',
        "org_type": "ООО",
        "okfs_name": "Частная собственность",
        "company_age_years_gradation": "11-15",
        "eco_mark_label": "Стабильный бизнес",
        "mainokved_code": "25.61",
        "mainokved_name": "Обработка металлов и нанесение покрытий на металлы",
        "negativemark": 0.0,
        "amount_workers_fns_gradation": "101-250",
        "amount_workers_spark_gradation": "101-250",
        "cl_type": "ACTIVE",
        "cl_product_rko_mark": 1.0,
        "cl_product_gar_mark": 0.0,
        "cl_product_loa_mark": 1.0,
        "cl_product_lea_mark": 1.0,
        "cl_product_dep_mark": 0.0,
        "cl_product_zpp_mark": 1.0,
        "fts_flag": 0.0,
        "fts_country_name": "",
        "factoring_mark": 0.0,
        "revenue_company": 1423218000.0,  # 1.42 млрд руб. (Средний бизнес)
        "group_id": "group_ural_metal",
        "city": "Екатеринбург",
        "region": "Свердловская область"
    },
    {
        "synthetic_u": "U_4217",
        "name": 'АО "ФармаТехИнвест"',
        "org_type": "АО",
        "okfs_name": "Частная собственность",
        "company_age_years_gradation": "16-25",
        "eco_mark_label": "Лидер отрасли",
        "mainokved_code": "46.46",
        "mainokved_name": "Торговля оптовая фармацевтической продукцией",
        "negativemark": 0.0,
        "amount_workers_fns_gradation": "251-500",
        "amount_workers_spark_gradation": "251-500",
        "cl_type": "ACTIVE",
        "cl_product_rko_mark": 1.0,
        "cl_product_gar_mark": 1.0,
        "cl_product_loa_mark": 1.0,
        "cl_product_lea_mark": 0.0,
        "cl_product_dep_mark": 1.0,
        "cl_product_zpp_mark": 1.0,
        "fts_flag": 0.0,
        "fts_country_name": "",
        "factoring_mark": 1.0,
        "revenue_company": 16724140000.0,  # 16.72 млрд руб.
        "group_id": "group_pharma_hold",
        "city": "Москва",
        "region": "Москва"
    }
]

# --------------------------------------------------------------------------
# Тестовые пользователи для входа (включая аккаунт жюри)
# --------------------------------------------------------------------------
SAMPLE_USERS = [
    {
        "id": str(uuid.uuid4()),
        "email": "alfa-hack-2026",  # логин жюри из ТЗ
        "hashed_password": "$2b$12$e8YkZfZ0l8nSg1a4nE5PtuN3lP7r9Vw5uB5H3w4X7z9M1k2L3P4q6",  # password123
        "full_name": "Эксперт Жюри Альфа-Банка",
        "role": "CEO",
        "current_company_id": "U_1595"
    },
    {
        "id": str(uuid.uuid4()),
        "email": "ceo@alfabusiness.ru",
        "hashed_password": "$2b$12$e8YkZfZ0l8nSg1a4nE5PtuN3lP7r9Vw5uB5H3w4X7z9M1k2L3P4q6",
        "full_name": "Алексей Смирнов (Генеральный директор)",
        "role": "CEO",
        "current_company_id": "U_1595"
    },
    {
        "id": str(uuid.uuid4()),
        "email": "cfo@alfabusiness.ru",
        "hashed_password": "$2b$12$e8YkZfZ0l8nSg1a4nE5PtuN3lP7r9Vw5uB5H3w4X7z9M1k2L3P4q6",
        "full_name": "Елена Кузнецова (Финансовый директор)",
        "role": "CFO",
        "current_company_id": "U_1595"
    },
    {
        "id": str(uuid.uuid4()),
        "email": "accountant@alfabusiness.ru",
        "hashed_password": "$2b$12$e8YkZfZ0l8nSg1a4nE5PtuN3lP7r9Vw5uB5H3w4X7z9M1k2L3P4q6",
        "full_name": "Ольга Васильева (Главный бухгалтер)",
        "role": "ACCOUNTANT",
        "current_company_id": "U_1595"
    }
]

# --------------------------------------------------------------------------
# Спаренные новости-инсайты (на основе реальных PDF-отчетов Альфа-Банка)
# --------------------------------------------------------------------------
NEWS_INSIGHTS_DATA = [
    {
        "news": {
            "id": str(uuid.uuid4()),
            "title": "Совет директоров Банка России сохранил ключевую ставку на уровне 14,0% годовых",
            "summary_facts": "11 сентября 2026 года совет директоров Банка России принял решение сохранить ключевую ставку на уровне 14,00% годовых. Это первая пауза в цикле смягчения ДКП после последовательных снижений. Регулятор отметил, что текущее инфляционное давление стабилизировалось, однако инфляционные ожидания населения и бизнеса остаются повышенными, а кредитная активность восстанавливается умеренными темпами.",
            "full_text": "Совет директоров Банка России 11 сентября 2026 года сохранил ключевую ставку на уровне 14,00% годовых. В пресс-релизе подчеркивается, что баланс рисков по-прежнему смещен в сторону проинфляционных. Рост внутреннего спроса продолжает опережать возможности расширения предложения. Дальнейшие решения по ставке будут приниматься с учетом фактической динамики инфляции относительно целевого ориентира.",
            "source": "Пресс-служба Банка России",
            "source_url": "https://cbr.ru/press/pr/?file=11092026_key_rate.htm",
            "category": "Финансы и ДКП",
            "published_at": "2026-09-11T13:30:00"
        },
        "insights": [
            {
                "company_id": "U_1595",
                "target_role": "CEO",
                "why_it_matters": "Для крупного ритейла (выручка 16.4 млрд ₽, кредиты CL_PRODUCT_LOA_MARK=1.0) пауза означает закрепление процентных ставок по кредитам на оборотный капитал на уровне 16–17% до 1К27. Быстрого удешевления денег для расширения филиальной сети не предвидится.",
                "risks": [
                    "Сохранение высокой стоимости обслуживания заемных средств (до 85 млн ₽ дополнительных выплат в квартал)",
                    "Сдержанный рост покупательской способности в сегменте премиальной одежды"
                ],
                "opportunities": [
                    "Усиление позиций против закредитованных конкурентов, не имеющих запаса прочности",
                    "Перехват контрактов поставщиков, готовых предоставить товарный кредит"
                ],
                "action_item": "Пересмотреть инвестиционную программу открытия новых флагманских магазинов и диверсифицировать финансирование через факторинг.",
                "recommended_bank_product": "Факторинг без регресса от Альфа-Банка для финансирования товарных запасов",
                "alfa_bank_position": "Центр макроэкономических исследований Альфа-Банка подчеркивает, что риторика регулятора стала жестче. Прогноз средней ставки на 2026 год скорректирован до 14.5%. Пауза является сигналом о длительном удержании жестких условий.",
                "alfa_report_name": "Ключевая ставка ЦБ РФ: ставка без изменения на 14,0%, риторика стала жестче",
                "alfa_report_page": 2,
                "alfa_report_url": "/articles/ALFA-Macro_Insights-Policy_Rate_11Sep.pdf#page=2",
                "traceability": {
                    "matched_company_features": ["CL_PRODUCT_LOA_MARK=1.0", "REVENUE_COMPANY=16.4B", "FTS_FLAG=1.0"],
                    "primary_macro_report": "ALFA-Macro_Insights-Policy_Rate_11Sep.pdf",
                    "agent_steps": ["CheckCreditExposure", "MacroRateMatching", "RetailBenchmarkScan"]
                },
                "importance_score": 9,
                "sentiment": "negative",
                "risk_level": "high"
            },
            {
                "company_id": "U_1595",
                "target_role": "CFO",
                "why_it_matters": "Прямое влияние на коэффициент обслуживания долга (DSCR). Срочные кредиты с плавающей ставкой не снизят платежную нагрузку. Свободную ликвидность имеет смысл разместить в высокодоходные овернайт-депозиты Альфа-Банка под 13.7%.",
                "risks": [
                    "Удорожание рефинансирования облигационного транша в ноябре 2026 года",
                    "Давление на маржинальность EBITDA из-за процентных расходов"
                ],
                "opportunities": [
                    "Фиксация доходности казначейского портфеля на депозитах Альфа-Банка под 13.5–13.8% годовых",
                    "Оптимизация платежного календаря за счет факторинга"
                ],
                "action_item": "Зафиксировать ставку хеджированием процентного риска (IRS) или перевести 400 млн ₽ кассовых остатков в депозитную линейку Альфа-Бизнес.",
                "recommended_bank_product": "Депозит «Овернайт» и «Управляемый процент» Альфа-Банка",
                "alfa_bank_position": "Аналитики банка отмечают, что спред между ставками фондирования и доходностью ОФЗ стабилизировался. Рекомендуется фиксация длинных пассивов.",
                "alfa_report_name": "Бонд Бриф: итоги недели",
                "alfa_report_page": 1,
                "alfa_report_url": "/articles/Бонд_Бриф_14092026.pdf#page=1",
                "traceability": {
                    "matched_company_features": ["CL_PRODUCT_DEP_MARK=1.0", "CL_PRODUCT_LOA_MARK=1.0"],
                    "primary_macro_report": "Бонд_Бриф_14092026.pdf"
                },
                "importance_score": 9,
                "sentiment": "neutral",
                "risk_level": "medium"
            }
        ]
    },
    {
        "news": {
            "id": str(uuid.uuid4()),
            "title": "Недельная инфляция замедлилась до 0,05%, дефляция в плодоовощной группе усиливается",
            "summary_facts": "По данным Росстата за последнюю неделю августа прирост индекса потребительских цен составил всего 0,05% против 0,08% неделей ранее. Годовая инфляция замедлилась до 8,85%. Основным фактором стало сезонное удешевление плодоовощной продукции на 1,3%. В непродовольственном секторе темпы роста цен стабилизировались.",
            "full_text": "За период с 25 по 31 августа 2026 года инфляция замедлилась. Снизились цены на плодоовощную продукцию, бензин автомобильный подорожал на 0,1%. В сегменте услуг зафиксировано замедление удорожания авиаперелетов и туризма.",
            "source": "Федеральная служба государственной статистики (Росстат)",
            "source_url": "https://rosstat.gov.ru/storage/mediabank/inflation_aug26.pdf",
            "category": "Инфляция и цены",
            "published_at": "2026-09-02T19:00:00"
        },
        "insights": [
            {
                "company_id": "U_1595",
                "target_role": "CEO",
                "why_it_matters": "Замедление общей инфляции сопровождается сохранением повышенного спроса на непродовольственные товары. Ваши поставщики тканей и фурнитуры не имеют оснований завышать отпускные цены под предлогом инфляционного шока.",
                "risks": [
                    "Попытки поставщиков навязать индексацию цен выше 0.5% в месяц без реального роста себестоимости"
                ],
                "opportunities": [
                    "Жесткий аргументированный переговорный процесс с контрагентами на базе данных Альфа-Банка",
                    "Экономия до 34 млн ₽ на закупках осенне-зимней коллекции"
                ],
                "action_item": "Использовать выгрузку аналитики Альфа-Банка для отклонения запросов контрагентов на повышение закупочных цен.",
                "recommended_bank_product": "Банковские гарантии исполнения контракта (CL_PRODUCT_GAR_MARK)",
                "alfa_bank_position": "Центр макроэкономических исследований в отчете «Инфляция 25–31 августа: основные выводы» констатирует, что дезинфляционный тренд в продовольствии не транслируется напрямую в базовую инфляцию, однако оптовые цены на сырье стабилизировались.",
                "alfa_report_name": "Инфляция 25–31 августа: основные выводы",
                "alfa_report_page": 1,
                "alfa_report_url": "/articles/Inflation_tracker_02.pdf#page=1",
                "traceability": {
                    "matched_company_features": ["MAINOKVED=47.71", "FTS_FLAG=1.0"],
                    "primary_macro_report": "Inflation_tracker_02.pdf"
                },
                "importance_score": 7,
                "sentiment": "positive",
                "risk_level": "low"
            }
        ]
    },
    {
        "news": {
            "id": str(uuid.uuid4()),
            "title": "Рынок труда 7М26: безработица зафиксирована на историческом минимуме 2,4%, давление на ФОТ сохраняется",
            "summary_facts": "По итогам первых семи месяцев 2026 года уровень безработицы в России удержался на уровне 2,4%. Реальные заработные платы выросли на 8,9% в годовом выражении. Наибольший дефицит кадров наблюдается в промышленности, логистике и ритейле. Компании вынуждены повышать компенсационные пакеты и внедрять автоматизацию.",
            "full_text": "Экономика продолжает функционировать в условиях жесткого дефицита трудовых ресурсов. Коэффициент напряженности на рынке труда составляет 0,3 соискателя на вакансию. Предприятия компенсируют дефицит расширением программ нематериальной мотивации и зарплатными проектами с расширенным страхованием.",
            "source": "Министерство труда и социальной защиты",
            "source_url": "https://mintrud.gov.ru/labour/7m26",
            "category": "Рынок труда и кадры",
            "published_at": "2026-08-28T11:00:00"
        },
        "insights": [
            {
                "company_id": "U_1595",
                "target_role": "ACCOUNTANT",
                "why_it_matters": "Для компании со штатом более 1000 сотрудников (AMOUNT_WORKERS_FNS_GRADATION) рост заработных плат на 8.9% увеличивает налогооблагаемую базу по страховым взносам и НДФЛ. Расхождение между данными ФНС и СПАРК может стать триггером углубленной камеральной проверки.",
                "risks": [
                    "Рост совокупного ФОТ и отчислений на 58 млн ₽ до конца года",
                    "Внимание налоговых органов к расхождению численности сотрудников между отчетами РСВ и СПАРК"
                ],
                "opportunities": [
                    "Снижение издержек на кадровое делопроизводство через цифровой зарплатный проект Альфа-Банка",
                    "Льготные корпоративные программы кредитования сотрудников от банка"
                ],
                "action_item": "Провести сверку штатного расписания и внедрить автоматизированный зарплатный реестр Альфа-Бизнес (CL_PRODUCT_ZPP_MARK).",
                "recommended_bank_product": "Зарплатный проект Альфа-Банка с интеграцией в 1С",
                "alfa_bank_position": "Аналитики Альфа-Банка в отчете «Макростатистика 7М26: данные по рынку труда не подтверждают охлаждения экономики» отмечают, что зарплатная гонка остается ключевым проинфляционным драйвером, ограничивающим рентабельность трудоемких отраслей.",
                "alfa_report_name": "Макростатистика 7М26: данные по рынку труда не подтверждают охлаждения экономики",
                "alfa_report_page": 3,
                "alfa_report_url": "/articles/ALFA-7M26.pdf#page=3",
                "traceability": {
                    "matched_company_features": ["AMOUNT_WORKERS_FNS_GRADATION=>1000", "CL_PRODUCT_ZPP_MARK=1.0"],
                    "primary_macro_report": "ALFA-7M26.pdf"
                },
                "importance_score": 8,
                "sentiment": "negative",
                "risk_level": "medium"
            }
        ]
    },
    {
        "news": {
            "id": str(uuid.uuid4()),
            "title": "Потребительский спрос достиг пика: розничный товарооборот вырос на 5,8% г/г",
            "summary_facts": "По данным обзора потребительской активности, индекс потребительских настроений находится в зоне рекордных значений. Граждане продолжают реализовывать отложенный спрос на товары длительного пользования и одежду. Доля сбережений стабилизировалась, уступая место покупкам качественных отечественных брендов.",
            "full_text": "Потребительский бум подпитывается высокими темпами роста номинальных зарплат и государственными выплатами. Продажи в ритейл-сетях одежды выросли на 7,4% в физическом объеме.",
            "source": "Аналитический центр ритейла",
            "source_url": "https://retail-analytics.ru/consumption-peak-2026",
            "category": "Торговля и ритейл",
            "published_at": "2026-08-20T10:15:00"
        },
        "insights": [
            {
                "company_id": "U_1595",
                "target_role": "CEO",
                "why_it_matters": "Прямой драйвер роста для сети магазинов одежды. Пик потребления совпадает с поступлением осенней коллекции, что позволяет максимизировать выручку без скидочного давления.",
                "risks": [
                    "Риск кассового разрыва при задержках расчетов с логистическими операторами"
                ],
                "opportunities": [
                    "Увеличение средней маржинальности чека на 2.4%",
                    "Захват доли уходящих зарубежных брендов в региональных ТЦ"
                ],
                "action_item": "Увеличить лимит торгового эквайринга Альфа-Банка для бесперебойного приема оплат через СБП и Alfa Pay.",
                "recommended_bank_product": "Торговый эквайринг и СБП для ритейла",
                "alfa_bank_position": "В отчете «Потребление на пике» Центр макроэкономических исследований прогнозирует, что окно сверхактивного спроса продлится еще 2–3 месяца перед сезонной коррекцией.",
                "alfa_report_name": "Потребление на пике",
                "alfa_report_page": 2,
                "alfa_report_url": "/articles/ALFA-consumption.pdf#page=2",
                "traceability": {
                    "matched_company_features": ["MAINOKVED=47.71", "ECO_MARK=Зрелый бизнес"],
                    "primary_macro_report": "ALFA-consumption.pdf"
                },
                "importance_score": 8,
                "sentiment": "positive",
                "risk_level": "low"
            }
        ]
    },
    {
        "news": {
            "id": str(uuid.uuid4()),
            "title": "Рынок металлопроката и стальных конструкций: динамика цен и новые экспортные ограничения",
            "summary_facts": "Цены на горячекатаный прокат на внутреннем рынке стабилизировались в районе 62 000 ₽ за тонну. Эксперты отмечают смещение спроса в сторону инфраструктурного строительства и машиностроения на фоне удорожания импортных сплавов.",
            "full_text": "Металлургические комбинаты сообщают о стабильной загрузке мощностей. Для региональных переработчиков металла ключевым фактором становится доступность оборотных кредитов и лизинга промышленного оборудования.",
            "source": "Металл-Бюллетень",
            "source_url": "https://metalinfo.ru/news/steel-2026",
            "category": "Промышленность и сырье",
            "published_at": "2026-08-15T15:45:00"
        },
        "insights": [
            {
                "company_id": "U_80",
                "target_role": "CEO",
                "why_it_matters": "Для металлообрабатывающего предприятия в Екатеринбурге (выручка 1.42 млрд ₽, кредиты CL_PRODUCT_LOA_MARK=1.0) стабилизация цен на прокат позволяет зафиксировать себестоимость заказов на 6 месяцев вперед.",
                "risks": [
                    "Кассовый разрыв из-за отсрочки платежей от крупных заказчиков из строительного сектора"
                ],
                "opportunities": [
                    "Замещение импортных комплектующих для локальных заводов машиностроения",
                    "Оформление промышленного лизинга на высокоточные станки с субсидированной ставкой"
                ],
                "action_item": "Оформить факторинговую линию Альфа-Банка для финансирования поставок с отсрочкой до 120 дней.",
                "recommended_bank_product": "Лизинг оборудования и факторинг Альфа-Банка",
                "alfa_bank_position": "Аналитики сектора металлургии Альфа-Банка отмечают устойчивость внутреннего спроса на конструкционную сталь при сохранении высоких требований к оборотной ликвидности переработчиков.",
                "alfa_report_name": "Тактический взгляд на 3-й квартал 2026 года: время собирать камни",
                "alfa_report_page": 4,
                "alfa_report_url": "/articles/FI_Strategy_3Q26_22072026.pdf#page=4",
                "traceability": {
                    "matched_company_features": ["MAINOKVED=25.61", "REGION=Свердловская область"],
                    "primary_macro_report": "FI_Strategy_3Q26_22072026.pdf"
                },
                "importance_score": 7,
                "sentiment": "neutral",
                "risk_level": "medium"
            }
        ]
    }
]

# --------------------------------------------------------------------------
# Платежные связи контрагентов (для проверки цепочек поставок)
# --------------------------------------------------------------------------
SAMPLE_PAYMENTS = [
    {"payer_id": "U_1595", "beneficiary_id": "U_80", "pay_amt": 48500000.0, "pay_cnt": 24},
    {"payer_id": "U_1465", "beneficiary_id": "U_3263", "pay_amt": 128900000.0, "pay_cnt": 142},
    {"payer_id": "U_3263", "beneficiary_id": "U_80", "pay_amt": 18200000.0, "pay_cnt": 15},
    {"payer_id": "U_1595", "beneficiary_id": "U_3263", "pay_amt": 74300000.0, "pay_cnt": 89},
    {"payer_id": "U_4217", "beneficiary_id": "U_3263", "pay_amt": 35600000.0, "pay_cnt": 48}
]


def seed_database():
    """Главная функция сидирования."""
    print("=" * 70)
    print(" Alfa News Insights: Старт наполнения базы данных (04-infra-db)")
    print("=" * 70)

    conn, db_type = get_db_connection()
    init_schema(conn, db_type)
    cursor = conn.cursor()

    # 1. Сидирование компаний
    print(f"\n[1/5] Сидирование компаний ({len(SAMPLE_COMPANIES)} шт.)...")
    for comp in SAMPLE_COMPANIES:
        if db_type == "sqlite":
            query = """
            INSERT OR REPLACE INTO companies (
                synthetic_u, name, org_type, okfs_name, company_age_years_gradation,
                eco_mark_label, mainokved_code, mainokved_name, negativemark,
                amount_workers_fns_gradation, amount_workers_spark_gradation,
                cl_type, cl_product_rko_mark, cl_product_gar_mark, cl_product_loa_mark,
                cl_product_lea_mark, cl_product_dep_mark, cl_product_zpp_mark,
                fts_flag, fts_country_name, factoring_mark, revenue_company,
                group_id, city, region
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        else:
            query = """
            INSERT INTO companies (
                synthetic_u, name, org_type, okfs_name, company_age_years_gradation,
                eco_mark_label, mainokved_code, mainokved_name, negativemark,
                amount_workers_fns_gradation, amount_workers_spark_gradation,
                cl_type, cl_product_rko_mark, cl_product_gar_mark, cl_product_loa_mark,
                cl_product_lea_mark, cl_product_dep_mark, cl_product_zpp_mark,
                fts_flag, fts_country_name, factoring_mark, revenue_company,
                group_id, city, region
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (synthetic_u) DO UPDATE SET
                name = EXCLUDED.name,
                revenue_company = EXCLUDED.revenue_company,
                cl_product_loa_mark = EXCLUDED.cl_product_loa_mark
            """
        params = (
            comp["synthetic_u"], comp["name"], comp["org_type"], comp["okfs_name"],
            comp["company_age_years_gradation"], comp["eco_mark_label"], comp["mainokved_code"],
            comp["mainokved_name"], comp["negativemark"], comp["amount_workers_fns_gradation"],
            comp["amount_workers_spark_gradation"], comp["cl_type"], comp["cl_product_rko_mark"],
            comp["cl_product_gar_mark"], comp["cl_product_loa_mark"], comp["cl_product_lea_mark"],
            comp["cl_product_dep_mark"], comp["cl_product_zpp_mark"], comp["fts_flag"],
            comp["fts_country_name"], comp["factoring_mark"], comp["revenue_company"],
            comp["group_id"], comp["city"], comp["region"]
        )
        cursor.execute(query, params)
    print(" -> Компании успешно сохранены.")

    # 2. Сидирование пользователей
    print(f"\n[2/5] Сидирование пользователей ({len(SAMPLE_USERS)} шт.)...")
    for u in SAMPLE_USERS:
        if db_type == "sqlite":
            query = """
            INSERT OR REPLACE INTO users (id, email, hashed_password, full_name, role, current_company_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        else:
            query = """
            INSERT INTO users (id, email, hashed_password, full_name, role, current_company_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                role = EXCLUDED.role,
                current_company_id = EXCLUDED.current_company_id
            """
        params = (u["id"], u["email"], u["hashed_password"], u["full_name"], u["role"], u["current_company_id"])
        cursor.execute(query, params)
    print(" -> Пользователи сохранены (логин жюри: alfa-hack-2026).")

    # 3. Сидирование новостей и инсайтов
    print(f"\n[3/5] Сидирование пар «Новость-Инсайт» ({len(NEWS_INSIGHTS_DATA)} пар)...")
    for item in NEWS_INSIGHTS_DATA:
        n = item["news"]
        if db_type == "sqlite":
            news_query = """
            INSERT OR REPLACE INTO news (id, title, summary_facts, full_text, source, source_url, category, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        else:
            news_query = """
            INSERT INTO news (id, title, summary_facts, full_text, source, source_url, category, published_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title
            """
        cursor.execute(news_query, (
            n["id"], n["title"], n["summary_facts"], n["full_text"],
            n["source"], n["source_url"], n["category"], n["published_at"]
        ))

        # Инсайты к этой новости
        for ins in item["insights"]:
            ins_id = str(uuid.uuid4())
            risks_json = json.dumps(ins["risks"], ensure_ascii=False)
            opps_json = json.dumps(ins["opportunities"], ensure_ascii=False)
            trace_json = json.dumps(ins["traceability"], ensure_ascii=False)

            if db_type == "sqlite":
                ins_query = """
                INSERT OR REPLACE INTO insights (
                    id, news_id, company_id, target_role, why_it_matters, risks, opportunities,
                    action_item, recommended_bank_product, alfa_bank_position,
                    alfa_report_name, alfa_report_page, alfa_report_url,
                    traceability, importance_score, sentiment, risk_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
            else:
                ins_query = """
                INSERT INTO insights (
                    id, news_id, company_id, target_role, why_it_matters, risks, opportunities,
                    action_item, recommended_bank_product, alfa_bank_position,
                    alfa_report_name, alfa_report_page, alfa_report_url,
                    traceability, importance_score, sentiment, risk_level
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            cursor.execute(ins_query, (
                ins_id, n["id"], ins["company_id"], ins["target_role"], ins["why_it_matters"],
                risks_json, opps_json, ins["action_item"], ins["recommended_bank_product"],
                ins["alfa_bank_position"], ins["alfa_report_name"], ins["alfa_report_page"],
                ins["alfa_report_url"], trace_json, ins["importance_score"],
                ins["sentiment"], ins["risk_level"]
            ))
    print(" -> Спаренные карточки «Новость-Инсайт» успешно записаны.")

    # 4. Сидирование платежей
    print(f"\n[4/5] Сидирование платежей контрагентов ({len(SAMPLE_PAYMENTS)} транзакций)...")
    for p in SAMPLE_PAYMENTS:
        pay_id = str(uuid.uuid4())
        if db_type == "sqlite":
            pay_query = "INSERT INTO payments (id, payer_id, beneficiary_id, pay_amt, pay_cnt) VALUES (?, ?, ?, ?, ?)"
        else:
            pay_query = "INSERT INTO payments (id, payer_id, beneficiary_id, pay_amt, pay_cnt) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(pay_query, (pay_id, p["payer_id"], p["beneficiary_id"], p["pay_amt"], p["pay_cnt"]))
    print(" -> Платежные связи сохранены.")

    # 5. Завершение и валидация
    if db_type == "sqlite":
        conn.commit()

    print("\n[5/5] Проверка контрольных счетчиков:")
    for table in ["companies", "users", "news", "insights", "payments"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cursor.fetchone()[0]
        print(f" • Таблица '{table}': {cnt} записей")

    conn.close()
    print("\n" + "=" * 70)
    print(" ✅ База данных успешно инициализирована и наполнена!")
    print("=" * 70)


if __name__ == "__main__":
    seed_database()
