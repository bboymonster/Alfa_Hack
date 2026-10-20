-- ==============================================================================
-- 04-infra-db: PostgreSQL Initial Schema for Alfa News Insights
-- Схема базы данных для сервиса новостной аналитики и персонализированных инсайтов
-- Разработано для кейса хакатона «Альфа Будущее» (Changellenge & АО «Альфа-Банк»)
-- ==============================================================================

-- 1. Подключение необходимых расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Пользовательские типы перечислений (ENUMs)
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('CEO', 'CFO', 'ACCOUNTANT', 'ANALYST', 'ADMIN');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE insight_sentiment AS ENUM ('positive', 'neutral', 'negative');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'critical');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. Таблица компаний-клиентов (на основе датасета df_Uid_data_hack.csv)
CREATE TABLE IF NOT EXISTS companies (
    synthetic_u VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    org_type VARCHAR(100),
    okfs_name VARCHAR(255),
    company_age_years_gradation VARCHAR(64),
    eco_mark_label VARCHAR(64),
    mainokved_code VARCHAR(32) NOT NULL,
    mainokved_name TEXT NOT NULL,
    negativemark NUMERIC(5,2) DEFAULT 0.0,
    amount_workers_fns_gradation VARCHAR(64),
    amount_workers_spark_gradation VARCHAR(64),
    cl_type VARCHAR(64) DEFAULT 'ACTIVE',
    cl_product_rko_mark NUMERIC(3,1) DEFAULT 0.0,
    cl_product_gar_mark NUMERIC(3,1) DEFAULT 0.0,
    cl_product_loa_mark NUMERIC(3,1) DEFAULT 0.0,
    cl_product_lea_mark NUMERIC(3,1) DEFAULT 0.0,
    cl_product_dep_mark NUMERIC(3,1) DEFAULT 0.0,
    cl_product_zpp_mark NUMERIC(3,1) DEFAULT 0.0,
    fts_flag NUMERIC(3,1) DEFAULT 0.0,
    fts_country_name VARCHAR(128),
    factoring_mark NUMERIC(3,1) DEFAULT 0.0,
    revenue_company NUMERIC(18,2) NOT NULL DEFAULT 0.0,
    group_id VARCHAR(64),
    city VARCHAR(128),
    region VARCHAR(128),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска и ранжирования по компаниям
CREATE INDEX IF NOT EXISTS idx_companies_okved ON companies (mainokved_code);
CREATE INDEX IF NOT EXISTS idx_companies_revenue ON companies (revenue_company);
CREATE INDEX IF NOT EXISTS idx_companies_region ON companies (region);
CREATE INDEX IF NOT EXISTS idx_companies_group ON companies (group_id);

-- 4. Таблица пользователей интернет-банка «Альфа-Бизнес»
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'CEO',
    current_company_id VARCHAR(64) REFERENCES companies (synthetic_u) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_company ON users (current_company_id);

-- 5. Таблица новостных событий (внешний поток и макро-факты)
CREATE TABLE IF NOT EXISTS news (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    summary_facts TEXT NOT NULL,
    full_text TEXT,
    source VARCHAR(255) NOT NULL,
    source_url VARCHAR(1000),
    category VARCHAR(100) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_news_published_at ON news (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_category ON news (category);

-- 6. Таблица инсайтов (персонализированная аналитика под компанию и роль)
-- Реализует структуру ответов на 6 вопросов из ТЗ кейса (стр. 14)
CREATE TABLE IF NOT EXISTS insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    news_id UUID NOT NULL REFERENCES news (id) ON DELETE CASCADE,
    company_id VARCHAR(64) NOT NULL REFERENCES companies (synthetic_u) ON DELETE CASCADE,
    target_role user_role NOT NULL DEFAULT 'CEO',
    
    -- Q1-Q4: Бизнес-интерпретация
    why_it_matters TEXT NOT NULL,
    risks JSONB DEFAULT '[]'::jsonb,
    opportunities JSONB DEFAULT '[]'::jsonb,
    action_item TEXT NOT NULL,
    recommended_bank_product VARCHAR(255),
    
    -- Q5: Экспертная позиция Альфа-Банка
    alfa_bank_position TEXT NOT NULL,
    alfa_report_name VARCHAR(255) NOT NULL,
    alfa_report_page INTEGER DEFAULT 1,
    alfa_report_url VARCHAR(500),
    
    -- Q6: Трассируемость и метаданные
    traceability JSONB DEFAULT '{}'::jsonb,
    importance_score INTEGER CHECK (importance_score BETWEEN 1 AND 10) DEFAULT 5,
    sentiment insight_sentiment DEFAULT 'neutral',
    risk_level risk_level DEFAULT 'medium',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_insights_news_company ON insights (news_id, company_id);
CREATE INDEX IF NOT EXISTS idx_insights_role ON insights (target_role);
CREATE INDEX IF NOT EXISTS idx_insights_importance ON insights (importance_score DESC);

-- 7. Платежные связи контрагентов (на основе df_Uid_payment_hack.csv)
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payer_id VARCHAR(64) NOT NULL,
    beneficiary_id VARCHAR(64) NOT NULL,
    pay_amt NUMERIC(18,2) NOT NULL DEFAULT 0.0,
    pay_cnt INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_payer ON payments (payer_id);
CREATE INDEX IF NOT EXISTS idx_payments_beneficiary ON payments (beneficiary_id);

-- 8. Связи физлиц-бенефициаров (на основе df_Fid_Uid_link_hack.csv)
CREATE TABLE IF NOT EXISTS beneficiary_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    synthetic_f VARCHAR(64) NOT NULL,
    city_name VARCHAR(128),
    rc_name VARCHAR(128),
    synthetic_u VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_beneficiary_f ON beneficiary_links (synthetic_f);
CREATE INDEX IF NOT EXISTS idx_beneficiary_u ON beneficiary_links (synthetic_u);

-- 9. Таблица закладок / избранных инсайтов пользователя
CREATE TABLE IF NOT EXISTS favorites (
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    news_id UUID NOT NULL REFERENCES news (id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, news_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites (user_id);

-- 10. Журнал аудита обращений и действий AI-компонента (требование ТЗ стр. 10, 12)
CREATE TABLE IF NOT EXISTS ai_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users (id) ON DELETE SET NULL,
    action_type VARCHAR(100) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON ai_audit_logs (created_at DESC);
