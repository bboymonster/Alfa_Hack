# 02. Backend — Серверный API и бизнес-логика

> **Модуль Участника 2: Backend Developer**
> FastAPI-сервер, к которому подключается `01-frontend`. Данные хранит в памяти
> (демо-режим), а инсайты и ответы чата получает из `03-ai-service` с честным
> fallback на детерминированную заглушку.

---

## 🎯 Зона ответственности и текущая версия

Backend принимает запросы интерфейса, проверяет пользователя и возвращает ленту **«Новость — Инсайт»** с учётом компании и роли.

В версии `0.1.0` уже работают:

- регистрация, вход с JWT-токеном и получение профиля;
- список доступных компаний;
- лента, фильтры по компании, роли и категории, разбивка на страницы;
- подробная карточка, добавление и удаление закладок;
- вопрос по новости — через `03-ai-service` (`POST /v1/ask`) с fallback на заглушку;
- Swagger `/docs`, описание API `/openapi.json` и CORS для локального frontend.

**Хранение.** Компании, новости и инсайты находятся в памяти одного процесса
(`MemoryStore`), регистрация и закладки сбрасываются при перезапуске. Реляционная
схема и сидирование PostgreSQL вынесены в модуль `04-infra-db` (артефакт модели
данных); в демо-режиме запуска backend обходится без БД.

**AI.** Инсайты и чат приходят из `03-ai-service` (`app/ai_client.py`). Без ключа
`AI_LLM_API_KEY` сервис работает в режиме `offline` — детерминированные инсайты с
трассировкой агента и `is_demo: true`. С ключом — реальные модели из Приложения 3
ТЗ и `is_demo: false`. При недоступности AI-сервиса каждый запрос автоматически
возвращает заглушку из `mock_ai.py`.

Позиция банка (`alfa_bank_position`) заполняется, только если у AI-сервиса построен
индекс отчётов Альфа-Банка; иначе остаётся `null` и в интерфейсе честно помечается
как «не найдена». Придуманные тексты не выдаются за позицию банка.

---

## 📁 Структура

```text
02-backend/
├── app/
│   ├── main.py          # Создание приложения, CORS и /health
│   ├── config.py        # Настройки из окружения и .env
│   ├── schemas.py       # Форматы запросов и ответов
│   ├── auth.py          # Регистрация, вход и проверка JWT
│   ├── feed.py          # Компании, лента, закладки и чат
│   ├── store.py         # Тестовые данные и хранение в памяти
│   ├── ai_client.py     # Клиент 03-ai-service с fallback на mock_ai
│   └── mock_ai.py       # Детерминированная заглушка инсайтов и чата
├── examples/
│   └── frontend-client.js # Готовые функции fetch для frontend
├── tests/               # Проверки сценариев API
├── requirements.in      # Основные зависимости
├── requirements.txt     # Зафиксированные версии для установки
├── requirements-dev.in  # Зависимости для разработки
├── requirements-dev.txt # Зафиксированные версии для разработки
├── .env.example         # Необязательные локальные настройки
└── Dockerfile           # Отдельный запуск backend в контейнере
```

---

## 🚀 Быстрый старт без Docker

Нужен **Python 3.11 или новее**. Проверено на Python 3.13.

Из корня репозитория:

```bash
cd 02-backend
python -m venv .venv
```

Активация окружения на macOS / Linux:

```bash
source .venv/bin/activate
```

На Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Установка и запуск:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Если команда Python у вас называется `python3`, используйте её при создании окружения. После активации доступна команда `python`.

Откройте:

- **Swagger, где можно отправлять запросы:** <http://localhost:8000/docs>
- **Проверка работы сервера:** <http://localhost:8000/health>
- **Машиночитаемый контракт API:** <http://localhost:8000/openapi.json>

Копировать `.env` для первого запуска не требуется. Без заданного `JWT_SECRET_KEY` создаётся временный ключ: токены перестают действовать после перезапуска. Если нужен свой ключ или другой адрес frontend, скопируйте `.env.example` в `.env` и измените значения.

