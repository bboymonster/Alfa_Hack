# Tasks: AI-Service «Новость → Инсайт»

**Input**: Design documents from `specs/001-ai-service/` (plan.md, spec.md, research.md,
data-model.md, contracts/openapi.yaml, contracts/backend-integration.md, quickstart.md)

**Tests**: обязательны (конституция, принцип V): каждая фаза содержит тесты, тесты
пишутся до реализации и должны падать, затем проходить. Все тесты без сети и без
скачивания моделей.

**Organization**: фазы по user story; каждая завершается независимо проверяемым чекпоинтом.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно делать параллельно (разные файлы, нет зависимостей)
- **[Story]**: US1 инсайт, US2 корпус, US3 чат, US4 скоринг, US5 сбор новостей
- Все пути — от `03-ai-service/`, если не указано иное

## Phase 1: Setup

- [ ] T001 Создать uv-проект: `pyproject.toml` (name `alfa-ai-service`, пакет `src/ai_service`, `requires-python >=3.12`, deps: fastapi, uvicorn, pydantic, pydantic-settings, structlog, langgraph, langchain, langchain-openai, qdrant-client, fastembed, pymupdf, pytesseract, pillow, feedparser, httpx, pandas, pyyaml; dev: ruff, mypy, pytest, pytest-asyncio, pandas-stubs, types-PyYAML, types-requests; `[tool.ruff]` line-length 100, select E,F,I,UP,B,ASYNC,RUF,SIM, ignore RUF001-003; `[tool.mypy] strict=true, ignore_missing_imports=true`; `[tool.pytest.ini_options] asyncio_mode="auto"`, testpaths; `[project.scripts] ai-service = "ai_service.cli:main"`), `uv sync`, удалить `03-ai-service/.gitkeep`
- [ ] T002 [P] Создать `scripts/check.sh` (set -euo pipefail; `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest -q`) и сделать исполняемым
- [ ] T003 [P] Создать `.env.example` со всеми `AI_*` переменными (LLM base_url/api_key/model_main/model_fast/model_checker, timeouts, retries, max_tokens, articles/datasets/index dirs, embed model names, rag top_k/min_score, news sources on/off, log level) с комментариями и TODO про id моделей провайдера
- [ ] T004 [P] Создать `data/reports_catalog.yaml` (9 файлов → официальные названия из THIRD_PARTY_NOTICES.md и OCR-заголовков) и `data/sample/.gitkeep`; проверить, что `data/articles`, `data/datasets`, `data/index` игнорируются корневым `.gitignore`

## Phase 2: Foundational (блокирует все user stories)

