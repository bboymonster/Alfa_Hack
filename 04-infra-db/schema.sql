-- ==============================================================================
-- 04-infra-db: Universal ANSI SQL Schema (PostgreSQL & SQLite compatible)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS companies (
    synthetic_u TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    org_type TEXT,
    okfs_name TEXT,
    company_age_years_gradation TEXT,
    eco_mark_label TEXT,
    mainokved_code TEXT NOT NULL,
    mainokved_name TEXT NOT NULL,
    negativemark REAL DEFAULT 0.0,
    amount_workers_fns_gradation TEXT,
    amount_workers_spark_gradation TEXT,
    cl_type TEXT DEFAULT 'ACTIVE',
    cl_product_rko_mark REAL DEFAULT 0.0,
    cl_product_gar_mark REAL DEFAULT 0.0,
    cl_product_loa_mark REAL DEFAULT 0.0,
    cl_product_lea_mark REAL DEFAULT 0.0,
    cl_product_dep_mark REAL DEFAULT 0.0,
    cl_product_zpp_mark REAL DEFAULT 0.0,
    fts_flag REAL DEFAULT 0.0,
    fts_country_name TEXT,
    factoring_mark REAL DEFAULT 0.0,
    revenue_company REAL NOT NULL DEFAULT 0.0,
    group_id TEXT,
    city TEXT,
    region TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'CEO',
    current_company_id TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_company_id) REFERENCES companies (synthetic_u) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS news (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary_facts TEXT NOT NULL,
    full_text TEXT,
    source TEXT NOT NULL,
    source_url TEXT,
    category TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY,
    news_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    target_role TEXT NOT NULL DEFAULT 'CEO',
    why_it_matters TEXT NOT NULL,
    risks TEXT DEFAULT '[]',
    opportunities TEXT DEFAULT '[]',
    action_item TEXT NOT NULL,
    recommended_bank_product TEXT,
    alfa_bank_position TEXT NOT NULL,
    alfa_report_name TEXT NOT NULL,
    alfa_report_page INTEGER DEFAULT 1,
    alfa_report_url TEXT,
    traceability TEXT DEFAULT '{}',
    importance_score INTEGER DEFAULT 5,
    sentiment TEXT DEFAULT 'neutral',
    risk_level TEXT DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (news_id) REFERENCES news (id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies (synthetic_u) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    payer_id TEXT NOT NULL,
    beneficiary_id TEXT NOT NULL,
    pay_amt REAL NOT NULL DEFAULT 0.0,
    pay_cnt INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS beneficiary_links (
    id TEXT PRIMARY KEY,
    synthetic_f TEXT NOT NULL,
    city_name TEXT,
    rc_name TEXT,
    synthetic_u TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
    user_id TEXT NOT NULL,
    news_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, news_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (news_id) REFERENCES news (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_audit_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    action_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);
