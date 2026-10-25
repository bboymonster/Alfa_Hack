# Research: AI-Service «Новость → Инсайт»

**Date**: 2026-10-25 | **Feature**: `specs/001-ai-service/spec.md`

Каждое решение: что выбрано, почему, что отвергнуто.

## R1. Форма интеграции с backend

- **Decision**: отдельный FastAPI-сервис `03-ai-service` на порту 8001, HTTP/JSON, вызывается
  backend'ом. Backend остаётся владельцем auth, хранения и аудита.
- **Rationale**: выбор пользователя; независимый деплой и тесты; тяжёлые зависимости
  (ONNX-эмбеддинги, OCR, LangGraph) не попадают в процесс backend.
- **Alternatives**: Python-пакет внутри `02-backend` (проще вызов, но тащит ML-зависимости
  в backend и ломает разделение зон команды).

## R2. LLM-провайдер и режимы работы

- **Decision**: один OpenAI-совместимый клиент (`langchain-openai`, `ChatOpenAI(base_url,
  api_key, model)`), три конфигурируемых слота моделей из Приложения 3 ТЗ:
  `fast` (классификация/скоринг — Gemma 4 26B A4B), `main` (черновик инсайта, чат —
  DeepSeek-V4.1-Flash), `checker` (самопроверка — GLM-5.3-Flash). Если `AI_LLM_API_KEY`
  пуст — сервис стартует в `mode=offline`: детерминированные шаблонные генераторы,
  ответы помечены `mode: offline` (backend выставляет `is_demo`).
- **Rationale**: у команды пока нет ключа; OpenRouter и большинство хостингов разрешённых
  моделей совместимы с OpenAI API, поэтому подключение = переменные окружения. Разделение
  на слоты позволяет дешёвую модель на массовые операции.
- **Alternatives**: `langchain-anthropic`/Claude — запрещено регламентом кейса; локальный
  vLLM/Ollama — совместим с тем же клиентом через `base_url`, отдельный код не нужен.
- **Open**: точные id моделей у провайдера (например `deepseek/deepseek-v4.1-flash`) —
  проверить при получении ключа; в `.env.example` оставлены плейсхолдеры с TODO.

## R3. Архитектура агента

- **Decision**: LangGraph `StateGraph` как детерминированный пайплайн, а не свободный
  ReAct: `plan → gather_context → draft → self_check → (draft повторно ≤1 раз | finalize)`.
  Инструменты (`CompanyProfileTool`, `CounterpartyTool`, `AlfaRAGTool`) вызываются нодой
  `gather_context` явно, их результаты складываются в state. Генерация и проверка идут
  через протокол `InsightGenerator` с двумя реализациями: `LLMGenerator`
  (`with_structured_output(PydanticModel)`) и `OfflineGenerator` (правила + шаблоны).
- **Rationale**: ТЗ требует шаги «планирование → инструменты → самопроверка» и
  трассируемость; явный граф делает шаги видимыми в `traceability.agent_steps`, а
  протокол генератора позволяет один и тот же граф гонять в тестах и offline без LLM.
  `RetryPolicy` на LLM-нодах, `recursion_limit`, ошибки инструментов — в state, не исключения.
- **Alternatives**: ReAct с tool calling (менее предсказуем, дороже по токенам, сложнее
  гарантировать 6 блоков); цепочка LCEL без графа (нет ретраев/ветвления самопроверки).

## R4. Извлечение текста из PDF-отчётов

- **Finding**: все 9 PDF (60 страниц) — изображения без текстового слоя: pypdf и PyMuPDF
  дают 0 символов, по одному изображению на страницу, шрифтов нет.
- **Decision**: `PageTextExtractor` с цепочкой бэкендов: PyMuPDF text layer → Tesseract
  OCR (`rus+eng`, рендер страницы PyMuPDF 200 dpi) → (позже) VLM Qwen3-VL. Результат OCR
  кэшируется в `data/index/ocr/<sha256>.json`, переиндексация без повторного OCR.
  Локально `brew install tesseract tesseract-lang`, в Docker `apt tesseract-ocr-rus`.
- **Rationale**: выбор пользователя; Tesseract — единственный переносимый вариант без
  ключа модели и без torch. Кэш нужен, потому что OCR 60 страниц занимает минуты.
- **Alternatives**: Apple Vision (`ocrmac`) — только macOS; EasyOCR — torch ~2 ГБ;
  RapidOCR — нет готовой кириллической модели; Qwen3-VL — разрешён ТЗ и понимает графики,
  но требует ключ; оставлен как второй бэкенд.

## R5. Эмбеддинги и векторный поиск