- [ ] T005 `src/ai_service/config.py`: `Settings(BaseSettings)` с `env_prefix="AI_"`, `env_file=(.env корня репо, .env сервиса)`, поля из data-model/research (llm_*, timeouts, dirs как `Path`, embed_dense_model, embed_sparse_language, rag_top_k, rag_min_score, news_sources_enabled, prompt_version), свойство `llm_enabled = bool(api_key)`, `get_settings()` с lru_cache и сбросом в тестах
- [ ] T006 [P] `src/ai_service/logging.py`: настройка structlog (JSON в проде, консоль при `AI_LOG_FORMAT=console`), `bind_request_id` middleware (заголовок `X-Request-ID` или uuid4), помощник `log_llm_call(slot, model, input_tokens, output_tokens, latency_ms)`
- [ ] T007 [P] `src/ai_service/errors.py`: `ApiError(code, status, message, details)`, коды из data-model, exception handlers FastAPI (включая `RequestValidationError` → `validation_error`, неожиданные → `internal_error` с request_id в теле)
- [ ] T008 [P] `src/ai_service/schemas/common.py` (Role, Mode, NewsCategory + словарь `CATEGORY_LABELS_RU`, ErrorResponse), `schemas/news.py` (NewsItem с валидацией длин, tz-aware datetime), `schemas/company.py` (CompanyProfile с валидатором `0.0/1.0 → bool`, Counterparty, производные свойства `is_large_business`, `industry_prefix`)
- [ ] T009 [P] `src/ai_service/schemas/insight.py` (BankPosition, SixQuestions, MatchedFeature, SourceRef, CheckReport, Traceability, Card с вложенной `CardTraceability`, InsightOptions, InsightRequest, InsightResponse), `schemas/score.py` (ScoreFactor, ImportanceScore, ScoreRequest, ScoreResponse), `schemas/chat.py` (AskRequest, AskResponse), `schemas/reports.py` (ReportDocument, ReportChunk, SearchResponse), `schemas/ingest.py` (NewsSource, CollectRequest, SourceStatus, CollectReport, CollectResponse)
- [ ] T010 [P] `tests/unit/test_schemas.py`: маркеры `1.0`/`0.0`/`true` → bool; revenue < 0 отклоняется; question длиной 2001 отклоняется; `Card` принимает JSON из `02-backend/app/schemas.py`-формата (фикстура из mock_ai); NewsItem без tz отклоняется
- [ ] T011 `src/ai_service/agent/rules.py`: `ROLE_FOCUS` (CEO/CFO/ACCOUNTANT: описание фокуса, ключевые слова), `TOPIC_KEYWORDS` (NewsCategory → словарь русских ключевых слов/лемм-префиксов), `classify_topic_offline(text) -> NewsCategory`, `TRIGGER_RULES` (тема → список правил: признак профиля, условие, пояснение), `match_triggers(company, topic) -> list[MatchedFeature]` (значения строго из профиля: `CL_PRODUCT_LOA_MARK=1`, `REVENUE_COMPANY=16.46 млрд`, `MAINOKVED_CODE=47.71`, `FTS_FLAG=0` и т.д.; совпадение отрасли по префиксу ОКВЭД и словарю отраслевых тем), `industry_match(company, news) -> bool`
- [ ] T012 [P] `tests/unit/test_rules.py`: ставка + loa=1 → триггер LOA; ставка + loa=0 → нет LOA, но есть REVENUE/отрасль; логистика + fts=0 → триггер `FTS_FLAG=0` с пояснением «нет внешнеторговой деятельности»; рынок труда + zpp=1 → ZPP и численность; классификация 6 образцов текстов по темам
- [ ] T013 `src/ai_service/scoring/scorer.py`: `score_news(company, role, news, topic, triggers, now) -> ImportanceScore` по правилам research R7 (база 5, отрасль +2, триггеры +1 до +3, ролевой фокус +1/+2 по `ROLE_FOCUS[role].topics`, давность > 30 дней −1, масштаб события по словарю +1, клип 1–10), детерминированно, факторы с `delta` и `explanation`
- [ ] T014 [P] `tests/unit/test_scorer.py`: сценарии US4 (рынок труда ACCOUNTANT > CEO; металлопрокат: металлообработчик > ритейлер; старая новость ниже свежей; клип в [1,10]; детерминизм)
- [ ] T015 `src/ai_service/llm/provider.py`: `ModelSlots` (fast/main/checker: `BaseChatModel`), `build_model_slots(settings) -> ModelSlots | None` через `ChatOpenAI(base_url, api_key, model, timeout, max_retries=0, max_tokens, temperature=0)` (ретраи делает LangGraph `RetryPolicy`), `None` при пустом ключе; `llm/callbacks.py`: `BaseCallbackHandler`, пишущий `llm.call` через `log_llm_call` из `response.llm_output`/`usage_metadata`, без текстов
- [ ] T016 `src/ai_service/llm/generator.py`: `InsightGenerator` Protocol (`async plan(news) -> NewsPlan`, `async draft(ctx: DraftContext, feedback: list[str]) -> SixQuestions`, `async check(ctx, draft) -> CheckReport`, `async answer(ctx: ChatContext) -> ChatDraft`, `mode`, `models`), `OfflineGenerator` — детерминированные русские шаблоны по теме, роли и триггерам (q5 только из лучшего `ReportChunk` с дословной цитатой; при пустом корпусе `None`), `LLMGenerator` — `with_structured_output(SixQuestions/NewsPlan/CheckReport/ChatDraft)` на соответствующих слотах, промпты из `prompts/`
- [ ] T017 [P] `src/ai_service/prompts/insight.py`, `prompts/check.py`, `prompts/chat.py`, `prompts/classify.py`: system/user шаблоны (русский, правила «только факты», «позиция банка только из фрагментов», «не упоминать признаки, которых нет», формат ролевого фокуса), `PROMPT_VERSION = "2026-10-25.1"`
- [ ] T018 [P] `tests/conftest.py`: фикстуры `settings` (tmp dirs, без ключа), `company_u1595`/`company_demo_local`/`company_u80` (из seed.py), `news_key_rate`/`news_logistics`/`news_labor`/`news_steel`, `chunk_key_rate` (ReportChunk с цитатой), `FakeGenerator` (очередь заранее заданных SixQuestions/CheckReport, учёт вызовов), `FakeStructuredModel` (BaseChatModel, у которого `with_structured_output` возвращает Runnable с фиксированным объектом) для тестов `LLMGenerator`, `FakeRetriever`, `NullRetriever`, `app_client` (httpx AsyncClient + ASGITransport)
- [ ] T019 `src/ai_service/main.py`: `create_app(settings=None, *, generator=None, retriever=None, scorer=None)` с lifespan (инициализация слотов моделей, генератора по режиму, ретривера или `NullRetriever`, датасетов лениво), `app.state.ctx`, подключение middleware request_id, handlers ошибок, роутера `api/health.py` (`GET /health` по контракту: mode, models, corpus, ocr_available через `shutil.which("tesseract")`); `app = create_app()`
- [ ] T020 [P] `tests/contract/test_health.py`: `/health` offline без корпуса → `mode=offline`, `corpus.available=false`; с `FakeRetriever` → `available=true`, `reports=1`