Порядок настроек: переменные процесса → `02-backend/.env` → корневой `.env` → значения по умолчанию. `CORS_ORIGINS` задаётся JSON-массивом адресов.

### Запуск только backend в Docker

Из папки `02-backend`:

```bash
docker build -t alfa-backend:local .
docker run --rm --name alfa-backend -p 127.0.0.1:8000:8000 alfa-backend:local
```

Полный стек (frontend + backend + ai-service) запускается корневым
`docker-compose.yml` — см. главный [README](../README.md). Используйте один
процесс / worker, поскольку память между процессами не разделяется. Порт контейнера
фиксирован: `8000`. Внутри compose `AI_SERVICE_URL` задаётся как
`http://ai-service:8001`.

---

## 🔑 Вход и доступ к компаниям

Все бизнес-запросы требуют заголовок:

```http
Authorization: Bearer <access_token>
```

Без входа доступны `/health`, `/docs`, `/redoc`, `/openapi.json`, регистрация и вход.

| Логин в поле `email` | Пароль | Роль по умолчанию |
|---|---|---|
| `alfa-hack-2026` | `password123` | `CEO` |
| `ceo@alfabusiness.ru` | `password123` | `CEO` |
| `cfo@alfabusiness.ru` | `password123` | `CFO` |
| `accountant@alfabusiness.ru` | `password123` | `ACCOUNTANT` |

У этих аккаунтов есть доступ ко всем трём демо-компаниям. При регистрации нового аккаунта доступ выдаётся только к выбранной `company_id` (по умолчанию `U_1595`). Это учебный механизм выдачи доступа; реальное подтверждение связи пользователя с компанией ещё предстоит реализовать.

Пароли хранятся в памяти в виде Argon2-хешей. JWT подписывается HS256, срок действия по умолчанию — сутки. Обновления токена и серверного отзыва сессии пока нет: после истечения срока нужно войти повторно.

### Проверка через Swagger

1. Откройте `POST /api/auth/login` → **Try it out**.
2. Отправьте `{"email":"alfa-hack-2026","password":"password123"}`.
3. Скопируйте `access_token` из ответа.
4. Нажмите **Authorize** сверху и вставьте только токен, без слова `Bearer`.
5. Теперь можно вызывать `/api/companies`, `/api/feed` и остальные защищённые маршруты.

---

## 🔌 Контракт для frontend

