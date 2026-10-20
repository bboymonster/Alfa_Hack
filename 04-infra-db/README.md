# 04. Infra & Database — База данных, Контейнеризация и Сиды

## Зона ответственности
Проектирование базы данных для объединения новостей и инсайтов, docker-compose инфраструктура, сидирование демонстрационными данными из ТЗ и подготовка проекта к сдаче.

---

## Схема базы данных (Relational Schema)

Схема оптимизирована для быстрой выдачи объединенных карточек **«Новость-Инсайт»**:

- **`companies`** (справочник клиентов на базе `df_Uid_data_hack.csv`):
  - `synthetic_u` (PK): идентификатор компании
  - `name`: название компании для демо-интерфейса
  - `mainokved_name`: отрасль
  - `revenue_company`: годовая выручка (> 15 млрд руб. для крупного бизнеса)
  - `fts_flag`: наличие импорта/экспорта в ФТС (0/1)
  - `cl_product_loa_mark`: наличие кредитов (0/1)
  - `cl_product_gar_mark`: наличие банковских гарантий (0/1)
  - `cl_product_rko_mark`: наличие РКО (0/1)
  - `region`: регион регистрации

- **`users`** (пользователи интернет-банка):
  - `id` (PK), `email`, `hashed_password`
  - `full_name`: ФИО
  - `role`: роль ЛПР (`CEO`, `CFO`, `ACCOUNTANT`)
  - `current_company_id` (FK -> companies.synthetic_u)

- **`news`** (новости):
  - `id` (PK), `title`, `summary_facts`, `source`, `source_url`, `category`, `published_at`

- **`insights`** (персонализированные инсайты под связку новость + компания + роль):
  - `id` (PK)
  - `news_id` (FK -> news.id ON DELETE CASCADE)
  - `company_id` (FK -> companies.synthetic_u)
  - `target_role`: `CEO` | `CFO` | `ACCOUNTANT` | `ALL`
  - `why_it_matters`: почему важно для бизнеса клиента
  - `risks`: JSON-список рисков
  - `opportunities`: JSON-список возможностей
  - `action_item`: рекомендуемый следующий шаг
  - `alfa_bank_position`: цитата и позиция экспертов Альфа-Банка
  - `alfa_report_name`: название отчета банка
  - `alfa_report_page`: номер страницы
  - `traceability_json`: сработавшие признаки и скоринг

- **`favorites`** (закладки):
  - `user_id` (FK -> users.id), `news_id` (FK -> news.id)

---

## Сиды демонстрационных данных (`seed_data.py`)
Включают в себя:
1. Тестовые учетные записи для жюри (`alfa-hack-2026` / `ceo@alfabusiness.ru`).
2. Профили компаний из датасета кейса (с выручкой > 15 млрд руб. и средний бизнес).
3. Готовые карточки «Новость-Инсайт» по ключевым отчетам Альфа-Банка:
   - Сохранение ключевой ставки на уровне 14% (кредитная нагрузка vs факторинг).
   - Инфляция 25–31 августа и региональные тренды.
   - Макростатистика 7М26 по рынку труда (дефицит кадров и рост ФОТ).

---

## Развертывание через Docker Compose
```bash
docker compose up --build -d
```
Поднимает сервисы: `db` (PostgreSQL), `backend` (FastAPI), `frontend` (React/Next.js).