**Checkpoint**: `./scripts/check.sh` зелёный, `/health` работает, правила/скорер/схемы покрыты тестами.

## Phase 3: User Story 1 — Инсайт по новости (P1) 🎯 MVP

**Goal**: `POST /v1/insight` возвращает 6 блоков + `card` + трассировку; работает offline и с LLM; самопроверка убирает противоречия.

**Independent Test**: сценарии 1–5 US1 через `app_client` с `FakeRetriever`/`NullRetriever` и `OfflineGenerator`/`FakeGenerator`.

- [ ] T021 [P] [US1] `tests/agent/test_graph.py` (падают до реализации): happy path (ставка, U_1595, CFO, FakeRetriever) → все 6 блоков, q5 с страницей, триггер LOA, steps содержат plan/gather_context/draft/self_check/finalize; DEMO_LOCAL → нет LOA/FTS в q2/q3, check passed; NullRetriever → q5 None, `corpus_available=false`, шаг `AlfaRAGTool: corpus unavailable`; FakeGenerator с черновиком, упоминающим импорт при fts=0 → повторный draft (attempts=2) и затем зачистка, `violations` не пуст, `fixed` не пуст; генератор бросает исключение → `ApiError(llm_error)`; детерминизм offline (два прогона равны)
- [ ] T022 [P] [US1] `tests/unit/test_mapping.py`: `SixQuestions → Card` (url `/articles/{file}#page={n}`, `matched_company_features` как `FEATURE=value`, `verified_sources` с «, стр. N», q5 None → все `alfa_*` None, `action_item` объединяет q4)
- [ ] T023 [US1] `src/ai_service/agent/state.py`: `InsightState` TypedDict по data-model (`steps`/`errors` с `operator.add`), `NewsPlan`, `DraftContext`, `ChatContext` (pydantic/dataclasses)
- [ ] T024 [US1] `src/ai_service/agent/tools.py`: `CompanyProfileTool.run(company, datasets) -> (CompanyProfile, list[MatchedFeature], steps)` (дополняет пустые поля из датасета при `enrich_from_datasets`), `CounterpartyTool.run(company, datasets, top_n=5)` (из запроса или `datasets/payments.py`), `AlfaRAGTool.run(retriever, queries, top_k, min_score) -> (chunks, corpus_available, steps)`; `Retriever` Protocol (`search(query, k) -> list[ReportChunk]`, `available`, `stats()`), `NullRetriever`
- [ ] T025 [US1] `src/ai_service/agent/mapping.py`: `to_card(six, news, triggers, chunks) -> Card`, `build_traceability(state, generator) -> Traceability`, `compute_confidence(state)` (базово 0.5; +0.2 корпус с цитатой; +0.1 за ≥2 триггера; −0.2 при зачистке; клип)
- [ ] T026 [US1] `src/ai_service/agent/nodes.py`: `plan` (генератор `plan`, fallback на `classify_topic_offline`, запросы к корпусу из заголовка + ключевых слов темы), `gather_context` (три инструмента, усечение `full_text` до лимита с пометкой в `truncated`), `draft` (генератор, передаёт `feedback` из прошлой проверки), `self_check` (правила: признак в q2/q3 без триггера; слова «импорт/поставки/таможня» при `fts_flag=False`; «кредит/долг/ставка по кредиту компании» при `loa=False`; q5 без chunk или цитата не подстрока текста чанка; числа в q5.statement, отсутствующие в цитате; затем `generator.check`; объединение в `CheckReport`), `route_after_check` (`draft` если не passed и attempts < 2, иначе `finalize`), `finalize` (принудительная зачистка нарушений: удалить пункты рисков/возможностей с нарушением, q5 → None если источник не подтверждён; `Traceability`, `score_news`, `InsightResponse`)
- [ ] T027 [US1] `src/ai_service/agent/graph.py`: `build_insight_graph(generator, retriever, datasets, settings) -> CompiledStateGraph`, `RetryPolicy(max_attempts=settings.llm_max_retries)` на `plan/draft/self_check`, `recursion_limit`, `async run_insight(graph, request, request_id) -> InsightResponse` с `asyncio.timeout(settings.insight_timeout_s)` → `ApiError(llm_timeout)`; исключения генератора → `ApiError(llm_error)`
- [ ] T028 [US1] `src/ai_service/api/insight.py`: `POST /v1/insight` → `run_insight`, `latency_ms`, лог `insight.done` (request_id, mode, topic, triggers count, chunks count, passed, latency); подключить в `main.py`
- [ ] T029 [P] [US1] `tests/contract/test_insight_api.py`: 200 по контракту (ключи `request_id, mode, insight, card, importance, traceability, latency_ms`), `card` валидируется схемой backend (поля и типы), 422 на роль `CTO` → `error.code=validation_error`, 502 при падении генератора, 504 при `insight_timeout_s=0.01` и медленном FakeGenerator
- [ ] T030 [US1] `src/ai_service/cli.py`: `main()` с argparse-подкомандами; `insight --sample {key-rate,logistics,labor,steel} --company U --role R [--json]` (компании из `data/sample/companies.json`, новости из `data/sample/news.json` — создать файлы по seed.py), печать JSON; остальные подкоманды добавляются в своих фазах
- [ ] T031 [P] [US1] `data/sample/insight_request.json`, `data/sample/companies.json`, `data/sample/news.json` (U_1595, U_1465, U_80, U_3263, U_4217, DEMO_LOCAL; 5 новостей из seed.py)

