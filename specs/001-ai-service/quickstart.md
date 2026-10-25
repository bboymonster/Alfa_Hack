# Quickstart: проверка AI-Service

Все команды — из `03-ai-service/`. Нужны: `uv`, Python 3.12 (uv скачает), для OCR —
`brew install tesseract tesseract-lang` (macOS) или `apt install tesseract-ocr tesseract-ocr-rus`.

## 1. Установка и проверки

```bash
uv sync
./scripts/check.sh          # ruff check, ruff format --check, mypy, pytest — всё зелёное, без сети
```

Ожидание: проверки проходят без ключа LLM и без скачивания моделей (тесты на фейках).

## 2. Данные

```text
data/articles/   ← 9 PDF отчётов Альфа-Банка (из архива «статьи.zip»)
data/datasets/   ← df_Uid_data_hack.csv, df_Uid_payment_hack.csv, df_Fid_Uid_link_hack.csv
```

Папки в `.gitignore`; пути переопределяются `AI_ARTICLES_DIR`, `AI_DATASETS_DIR`, `AI_INDEX_DIR`.

## 3. Индексация корпуса (US2)

```bash
uv run ai-service index-reports
# Ожидание: 9 отчётов, ~60 страниц, extractor=ocr, несколько сотен фрагментов; повтор
# команды использует OCR-кэш и завершается за секунды.
uv run ai-service search "ключевая ставка 14%"
# Ожидание: в топ-3 фрагмент из «Ключевая ставка ЦБ РФ: ставка без изменения на 14,0%…», стр. 1–2.
uv run ai-service search "недельная инфляция плодоовощная продукция"
# Ожидание: фрагмент из «Инфляция 25–31 августа: основные выводы».
```

## 4. Запуск сервиса

```bash
uv run uvicorn ai_service.main:app --port 8001 --reload
curl -s localhost:8001/health | jq
# Ожидание: {"status":"ok","mode":"offline","corpus":{"available":true,"reports":9,...},"ocr_available":true}
```

## 5. Инсайт (US1) — offline-режим

```bash
uv run ai-service insight --sample key-rate --company U_1595 --role CFO | jq .card
```

Ожидание: заполнены `why_it_matters` (упоминает кредиты `CL_PRODUCT_LOA_MARK=1` и выручку),
`risks`, `opportunities`, `action_item`; `alfa_bank_position` с `alfa_report_name` отчёта о
ставке и `alfa_report_page`; `traceability.matched_company_features` содержит `CL_PRODUCT_LOA_MARK=1`.

```bash
uv run ai-service insight --sample key-rate --company DEMO_LOCAL --role CEO | jq .insight
```

Ожидание: компания без кредитов и импорта — в `q3_risks` нет утверждений про собственный
долг или импорт; `self_check.passed = true`.

Повторный вызов с теми же аргументами даёт идентичный JSON (детерминизм offline).

Через HTTP: `curl -X POST localhost:8001/v1/insight -H 'content-type: application/json' -d @data/sample/insight_request.json`.

## 6. Чат (US3)

```bash
curl -s -X POST localhost:8001/v1/ask -H 'content-type: application/json' \
  -d @data/sample/ask_request.json | jq
```

Ожидание: `on_topic: true`, `sources` содержит отчёт со страницей. Вопрос «напиши
стихотворение» → `on_topic: false`, ответ возвращает к теме карточки.

## 7. Скоринг (US4)

```bash
curl -s -X POST localhost:8001/v1/score -d @data/sample/score_request.json -H 'content-type: application/json' | jq '.scores[] | {news_id, score}'
```

Ожидание: новость о рынке труда для роли ACCOUNTANT выше, чем для CEO; порядок как во входе.

## 8. Сбор новостей (US5)

```bash
uv run ai-service collect-news --limit 20
```

Ожидание: отчёт по источникам (cbr_press, cbr_news, rbc, interfax, kommersant), новости с
категорией, без точных дубликатов; спортивные/культурные материалы отброшены. Требует сеть.

## 9. Включение реальной LLM

```bash
cp .env.example .env   # заполнить AI_LLM_BASE_URL, AI_LLM_API_KEY, AI_LLM_MODEL_*
```

После перезапуска `/health` показывает `mode: "llm"` и `models`. Перед мержем изменений
промптов/моделей: `uv run python evals/run_eval.py` — сравнение с `evals/baseline.json`,
exit 1 при регрессии.

## 10. Docker

```bash
docker build -t alfa-ai-service:local .
docker run --rm -p 127.0.0.1:8001:8001 -v "$PWD/data/articles:/data/articles:ro" -v ai_index:/data/index alfa-ai-service:local
```

Ожидание: контейнер `healthy`, `/health` отвечает; сниппет для общего compose — в
[contracts/backend-integration.md](contracts/backend-integration.md).