Базовый адрес при локальном запуске: `http://localhost:8000`. Тела запросов передаются как JSON с `Content-Type: application/json`.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/health` | Проверка сервера и режима (AI-сервис / mock) |
| `POST` | `/api/auth/register` | Создать демо-аккаунт, получить токен и профиль |
| `POST` | `/api/auth/login` | Получить токен и профиль |
| `GET` | `/api/auth/me` | Текущий профиль и `allowed_company_ids` |
| `GET` | `/api/companies` | JSON-массив доступных компаний |
| `GET` | `/api/feed` | Объект со списком карточек и пагинацией |
| `GET` | `/api/feed/{item_id}` | Одна карточка из ленты |
| `POST` | `/api/feed/{item_id}/favorite` | Установить состояние закладки |
| `POST` | `/api/feed/{item_id}/ask` | Получить JSON с ответом AI-сервиса (или заглушки) |

### Регистрация и вход

Вход:

```json
{"email": "alfa-hack-2026", "password": "password123"}
```

Регистрация:

```json
{
  "email": "developer@example.com",
  "password": "my-password-123",
  "full_name": "Участник команды",
  "role": "CFO",
  "company_id": "U_1595"
}
```

Оба маршрута возвращают `access_token`, `token_type: "bearer"`, `expires_in` (секунды) и `user`. Регистрация отвечает `201`, вход — `200`. Поле логина называется `email`, включая специальный логин `alfa-hack-2026`. Пароль при регистрации — от 8 до 128 символов.

### Компании и лента

В компании используйте `synthetic_u` как значение селектора и параметр `company_id`. Есть `U_1595`, `U_1465` и полностью вымышленная `DEMO_LOCAL`. Последняя нужна для сравнения: у неё нет кредитных продуктов и признака внешнеторговой деятельности.

```http
GET /api/feed?company_id=U_1595&role=CFO&page=1&page_size=10
```

| Параметр | Значение по умолчанию | Что делает |
|---|---|---|
| `company_id` | `current_company_id` пользователя | Выбирает компанию |
| `role` | Роль пользователя | `CEO`, `CFO` или `ACCOUNTANT` |
| `category` | Все категории | Точное название категории из карточки |
| `page` | `1` | Номер страницы, от 1 |
| `page_size` | `10` | Количество карточек, от 1 до 100 |
| `favorites_only` | `false` | Показывать только закладки |

Ответ ленты — объект с полями `items`, `total`, `page`, `page_size`, `total_pages`, `is_demo`. `total` считается после фильтрации и до разбивки на страницы. За последней страницей вернётся пустой `items`. При отсутствии результатов `total_pages` равен `0`.

Каждая карточка содержит:

- `id`, `company_id`, `role` — идентификатор и контекст карточки;
- `news` — `id`, `title`, `summary_facts`, `source`, `source_url`, `published_at`, `category`;
- `insight` — `why_it_matters`, `risks`, `opportunities`, `action_item`, `alfa_bank_position`, `alfa_report_name`, `alfa_report_page`, `alfa_report_url`, `traceability`, а также опциональные `agent_steps`, `self_check`, `confidence`, `mode` (агентная трассировка из AI-сервиса);
- `importance_score` — демонстрационная важность от 1 до 10, сортировка по убыванию;
- `is_favorite`, `is_demo`.

В `traceability` есть массивы `matched_company_features` и `verified_sources`. Все поля отчёта и позиции банка, а также `news.source_url`, могут быть `null`: в интерфейсе нужен вариант «источник ещё не подключён». Даты имеют часовой пояс UTC.

Используйте `items[i].id` для деталей, чата и закладок, **не `news.id`**. ID карточки учитывает компанию и роль и остаётся одинаковым между запусками этой версии. После смены компании или роли получайте свежую ленту. Эти query-параметры не изменяют профиль пользователя.

### Закладки

```http
POST /api/feed/{item_id}/favorite
```

```json
{"is_favorite": true}
```

Для удаления отправьте `false`. Ответ: `{"id":"...","is_favorite":true}`. Повторная отправка `true` оставляет закладку включённой. Для экрана избранного используйте `/api/feed?favorites_only=true` с выбранными компанией и ролью.

Как в текущей схеме БД, закладка привязана к **пользователю и новости**, поэтому сохраняется при переключении роли и компании, если эта новость есть в новой ленте. Закладки другого пользователя не видны.

### Чат

```http
POST /api/feed/{item_id}/ask
```

```json
{"question": "Как это влияет на нашу компанию?"}
```

Ответ содержит `feed_item_id`, `answer` и `is_demo`. При подключённом AI-сервисе
ответ формируется моделью (`is_demo: false` в режиме `llm`), при его недоступности —
заглушкой (`is_demo: true`). Сейчас это один JSON-ответ, **без стриминга и истории
переписки**. Вопрос — от 1 до 2000 символов после удаления пробелов по краям.
Потоковый протокол нужно отдельно согласовать с frontend и AI-разработчиком.

### Ошибки

| Код | Причина |
|---|---|
| `401` | Нет токена, токен недействителен или истёк, неверный логин/пароль |
| `403` | Нет доступа к выбранной компании или её карточке |
| `404` | Компания или карточка не найдена |
| `409` | Email уже зарегистрирован |
| `422` | Неправильные поля, роль, номер страницы или пустой вопрос |

Обычная ошибка выглядит как `{"detail":"Компания не найдена."}`. Для `422` поле `detail` содержит массив ошибок валидации. Проверяйте HTTP-код: ответ с ошибкой тоже является JSON.

---

## 🖥 Подключение frontend

CORS по умолчанию разрешает `localhost` и `127.0.0.1` на портах `3000` и `5173`, включая заголовок `Authorization`. Cookies не используются, `credentials: "include"` не требуется. Другой адрес добавьте в `CORS_ORIGINS` и перезапустите backend.

Готовые функции находятся в [examples/frontend-client.js](examples/frontend-client.js). Файл можно скопировать в `01-frontend` и импортировать в браузерном коде:

```javascript
import { createApi } from "./frontend-client.js";