**Checkpoint**: инсайт работает offline через HTTP и CLI; все сценарии US1 зелёные.

## Phase 4: User Story 2 — Корпус отчётов (P1)

**Goal**: `ai-service index-reports` строит индекс из PDF (OCR с кэшем), `/v1/reports`, `/v1/reports/search`, ретривер подключён к графу.

**Independent Test**: unit на фейках (экстрактор, эмбеддеры) + embedded Qdrant в `tmp_path`; ручная проверка quickstart §3 на реальных PDF.

- [ ] T032 [P] [US2] `tests/rag/test_chunk.py`: разбиение страницы 2500 символов → окна ≤ 800 с перекрытием, границы по предложениям, `chunk_id` формат, пустая страница → 0 чанков
- [ ] T033 [P] [US2] `tests/rag/test_extract.py`: `FakePdf` (страницы с текстом/без) → `PyMuPdfTextBackend` отдаёт текст, `OcrBackend` вызывается только для пустых страниц (мок `pytesseract`), кэш `data/index/ocr/<sha>.json` используется при повторе, повреждённый файл → `ExtractError` и пропуск в `index_reports`
- [ ] T034 [P] [US2] `tests/rag/test_index_retrieve.py`: `FakeDenseEmbedder` (детерминированный хэш-мешок слов, dim 64) + `FakeSparseEmbedder` (счётчик токенов) + `QdrantClient(path=tmp_path)`; индексируем 2 «отчёта» по 2 страницы → `stats()` верные; поиск «ключевая ставка» → чанк из отчёта о ставке первым, `page` верный; `min_score` отсекает мусорный запрос (`corpus weak`); переиндексация заменяет чанки, не дублирует; `list_reports()` возвращает ReportDocument
- [ ] T035 [US2] `src/ai_service/rag/catalog.py`: загрузка `data/reports_catalog.yaml`, `title_for(file, first_page_text)` с fallback на первую содержательную строку OCR
- [ ] T036 [US2] `src/ai_service/rag/extract.py`: `PageText`, `PageTextExtractor` Protocol, `PyMuPdfTextBackend`, `TesseractOcrBackend(lang="rus+eng", dpi=200)` (рендер PyMuPDF → PIL → pytesseract; `available()` через `shutil.which`), `CachedExtractor(backends, cache_dir)` с ключом sha256 файла, `ExtractError`
- [ ] T037 [P] [US2] `src/ai_service/rag/chunk.py`: `split_page(text, max_chars=800, overlap=150) -> list[str]` по предложениям/абзацам, нормализация пробелов и переносов OCR
- [ ] T038 [P] [US2] `src/ai_service/rag/embedders.py`: `DenseEmbedder`/`SparseEmbedder` Protocols (`embed(texts)`, `embed_query(text)`, `dim`), `FastembedDense(model_name, cache_dir)`, `FastembedBm25(language="russian")` c ленивой загрузкой моделей
- [ ] T039 [US2] `src/ai_service/rag/index.py`: `ReportIndex(client, dense, sparse, collection="alfa_reports")`: `ensure_collection()` (named vectors `dense` cosine + `sparse` с IDF modifier), `index_report(path, extractor, catalog) -> ReportDocument` (удаление старых точек по `report_id`, upsert чанков, манифест `data/index/manifest.json`), `index_directory(dir) -> IndexReport` (пропуск ошибок с логом), `list_reports()`, `stats()`
- [ ] T040 [US2] `src/ai_service/rag/retriever.py`: `QdrantHybridRetriever(index, top_k, min_score)` реализует `Retriever`: `query_points(prefetch=[dense, sparse], query=FusionQuery(RRF))`, затем отдельный dense-score для гейта (`dense_score` в чанке), `available` = коллекция существует и не пуста; `build_retriever(settings) -> Retriever` (Null, если индекса нет)
- [ ] T041 [US2] `src/ai_service/api/reports.py`: `GET /v1/reports`, `GET /v1/reports/search?q&k` (503 `corpus_error`, если индекс отсутствует); подключить в `main.py`; `/health` берёт `corpus` из `retriever.stats()`
- [ ] T042 [US2] `cli.py`: подкоманды `index-reports [--dir] [--force]` (печать по отчётам: pages, chunks, extractor, время) и `search <query> [-k]`
- [ ] T043 [P] [US2] `tests/contract/test_reports_api.py`: `/v1/reports` с FakeRetriever; `/v1/reports/search` 200 и 503 с NullRetriever
- [ ] T044 [US2] Ручная проверка quickstart §3 на реальных 9 PDF (OCR ~4 с/страница, кэш), зафиксировать в `specs/001-ai-service/quickstart.md` фактические числа (страниц, чанков, время) и топ-результаты двух поисков

