# 04. Infra & Database — База данных, Контейнеризация и Инфраструктура

## Зона ответственности
Проектирование схемы базы данных, управление миграциями, контейнеризация проекта через Docker, настройка окружения и подготовка демонстрационных данных.

---

## Основной функционал

### 1. Схема базы данных (Database Schema)
Реляционная структура данных (PostgreSQL / SQLite):

- **Таблица `users`**:
  - `id`: UUID / Primary Key
  - `email`: VARCHAR(255), UNIQUE, NOT NULL
  - `hashed_password`: VARCHAR(255), NOT NULL
  - `full_name`: VARCHAR(150)
  - `role`: ENUM ('user', 'admin') DEFAULT 'user'
  - `created_at`: TIMESTAMP

- **Таблица `news`**:
  - `id`: UUID / Primary Key
  - `title`: VARCHAR(500), NOT NULL
  - `content`: TEXT, NOT NULL
  - `source`: VARCHAR(255)
  - `source_url`: VARCHAR(1000)
  - `category`: VARCHAR(100)
  - `published_at`: TIMESTAMP
  - `created_at`: TIMESTAMP

- **Таблица `insights`**:
  - `id`: UUID / Primary Key
  - `news_id`: UUID, FOREIGN KEY -> news(id) ON DELETE CASCADE
  - `summary`: TEXT (краткая выжимка TL;DR)
  - `sentiment`: VARCHAR(50) (positive, neutral, negative)
  - `importance_score`: INTEGER (1..10)
  - `key_takeaways`: JSON / TEXT[]
  - `risks`: JSON / TEXT[]
  - `opportunities`: JSON / TEXT[]
  - `action_items`: JSON / TEXT[]
  - `created_at`: TIMESTAMP

- **Таблица `favorites`**:
  - `user_id`: UUID, FOREIGN KEY -> users(id) ON DELETE CASCADE
  - `news_id`: UUID, FOREIGN KEY -> news(id) ON DELETE CASCADE
  - PRIMARY KEY (user_id, news_id)
  - `created_at`: TIMESTAMP

### 2. Контейнеризация (Docker & Docker Compose)
- Подготовка `docker-compose.yml`:
  - `frontend`: сборка/запуск интерфейса.
  - `backend`: запуск FastAPI / Node.js сервера.
  - `db`: образ PostgreSQL с пробросом volume для персистентности данных.
  - *(Опционально)* `ai-service`: отдельный контейнер для локальной LLM (Ollama) или микросервиса.

### 3. Сиды данных (Seed Data)
- Скрипт `seed_data.py` / `seed.sql`:
  - Создание тестового пользователя (`test@example.com` / `password123`).
  - Наполнение базы 10–15 актуальными новостями с качественными предрасчитанными инсайтами, чтобы фронтенд и бэкенд могли работать сразу без обязательного подключения платных API-ключей.

### 4. Управление окружением
- Шаблон `.env.example` с подробным описанием всех необходимых ключей:
  - `DATABASE_URL`
  - `JWT_SECRET_KEY`
  - `OPENAI_API_KEY` / `GEMINI_API_KEY`
  - `BACKEND_CORS_ORIGINS`