- **Decision**: Qdrant в embedded-режиме (`QdrantClient(path="data/index/qdrant")`),
  гибридный поиск: dense `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  (fastembed, ONNX, 384 dim, ~0.22 ГБ) + sparse `Qdrant/bm25` (fastembed `Bm25`,
  `language="russian"`), слияние RRF через `query_points(prefetch=[dense, sparse],
  query=FusionQuery(fusion=RRF))`. Гейт «слабый retrieval»: dense-score лучшего
  фрагмента ниже `AI_RAG_MIN_SCORE` (по умолчанию 0.45) → позиция банка не заполняется.
- **Rationale**: корпус крошечный (≈60 страниц, сотни фрагментов), важнее точность
  цитирования страницы, чем масштаб. fastembed даёт ONNX без torch (Docker-образ в разы
  меньше), BM25 ловит точные термины («ключевая ставка 14,0%», «7М26»), dense — перефраз.
  Embedded Qdrant не требует контейнера и совпадает с моим стеком.
- **Alternatives**: sentence-transformers `multilingual-e5` (лучше качество, но torch);
  `intfloat/multilingual-e5-small` через `TextEmbedding.add_custom_model` — возможен как
  апгрейд без смены кода (оставлен в конфиге как опция); только BM25 (нет перефраза);
  Chroma/FAISS — не в стеке.
- **Тесты**: протоколы `DenseEmbedder`/`SparseEmbedder` с фейками (хэш-эмбеддер,
  токен-счётчик) — без загрузки моделей и сети.

## R6. Чанкинг и каталог отчётов

- **Decision**: единица хранения — фрагмент страницы: текст страницы режется на окна
  ~800 символов с перекрытием 150 по границам предложений; payload: `report_id`, `title`,
  `file`, `page`, `chunk_index`, `text`, `indexed_at`. Названия отчётов берутся из
  `data/reports_catalog.yaml` (имя файла → официальное название, как в
  `THIRD_PARTY_NOTICES.md`), fallback — первая строка OCR первой страницы.
- **Rationale**: страница — минимальная единица цитирования, которую требует ТЗ
  («ссылка на отчёт и страницу»); каталог нужен, потому что OCR заголовков ненадёжен.

## R7. Скоринг важности

- **Decision**: детерминированный rule-based скорер (база 5; совпадение отрасли +2;
  сработавшие признаки компании по теме +1 за каждый, максимум +3; ролевой фокус +1/+2;
  давность > 30 дней −1; масштаб события по словарю +1; клип 1–10) с перечнем факторов.
  В режиме LLM — опциональная корректировка ±1 моделью `fast` с объяснением.
- **Rationale**: объяснимость и детерминизм (FR-022), нулевая стоимость для пакетной
  оценки ленты; LLM-поправка не ломает порядок при недоступности модели.

## R8. Сбор новостей

- **Decision**: `feedparser` + `httpx` для RSS; источники по умолчанию (проверены
  2026-10-25): ЦБ РФ пресс-релизы `https://www.cbr.ru/rss/RssPress` (14 записей), ЦБ РФ
  новости `https://www.cbr.ru/rss/RssNews` (100), РБК `https://rssexport.rbc.ru/rbcnews/news/30/full.rss`
  (29, есть полный текст), Интерфакс `https://www.interfax.ru/rss.asp` (25), Коммерсантъ
  `https://www.kommersant.ru/RSS/news.xml` (374). Росстат и Минфин RSS недоступны/пусты —
  не включены. Дедуп: нормализованный URL + нормализованный заголовок + Jaccard токенов
  ≥ 0.8. Фильтр релевантности: offline — словарь экономических терминов и стоп-тем
  (спорт, культура, происшествия, политика без экономики); LLM — классификатор `fast`.
  Статус «уже отдано» хранит backend: запрос содержит `since` и `exclude_urls`.
- **Rationale**: сервис остаётся stateless (принцип VI); деловые СМИ дают поток для демо,
  официальные ленты — факты для карточек.

## R9. Профиль компании и контрагенты

- **Decision**: профиль приходит в запросе (поля датасета `df_Uid_data_hack.csv`,
  85 525 компаний; разделитель `;`). Опциональное обогащение из локальных CSV
  (`AI_DATASETS_DIR`): `CompanyProfileTool` дополняет пустые поля, `CounterpartyTool`
  берёт топ контрагентов из `df_Uid_payment_hack.csv` (1,38 млн строк: BENEFICIARY,
  PAYER, PAY_AMT, PAY_CNT) через pandas, загружается лениво один раз.
  `df_Fid_Uid_link_hack.csv` (связи физлиц и компаний, 12 514 строк) в MVP не используется.
- **Rationale**: backend уже владеет профилем; CSV нужны для демо и golden-набора.

## R10. Логи, ошибки, наблюдаемость

- **Decision**: structlog JSON; на каждый LLM-вызов событие `llm.call` (`slot`, `model`,
  `input_tokens`, `output_tokens`, `latency_ms`, `request_id`), без текстов. Ошибки API —
  единый `{"error": {"code", "message", "request_id"}}`; коды: `validation_error` (422),
  `llm_timeout` (504), `llm_error` (502), `corpus_error` (503 только для /reports/search).
  Таймаут одного LLM-вызова 30 с, инсайта целиком 60 с.

## R11. Тесты и eval

- **Decision**: pytest без сети: фейковые генераторы, фейковые эмбеддеры, фейковый
  экстрактор PDF, embedded Qdrant в `tmp_path`, httpx `ASGITransport` для контрактных
  тестов. Eval: `evals/golden.jsonl` (≥ 20 пар из сидов `04-infra-db/seed.py` и
  реальных отчётов), метрики: покрытие 6 блоков, source-hit@3, нарушения профиля,
  попадание ролевого фокуса; `baseline.json` в git; скрипт возвращает exit 1 при регрессии.

## R12. Поставка

- **Decision**: `03-ai-service/Dockerfile` (python:3.12-slim + tesseract-ocr-rus + uv,
  non-root, HEALTHCHECK `/health`), сервис `ai-service` для `04-infra-db/docker-compose.yml`
  описан в `quickstart.md` как сниппет для участника 4; backend получает `AI_SERVICE_URL`.
  Индекс и OCR-кэш — volume `ai_index`.