**Checkpoint**: инсайт по ставке для U_1595 из CLI показывает позицию банка с отчётом и страницей.

## Phase 5: User Story 3 — Чат по карточке (P2)

**Goal**: `POST /v1/ask` отвечает по контексту карточки с источниками, отбивает оффтоп и инъекции.

- [ ] T045 [P] [US3] `tests/unit/test_chat.py` и `tests/contract/test_ask_api.py`: вопрос про долг → `on_topic=true`, `sources` содержит отчёт и новость; «напиши стихотворение» → `on_topic=false`, ответ о рамках карточки; вопрос с «игнорируй правила…» → инструкция не исполнена (ответ не содержит системного промпта, `on_topic` по теме); 422 на 2001 символ; offline детерминизм
- [ ] T046 [US3] `src/ai_service/agent/chat.py`: `is_on_topic(question, news, card, topic)` (пересечение лемм/ключевых слов темы и карточки, список оффтоп-маркеров), `build_chat_context` (новость, card, профиль, роль, retrieval top-3 по вопросу + теме), `answer_question(generator, retriever, request) -> AskResponse` с источниками (чанк+страница, новость); `OfflineGenerator.answer` — шаблон на основе card и лучшего чанка; `LLMGenerator.answer` — `ChatDraft` structured output (answer, used_chunk_ids, on_topic)
- [ ] T047 [US3] `src/ai_service/api/chat.py`: `POST /v1/ask`, таймаут `chat_timeout_s`, ошибки как в инсайте; подключить в `main.py`
- [ ] T048 [P] [US3] `data/sample/ask_request.json`

