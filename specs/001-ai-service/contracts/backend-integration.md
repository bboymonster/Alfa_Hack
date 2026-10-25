# Интеграция `02-backend` ↔ `03-ai-service`

Контракт HTTP — [openapi.yaml](openapi.yaml). Этот документ — договорённость для
владельца backend; код в `02-backend` правит он.

## Конфигурация backend

| Переменная | Значение по умолчанию | Назначение |
|---|---|---|
| `AI_SERVICE_URL` | `http://ai-service:8001` (compose) / `http://localhost:8001` | базовый адрес |
| `AI_SERVICE_TIMEOUT_S` | `60` | таймаут одного запроса инсайта/чата |
| `AI_SERVICE_ENABLED` | `true` | `false` → всегда `mock_ai.py` |

## Вызовы

1. **Инсайт** — `POST /v1/insight` с `news` (= `News` backend + при наличии `full_text`),
   `company` (= `Company` backend; маркеры bool), `role`. Backend берёт из ответа:
   - `card` → `FeedItem.insight` **как есть** (поля совпадают с `Insight` backend);
   - `importance.score` → `FeedItem.importance_score`;
   - `mode == "offline"` → `FeedItem.is_demo = true`, иначе `false`;
   - `traceability`, `request_id`, `latency_ms`, `traceability.models` → `ai_audit_logs`.
2. **Чат** — `POST /v1/ask` с `news`, `card` (= текущий `insight` карточки), `company`,
   `role`, `question`. `answer` → `AskResponse.answer`; `mode` → `is_demo`.
3. **Скоринг ленты** — `POST /v1/score` пакетом по новостям компании и роли, когда нужна
   пересортировка без генерации инсайтов.
4. **Сбор новостей** — `POST /v1/news/collect` с `since` = время последнего успешного
   сбора и `exclude_urls` = URL уже сохранённых новостей за последние 7 дней. Backend
   сохраняет `items` в `news` (id = `items[i].id`, стабильный uuid5 от URL), затем
   генерирует инсайты для нужных пар компания/роль.

## Поведение при ошибках

- Сетевая ошибка, 5xx или таймаут → backend использует `mock_ai.py` и ставит
  `is_demo = true`; в лог — `request_id` из тела ошибки, если он есть.
- `422` → ошибка backend (несовпадение схем), не ретраить.
- Ретраи на стороне backend не нужны: сервис сам ретраит вызовы модели.

## Когда генерировать инсайт

Рекомендуется при появлении новости для каждой пары (компания, роль) с кэшированием в
таблице `insights` (ключ `news_id + company_id + target_role`). Повторный вызов с теми же
входами в режиме `offline` даёт идентичный результат; в режиме `llm` — эквивалентный, но не
побайтно одинаковый.

## Таблица соответствия категорий

`NewsItem.topic` (ai-service) → `news.category` (строка backend): `monetary_policy` →
«Финансы и ДКП», `inflation` → «Инфляция и цены», `labor_market` → «Рынок труда и кадры»,
`regulation_tax` → «Регулирование и налоги», `logistics_trade` → «Логистика и внешняя
торговля», `industry_markets` → «Отрасль и рынки», `consumer_demand` → «Торговля и ритейл»,
`commodities` → «Промышленность и сырьё», `other` → «Прочее». Для собранных новостей
ai-service уже проставляет `category` этой строкой.

## Docker Compose (для `04-infra-db/docker-compose.yml`)

```yaml
  ai-service:
    build:
      context: ../03-ai-service
      dockerfile: Dockerfile
    container_name: alfa-ai-service
    restart: unless-stopped
    environment:
      AI_LLM_BASE_URL: ${AI_LLM_BASE_URL:-}
      AI_LLM_API_KEY: ${AI_LLM_API_KEY:-}
      AI_LLM_MODEL_MAIN: ${AI_LLM_MODEL_MAIN:-}
      AI_LLM_MODEL_FAST: ${AI_LLM_MODEL_FAST:-}
      AI_LLM_MODEL_CHECKER: ${AI_LLM_MODEL_CHECKER:-}
      AI_ARTICLES_DIR: /data/articles
      AI_DATASETS_DIR: /data/datasets
      AI_INDEX_DIR: /data/index
    volumes:
      - ../03-ai-service/data/articles:/data/articles:ro
      - ../03-ai-service/data/datasets:/data/datasets:ro
      - ai_index:/data/index
    ports:
      - "127.0.0.1:8001:8001"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8001/health')"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - alfa-network
```

Backend получает `AI_SERVICE_URL: http://ai-service:8001` и
`depends_on: {ai-service: {condition: service_healthy}}`; `volumes:` дополняется `ai_index:`.
Индекс строится один раз: `docker compose exec ai-service ai-service index-reports`.