const api = createApi("http://localhost:8000");
const session = await api.login("alfa-hack-2026", "password123");
const companies = await api.companies();
const feed = await api.feed({ company_id: companies[0].synthetic_u, role: "CFO" });

const card = feed.items[0];
await api.setFavorite(card.id, true);
const reply = await api.ask(card.id, "Что проверить в первую очередь?");
console.log(session.user, feed.items, reply.answer);
```

Создавайте один экземпляр `api` на приложение. Клиент хранит токен только в памяти; после обновления страницы потребуется повторный вход. Ошибки приходят как `ApiError` с полями `status` и `detail`.

Если интерфейс открыт на другом компьютере, `localhost` указывает на компьютер пользователя. Для первого подключения удобнее каждому запустить backend локально. Для общей машины отдельно согласуйте её адрес, запуск на `0.0.0.0` и разрешённый origin. В браузерном запросе имя Docker-сервиса `backend` не заменяет доступный пользователю адрес.

---

## 🧪 Проверки

Из активированного окружения в `02-backend`:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Тесты проходят путь от входа до ленты, закладки и чата. Также проверяют поддельные и просроченные JWT, доступ к чужой компании, разделение закладок пользователей, фильтры, страницы и CORS.

Зависимости фиксируются в `requirements*.txt`. При намеренном обновлении меняйте `.in` и пересобирайте списки через `uv` на Python 3.13:

```bash
uv pip compile requirements.in --python 3.13 --output-file requirements.txt
uv pip compile requirements-dev.in --constraint requirements.txt --python 3.13 --output-file requirements-dev.txt
```

---

## 🤝 Объединение с командой

**С `03-ai-service` (подключено):** `app/ai_client.py` вызывает `POST /v1/insight`
(обогащение ленты фоном) и `POST /v1/ask` (чат), преобразуя `card` из ответа в
публичный `Insight` и проксируя агентную трассировку (`agent_steps`, `self_check`,
`confidence`, `mode`). Контракт и поведение при ошибках — в
[`specs/001-ai-service/contracts/backend-integration.md`](../specs/001-ai-service/contracts/backend-integration.md).
Настройки: `AI_SERVICE_URL`, `AI_SERVICE_TIMEOUT_S`, `AI_SERVICE_ENABLED`.

**С `04-infra-db`:** заменить `MemoryStore` на работу с согласованной БД, сохранив
форматы ответов. Сопоставления: `Company.synthetic_u` → `companies.synthetic_u`,
`FeedItem.id` → `insights.id`, `FeedItem.news.id` → `news.id`, закладка →
`(user_id, news_id)`. Пользовательские доступы к нескольким компаниям требуют
отдельного решения: в текущей схеме есть `current_company_id`, а таблицы связей
доступов ещё нет.

**До полноценного демо:** подключить постоянное хранение пользователей/закладок и
журнал вызовов AI (`ai_audit_logs`), а также сбор реальных новостей через
`POST /v1/news/collect` с сохранением в таблицу `news`.

### Сторонние компоненты этой версии

FastAPI, Pydantic, pydantic-settings, PyJWT и pwdlib — MIT; Uvicorn — BSD-3-Clause; email-validator — Unlicense; argon2-cffi — MIT. Для разработки используются pytest, HTTPX2 и Ruff. Точные версии и транзитивные зависимости находятся в `requirements*.txt`. Соседний общий `THIRD_PARTY_NOTICES.md` перечисляет компоненты всего проекта, в том числе ещё не подключённые здесь.