**Checkpoint**: сценарии US3 1–4 зелёные.

## Phase 6: User Story 4 — Скоринг важности (P2)

**Goal**: `POST /v1/score` пакетно, порядок сохранён, факторы объяснимы; опциональная LLM-поправка.

- [ ] T049 [P] [US4] `tests/contract/test_score_api.py`: 3 новости → 3 оценки в порядке входа; ACCOUNTANT vs CEO для рынка труда; 422 на пустой список и на 201 новость
- [ ] T050 [US4] `src/ai_service/scoring/service.py`: `score_batch(company, role, news_items, generator|None)`: тема через `classify_topic_offline` (или `news.topic`), триггеры, `score_news`; при `mode=llm` и `settings.score_llm_adjust=true` — один вызов слота `fast` на пакет с structured output `list[Adjustment(news_id, delta ∈ {-1,0,1}, reason)]`, применяется с клипом и фактором `llm_adjustment`
- [ ] T051 [US4] `src/ai_service/api/score.py`: `POST /v1/score`; подключить; `data/sample/score_request.json`

**Checkpoint**: сценарии US4 1–3 зелёные.

## Phase 7: User Story 5 — Сбор новостей (P3)

**Goal**: `POST /v1/news/collect` и `ai-service collect-news` возвращают нормализованные, дедуплицированные, релевантные новости из RSS.

- [ ] T052 [P] [US5] `tests/ingest/test_rss.py` с фикстурами `tests/fixtures/rss/cbr_press.xml`, `rbc_full.xml` (сокращённые реальные ленты, включая `rbc_news:full-text`): парсинг → NewsItem с tz-датой, `summary_facts` без HTML, `id` = uuid5(url), источник; недоступный источник (мок httpx → 500) → `SourceStatus.ok=false`, остальные обработаны
- [ ] T053 [P] [US5] `tests/ingest/test_normalize.py`: `strip_html`, усечение summary до 4000, `dedupe` (одинаковый URL; одинаковый заголовок с разной пунктуацией; Jaccard ≥ 0.8), `is_relevant` (ставка/инфляция/налоги → true; спорт/культура/погода → false), `since` и `exclude_urls` фильтруют, `limit` соблюдается
- [ ] T054 [US5] `src/ai_service/ingest/sources.py`: `DEFAULT_SOURCES` (cbr_press, cbr_news, rbc, interfax, kommersant из research R8 с `default_category`), переопределение через `AI_NEWS_SOURCES_JSON`
- [ ] T055 [P] [US5] `src/ai_service/ingest/rss.py`: `fetch_source(client, source) -> (list[RawEntry], SourceStatus)` (httpx async, UA, таймаут 15 с, `feedparser.parse(bytes)`, поддержка `rbc_news:full-text`), `ingest/normalize.py`: `to_news_item(raw, source) -> NewsItem` (strip html, даты, категория offline через `classify_topic_offline` + `CATEGORY_LABELS_RU`)
- [ ] T056 [P] [US5] `src/ai_service/ingest/dedupe.py` (`normalize_url`, `normalize_title`, `jaccard`, `dedupe(items)`) и `ingest/relevance.py` (`is_relevant(item)`: словарь экономических терминов, стоп-темы; при `mode=llm` батч-классификация слотом `fast` с structured output, fallback на словарь)
- [ ] T057 [US5] `src/ai_service/ingest/collector.py`: `collect(request, settings, generator|None) -> CollectResponse` (параллельный fetch источников через `asyncio.gather`, фильтры since/exclude, дедуп, релевантность, сортировка по дате, limit, отчёт)
- [ ] T058 [US5] `src/ai_service/api/news.py`: `POST /v1/news/collect`; `cli.py collect-news [--limit] [--since] [--sources]`; подключить
- [ ] T059 [P] [US5] `tests/contract/test_news_api.py` с моком `fetch_source`

