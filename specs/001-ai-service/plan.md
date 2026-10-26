# Implementation Plan: AI-Service «Новость → Инсайт»

**Branch**: `feat/ai-service` (spec dir `001-ai-service`) | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-ai-service/spec.md`

## Summary

Отдельный FastAPI-сервис `03-ai-service`, который по новости, профилю компании и роли
собирает инсайт из 6 блоков ТЗ через LangGraph-пайплайн «план → инструменты (профиль,
контрагенты, RAG по отчётам банка) → черновик → самопроверка → финализация», отвечает на
вопросы по карточке, оценивает важность новости и собирает новости из RSS. RAG — OCR
(Tesseract) сканов отчётов → гибридный поиск (fastembed dense + BM25) в embedded Qdrant с
цитированием страницы. Любой LLM-вызов идёт через OpenAI-совместимый клиент с моделями из
Приложения 3 ТЗ; без ключа сервис работает в детерминированном offline-режиме.

## Technical Context

**Language/Version**: Python 3.12 (uv, `requires-python = ">=3.12"`)

**Primary Dependencies**: fastapi, uvicorn, pydantic v2, pydantic-settings, structlog,
langgraph ≥ 1.0, langchain ≥ 1.0, langchain-openai, qdrant-client (local mode),
fastembed (dense MiniLM-multilingual + Bm25), pymupdf, pytesseract (+ системный tesseract
rus/eng), feedparser, httpx, pandas (CSV датасетов), pyyaml (каталог отчётов)

**Storage**: embedded Qdrant `data/index/qdrant/`, OCR-кэш `data/index/ocr/*.json`;
никакой БД — состояние новостей/инсайтов у backend

**Testing**: pytest + pytest-asyncio (`asyncio_mode=auto`), httpx `ASGITransport`;
фейки: генератор инсайтов, эмбеддеры, экстрактор PDF, RSS-фикстуры; без сети

**Target Platform**: Linux-контейнер (python:3.12-slim + tesseract-ocr-rus), локально macOS

**Project Type**: web-service (HTTP API) + CLI (индексация, сбор, демо)

**Performance Goals**: инсайт offline < 2 с; с LLM < 30 с (3 последовательных вызова);
скоринг 100 новостей < 1 с; поиск по корпусу < 300 мс

**Constraints**: только модели Приложения 3; работает без ключа; тесты без сети;
Docker-образ без torch (ONNX); все тексты для пользователя на русском

**Scale/Scope**: корпус ≈ 60 страниц / ≈ 300 фрагментов; 3–5 демо-компаний, до 100
новостей в ленте; один инстанс, один воркер

## Проверка требований

Основание: [принципы сервиса](principles.md).

| Принцип | Как выполняется | Статус |
|---|---|---|
| I. Контракт прежде всего | `contracts/openapi.yaml`; ответ `/v1/insight` содержит `card` в формате backend `Insight` без изменений его полей; маппинг q1–q6 → card в `agent/mapping.py` | PASS |
| II. Нет источника — нет утверждения | `alfa_*` заполняются только из `ReportChunk` выше порога; `matched_company_features` строятся кодом из профиля (`agent/rules.py`), не моделью; нода `self_check` с правилами противоречий + LLM-проверка | PASS |
| III. Трассируемость и наблюдаемость | `Traceability` обязателен; structlog-событие `llm.call` без текстов; `RetryPolicy`, таймауты, `max_tokens` в `llm/provider.py`; структурированные ошибки | PASS |
| IV. Разрешённые модели, конфиг | `Settings` с слотами `fast/main/checker`, id из env; `mode=offline` без ключа; тесты на фейках | PASS |
| V. Тесты и eval как гейт | `scripts/check.sh` (ruff, mypy, pytest); `evals/` с golden и baseline | PASS |
| VI. Простота и независимость | stateless, контекст в запросе; embedded Qdrant; новые зависимости перечислены ниже | PASS, см. Complexity Tracking |

**Re-check после Phase 1**: контракты и модель данных не добавили состояния и внешних
сервисов; все новые зависимости обоснованы. PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-service/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml            # HTTP-контракт ai-service
│   └── backend-integration.md  # как backend вызывает сервис, fallback, маппинг
├── checklists/requirements.md
└── tasks.md                    # задачи реализации
```

### Source Code (repository root)

```text
03-ai-service/
├── pyproject.toml / uv.lock
├── README.md                   # заменяет текущий README: запуск, API, режимы
├── .env.example
├── Dockerfile
├── scripts/check.sh            # ruff check, ruff format --check, mypy, pytest
├── data/
│   ├── reports_catalog.yaml    # файл → название отчёта (в git)
│   ├── sample/                 # маленькие фикстуры (в git)
│   ├── articles/               # PDF (gitignored)
│   ├── datasets/               # CSV (gitignored)
│   └── index/                  # qdrant + ocr-кэш (gitignored)
├── evals/
│   ├── golden.jsonl
│   ├── baseline.json
│   └── run_eval.py
├── src/ai_service/
│   ├── main.py                 # create_app(), lifespan, роутеры
│   ├── config.py               # Settings (env AI_*)
│   ├── logging.py              # structlog setup, request_id middleware
│   ├── errors.py               # ApiError, handlers
│   ├── api/
│   │   ├── health.py           # GET /health
│   │   ├── insight.py          # POST /v1/insight
│   │   ├── chat.py             # POST /v1/ask
│   │   ├── score.py            # POST /v1/score
│   │   ├── news.py             # POST /v1/news/collect
│   │   └── reports.py          # GET /v1/reports, GET /v1/reports/search
│   ├── schemas/
│   │   ├── common.py           # Role, Mode, NewsCategory, ErrorResponse
│   │   ├── company.py          # CompanyProfile, Counterparty
│   │   ├── news.py             # NewsItem
│   │   ├── insight.py          # SixQuestions, Traceability, Card (backend), InsightResponse
│   │   ├── chat.py / score.py / reports.py / ingest.py
│   ├── llm/
│   │   ├── provider.py         # build_models(settings) -> ModelSlots | None
│   │   ├── generator.py        # InsightGenerator protocol, LLMGenerator, OfflineGenerator
│   │   └── callbacks.py        # structlog callback: tokens/latency
│   ├── prompts/
│   │   ├── insight.py / check.py / chat.py / classify.py
│   ├── agent/
│   │   ├── state.py            # InsightState (TypedDict)
│   │   ├── rules.py            # topic taxonomy, триггеры профиль↔тема, ROLE_FOCUS
│   │   ├── tools.py            # CompanyProfileTool, CounterpartyTool, AlfaRAGTool
│   │   ├── nodes.py            # plan, gather_context, draft, self_check, finalize
│   │   ├── graph.py            # build_insight_graph(generator, tools)
│   │   └── mapping.py          # SixQuestions -> Card
│   ├── rag/
│   │   ├── extract.py          # PageTextExtractor: PyMuPDF text -> Tesseract OCR, кэш
│   │   ├── chunk.py
│   │   ├── embedders.py        # DenseEmbedder/SparseEmbedder protocols + fastembed impl
│   │   ├── index.py            # build/refresh index
│   │   ├── retriever.py        # hybrid search -> list[ReportChunk]
│   │   └── catalog.py
│   ├── scoring/scorer.py
│   ├── ingest/
│   │   ├── sources.py / rss.py / normalize.py / dedupe.py / relevance.py / collector.py
│   ├── datasets/
│   │   ├── companies.py        # загрузка df_Uid_data_hack.csv
│   │   └── payments.py         # контрагенты из df_Uid_payment_hack.csv
│   └── cli.py                  # ai-service index-reports | search | collect-news | insight
└── tests/
    ├── conftest.py             # fixtures: settings, fake generator/embedders/extractor, app client
    ├── unit/                   # rules, mapping, scorer, chunk, dedupe, relevance, extract
    ├── agent/                  # graph paths: happy, no-corpus, contradiction, generator error
    ├── rag/                    # index+retrieve on fakes, catalog
    └── contract/               # test_api_*.py по openapi
```

**Structure Decision**: один Python-пакет `ai_service` внутри `03-ai-service/` (зона
участника 3), слои `api → agent/scoring/ingest → llm/rag/datasets`. Другие папки репо не
меняются; интеграция с backend описана в `contracts/backend-integration.md` и выполняется
владельцем backend.

## Пайплайн инсайта (граф)

```mermaid
flowchart LR
    START --> plan
    plan --> gather_context
    gather_context --> draft
    draft --> self_check
    self_check -->|ok или 2-я попытка| finalize
    self_check -->|нарушения, 1-я попытка| draft
    finalize --> END
```

- `plan`: категория новости и ключевые темы (offline — словарь; LLM — слот `fast`,
  structured output `NewsPlan`), формирование поисковых запросов к корпусу.
- `gather_context`: `CompanyProfileTool` → `matched_triggers` по правилам;
  `CounterpartyTool` → топ контрагентов (если переданы или доступны CSV);
  `AlfaRAGTool` → `ReportChunk[]` + флаг `corpus_available`.
- `draft`: генератор → `SixQuestions` (LLM слот `main` или offline-шаблоны).
- `self_check`: правила (признаки без значения в профиле, импорт при `FTS_FLAG=0`,
  позиция банка без фрагмента, цифры, отсутствующие в источниках) + LLM-проверка слотом
  `checker`; результат `CheckReport` в state; при нарушениях — одна повторная генерация с
  замечаниями, затем принудительная зачистка полей.
- `finalize`: `Traceability`, `confidence`, маппинг в `Card`, скоринг важности.

## Complexity Tracking

| Отклонение / зависимость | Зачем | Почему не проще |
|---|---|---|
| Tesseract (системная зависимость) | все PDF — сканы без текста | pypdf/PyMuPDF дают 0 символов; VLM требует ключ; EasyOCR тянет torch |
| fastembed вместо sentence-transformers | ONNX без torch, образ в разы меньше | sentence-transformers даёт лучшее e5, но +2 ГБ torch в образ хакатона |
| pandas | фильтрация 1,38 млн строк платежей | csv-модуль медленнее на каждый запрос; pandas уже в THIRD_PARTY_NOTICES |
| feedparser | парсинг разношёрстных RSS (CBR, РБК с namespace) | ручной XML-парсинг хрупок на невалидных лентах |
| Два режима генерации (LLM/offline) | ключа нет, тесты без сети, демо жюри без ключа | один LLM-режим делает сервис неработоспособным без ключа (нарушает принцип IV) |
