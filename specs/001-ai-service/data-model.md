# Data Model: AI-Service «Новость → Инсайт»

Все сущности — Pydantic v2 модели в `src/ai_service/schemas/`. Сервис stateless: ничего
из перечисленного не хранится, кроме индекса корпуса (`ReportDocument`, `ReportChunk`).

## Перечисления (`schemas/common.py`)

- **Role**: `CEO | CFO | ACCOUNTANT` (совпадает с backend).
- **Mode**: `llm | offline` — как получен ответ.
- **NewsCategory** (фиксированный список, согласуется с backend):
  `monetary_policy` (финансы и ДКП), `inflation` (инфляция и цены), `labor_market`
  (рынок труда и кадры), `regulation_tax` (регулирование и налоги), `logistics_trade`
  (логистика и внешняя торговля), `industry_markets` (отрасль и рынки), `consumer_demand`
  (потребительский спрос), `commodities` (сырьё и металлы), `other`.
  Поле `category` у новости от backend — свободная строка; сервис хранит её как есть и
  дополнительно вычисляет `topic: NewsCategory`.

## NewsItem (`schemas/news.py`)

| Поле | Тип | Правила |
|---|---|---|
| id | str | идентификатор backend; для собранных новостей — uuid5 от URL |
| title | str | 1–500 символов |
| summary_facts | str | 1–4000, факты без оценок |
| full_text | str \| None | ≤ 20000, усечение с пометкой в traceability |
| source | str | название источника |
| source_url | HttpUrl \| None | |
| published_at | datetime (tz-aware) | |
| category | str | строка backend |
| topic | NewsCategory \| None | вычисляется сервисом, может прийти от backend |

## CompanyProfile (`schemas/company.py`)

Поля датасета `df_Uid_data_hack.csv`, имена в snake_case как в backend `Company`;
маркеры приходят как `bool` (backend) или `0.0/1.0` (датасет) — валидатор приводит к bool.

| Поле | Тип | Источник CSV |
|---|---|---|
| synthetic_u | str | SYNTHETIC_U |
| name | str | нет в CSV; backend |
| org_type, okfs_name | str \| None | ORG_TYPE, OKFS_NAME |
| company_age_years_gradation | str \| None | COMPANY_AGE_YEARS_GRADATION |
| eco_mark_label | str \| None | ECO_MARK_LABEL |
| mainokved_code, mainokved_name | str | MAINOKVED_CODE/NAME |
| negativemark | bool | NEGATIVEMARK |
| amount_workers_fns_gradation, amount_workers_spark_gradation | str \| None | |
| cl_type | str \| None | CL_TYPE (CLIENT/PROSPECT/CLOSE_CLIENT) |
| cl_product_rko_mark, cl_product_gar_mark, cl_product_loa_mark, cl_product_lea_mark, cl_product_dep_mark, cl_product_zpp_mark | bool | CL_PRODUCT_*_MARK |
| fts_flag | bool | FTS_FLAG |
| fts_country_name | str \| None | FTS_COUNTRY_NAME |
| factoring_mark | bool | FACTORING_MARK |
| revenue_company | float ≥ 0 | REVENUE_COMPANY (рубли) |
| group_id | str \| None | |
| city, region | str \| None | |
| counterparties | list[Counterparty] | опционально, от backend или `CounterpartyTool` |

**Counterparty**: `synthetic_u: str`, `direction: payer | beneficiary` (относительно
компании), `pay_amt: float`, `pay_cnt: int`, `mainokved_code/ name: str | None`.

Производные признаки (вычисляются, не хранятся): `is_large_business = revenue ≥ 15 млрд`,
`has_credit = loa`, `has_import_export = fts_flag`, `has_payroll = zpp`, `industry_prefix`
(первые 2 цифры ОКВЭД).

## Инсайт (`schemas/insight.py`)

**SixQuestions** — внутренняя модель, выход генератора:

| Поле | Тип | Требование |
|---|---|---|
| q1_what_happened | str | только факты новости |
| q2_why_matters_for_company | str | ссылается ≥ 1 признак из `matched_triggers` |
| q3_risks | list[str] 0–5 | |
| q3_opportunities | list[str] 0–5 | |
| q4_relevant_actions | list[str] 1–5 | конкретные шаги |
| q5_alfa_bank_position | BankPosition \| None | только при наличии фрагмента |
| q6_basis | str | краткое объяснение, на чём основан вывод |

**BankPosition**: `statement: str`, `report_title: str`, `report_file: str`, `page: int ≥ 1`,
`chunk_id: str`, `quote: str` (≤ 400 символов, дословно из фрагмента), `score: float`.

**Traceability**:

| Поле | Тип |
|---|---|
| matched_company_features | list[MatchedFeature] — `feature: str` (имя поля датасета), `value: str`, `why: str` |
| verified_sources | list[SourceRef] — `kind: news | report`, `title`, `url | None`, `page | None`, `chunk_id | None` |
| agent_steps | list[str] — имена пройденных нод и инструментов с результатом |
| self_check | CheckReport — `passed: bool`, `violations: list[str]`, `attempts: int`, `fixed: list[str]` |
| confidence | float 0–1 |
| corpus_available | bool |
| truncated_inputs | list[str] |
| mode | Mode |
| prompt_version | str |
| models | dict[str, str] — слот → id модели (пусто в offline) |

**Card** — публичный формат backend `Insight` (неизменяемый контракт):
`why_it_matters: str`, `risks: list[str]`, `opportunities: list[str]`, `action_item: str`,
`alfa_bank_position: str | None`, `alfa_report_name: str | None`, `alfa_report_page: int | None`,
`alfa_report_url: str | None`, `traceability: {matched_company_features: list[str],
verified_sources: list[str]}`.

Маппинг (`agent/mapping.py`): `why_it_matters = q2 (+ q1 первым предложением, если q2 не
содержит факта)`, `risks = q3_risks`, `opportunities = q3_opportunities`,
`action_item = "; ".join(q4)`, `alfa_bank_position = q5.statement`,
`alfa_report_name = q5.report_title`, `alfa_report_page = q5.page`,
`alfa_report_url = "/articles/{file}#page={page}"`,
`traceability.matched_company_features = [f"{feature}={value}"]`,
`traceability.verified_sources = ["{title}, стр. {page}", news.source_url]`.

**InsightResponse**: `request_id`, `mode`, `insight: SixQuestions`, `card: Card`,
`importance: ImportanceScore`, `traceability: Traceability`, `latency_ms: int`.

## Чат (`schemas/chat.py`)

- **AskRequest**: `news: NewsItem`, `card: Card`, `company: CompanyProfile`, `role: Role`,
  `question: str` (strip, 1–2000).
- **AskResponse**: `request_id`, `mode`, `answer: str`, `sources: list[SourceRef]`,
  `on_topic: bool`.

## Скоринг (`schemas/score.py`)

- **ScoreRequest**: `company`, `role`, `news: list[NewsItem]` (1–200).
- **ImportanceScore**: `news_id: str`, `score: int 1–10`, `factors: list[ScoreFactor]` —
  `name: str`, `delta: int`, `explanation: str`.
- **ScoreResponse**: `request_id`, `mode`, `scores: list[ImportanceScore]` (порядок входа).

## Корпус отчётов (`schemas/reports.py`)

- **ReportDocument**: `report_id: str` (sha256 файла[:16]), `title: str`, `file: str`,
  `pages: int`, `chunks: int`, `indexed_at: datetime`, `extractor: str` (`text | ocr`).
- **ReportChunk**: `chunk_id: str` (`{report_id}:{page}:{index}`), `report_id`, `title`,
  `file`, `page: int`, `index: int`, `text: str`, `score: float | None`,
  `dense_score: float | None`.
- **SearchResponse**: `query`, `results: list[ReportChunk]`, `corpus_available: bool`.
- Хранение: Qdrant-коллекция `alfa_reports` с именованными векторами `dense` (384,
  cosine) и `sparse` (`bm25`, IDF modifier); payload = поля чанка. Переиндексация: удалить
  точки по `report_id`, записать новые; `ReportDocument` — в payload служебной точки или
  в `data/index/manifest.json`.

## Сбор новостей (`schemas/ingest.py`)

- **NewsSource**: `name: str`, `url: HttpUrl`, `kind: rss`, `enabled: bool`,
  `default_category: NewsCategory | None`.
- **CollectRequest**: `sources: list[str] | None` (имена, по умолчанию все включённые),
  `since: datetime | None`, `exclude_urls: list[HttpUrl]` (≤ 5000), `limit: int 1–500 = 100`.
- **SourceStatus**: `name`, `ok: bool`, `fetched: int`, `error: str | None`,
  `latency_ms: int`.
- **CollectResponse**: `request_id`, `mode`, `items: list[NewsItem]`,
  `report: {sources: list[SourceStatus], returned, duplicates_dropped, irrelevant_dropped, older_dropped}`.

## Состояние графа (`agent/state.py`)

`InsightState` (TypedDict): `request_id`, `news`, `company`, `role`, `plan: NewsPlan | None`
(`topic`, `keywords`, `queries`), `matched_triggers: list[MatchedFeature]`,
`counterparties: list[Counterparty]`, `chunks: list[ReportChunk]`, `corpus_available: bool`,
`draft: SixQuestions | None`, `check: CheckReport | None`, `attempts: int`,
`steps: Annotated[list[str], operator.add]`, `errors: Annotated[list[str], operator.add]`,
`truncated: list[str]`, `result: InsightResponse | None`.

## Ошибки (`errors.py`)

`ErrorResponse = {"error": {"code": str, "message": str, "request_id": str}}`;
коды: `validation_error` (422), `llm_timeout` (504), `llm_error` (502), `corpus_error` (503),
`internal_error` (500).