**Checkpoint**: `uv run ai-service collect-news --limit 20` (с сетью) даёт отчёт по 5 источникам.

## Phase 8: Polish & Cross-Cutting

- [ ] T060 [P] `src/ai_service/datasets/companies.py` (pandas `read_csv(sep=";")`, lru-кэш, `get_profile(synthetic_u) -> CompanyProfile | None`, `merge_missing(profile, row)`), `datasets/payments.py` (`top_counterparties(synthetic_u, n)` по PAY_AMT из `df_Uid_payment_hack.csv`, обогащение ОКВЭД контрагента из companies), `tests/unit/test_datasets.py` на мини-CSV в `tests/fixtures/`
- [ ] T061 [P] `evals/golden.jsonl` (≥ 20 пар из `data/sample` × роли с ожидаемыми: тема, обязательные триггеры, запрещённые признаки, ожидаемый отчёт при наличии корпуса, ключевые слова ролевого фокуса), `evals/run_eval.py` (метрики: six_blocks_coverage, source_hit@3, profile_violations, role_focus_hit, latency; сравнение с `evals/baseline.json`, exit 1 при регрессии; флаг `--update-baseline`), `evals/baseline.json` из offline-прогона
- [ ] T062 [P] `Dockerfile` (python:3.12-slim, `apt tesseract-ocr tesseract-ocr-rus`, uv sync --frozen --no-dev, non-root, `HEALTHCHECK /health`, `CMD uvicorn ai_service.main:app --host 0.0.0.0 --port 8001`), `.dockerignore` (data/, tests/, .venv)
- [ ] T063 [P] `03-ai-service/README.md`: заменить текущий — назначение, архитектура (граф, RAG, режимы), запуск (quickstart), API (ссылка на `specs/001-ai-service/contracts/openapi.yaml` и `/docs`), переменные окружения, интеграция с backend (ссылка на backend-integration.md), ограничения (корпус — сканы, OCR; модели ТЗ; offline-режим), оценка стоимости/токенов на инсайт (3 вызова, ~6–8k входных токенов) 
- [ ] T064 Обновить корневой `README.md` (раздел «Быстрый старт»/архитектура: сервис ai-service на 8001, команда индексации) и `THIRD_PARTY_NOTICES.md` (fastembed, qdrant-client, PyMuPDF AGPL-3.0 — отметить лицензию, pytesseract/Tesseract Apache-2.0, feedparser, LangGraph/LangChain) — минимальные правки в общих файлах
- [ ] T065 Прогон `./scripts/check.sh` + quickstart §§1–10 целиком; зафиксировать результаты в `quickstart.md`; `git commit` conventional commits по фазам

## Dependencies & Execution Order

- Phase 1 → Phase 2 → (Phase 3 → Phase 4) → Phase 5, Phase 6, Phase 7 (независимы, после Phase 3) → Phase 8.
- Phase 4 зависит от `Retriever` Protocol (T024) и даёт реальный ретривер; Phase 3 тестируется на `FakeRetriever`.
- Phase 5 использует `generator.answer` и ретривер; Phase 6 — `scorer.py` (Phase 2); Phase 7 — `classify_topic_offline` (Phase 2).
- T060 (датасеты) нужен для `enrich_from_datasets`, но граф работает и без него (пустые датасеты).

## Parallel Example: Phase 2

```bash
# После T005 параллельно: T006, T007, T008, T009, T010, T012, T014, T017, T018, T020
```

## Implementation Strategy

1. **MVP** = Phase 1–3: инсайт offline через HTTP и CLI с `NullRetriever` → можно
   отдавать backend'у контракт и демо без корпуса.
2. Phase 4 даёт «позицию банка» из реальных отчётов — ключевая демонстрация для жюри.
3. Phase 5–7 — независимые инкременты; Phase 8 — поставка и eval-гейт.
4. Коммит после каждой фазы: `feat(ai-service): ...`, `test(ai-service): ...`, `docs(ai-service): ...`.
