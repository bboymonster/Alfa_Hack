#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04-infra-db: Database Healthcheck & Feed Query Test
Скрипт диагностики и проверки базы данных:
- Проверяет доступность БД (PostgreSQL или SQLite)
- Выводит сводную статистику по строкам в таблицах
- Тестирует ключевой запрос ленты «Новость-Инсайт» (/api/feed)
"""

import os
import sys
import json
import sqlite3

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(SCRIPT_DIR, "alfa_business.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
        try:
            import psycopg2
            return psycopg2.connect(DATABASE_URL), "postgres"
        except Exception:
            pass
    return sqlite3.connect(SQLITE_DB_PATH), "sqlite"


def run_diagnostics():
    print("=" * 70)
    print(" 🔍 ДИАГНОСТИКА ХРАНИЛИЩА (04-infra-db: Alfa News Insights)")
    print("=" * 70)

    conn, db_type = get_conn()
    cursor = conn.cursor()
    print(f" • Тип подключения: {db_type.upper()}")

    # Проверка таблиц
    tables = ["companies", "users", "news", "insights", "payments", "favorites", "ai_audit_logs"]
    print("\n[Таблицы и объем данных]:")
    total_records = 0
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cursor.fetchone()[0]
            total_records += cnt
            print(f"   ✓ {t:<16} : {cnt:>4} записей")
        except Exception as e:
            print(f"   ✗ {t:<16} : ОШИБКА ({e})")

    # Тестирование спаренного запроса ленты «Новость-Инсайт»
    print("\n[Тестовый запрос ленты /api/feed для компании 'U_1595' (Роль: CEO)]:")
    feed_query = """
    SELECT 
        n.title,
        n.category,
        n.published_at,
        i.target_role,
        i.why_it_matters,
        i.alfa_report_name,
        i.alfa_report_page,
        i.action_item,
        i.importance_score
    FROM news n
    JOIN insights i ON n.id = i.news_id
    WHERE i.company_id = ? AND (i.target_role = ? OR i.target_role = 'ALL')
    ORDER BY i.importance_score DESC, n.published_at DESC
    LIMIT 2
    """ if db_type == "sqlite" else """
    SELECT 
        n.title,
        n.category,
        n.published_at,
        i.target_role,
        i.why_it_matters,
        i.alfa_report_name,
        i.alfa_report_page,
        i.action_item,
        i.importance_score
    FROM news n
    JOIN insights i ON n.id = i.news_id
    WHERE i.company_id = %s AND (i.target_role = %s OR i.target_role = 'ALL')
    ORDER BY i.importance_score DESC, n.published_at DESC
    LIMIT 2
    """
    
    cursor.execute(feed_query, ("U_1595", "CEO"))
    rows = cursor.fetchall()

    if rows:
        for idx, r in enumerate(rows, 1):
            print(f"\n   --- Карточка #{idx} (Важность: {r[8]}/10) ---")
            print(f"   📰 Новость: {r[0]}")
            print(f"   🏷 Категория: {r[1]} | Дата: {r[2]}")
            print(f"   💡 Почему важно: {r[4]}")
            print(f"   🏦 Отчет Альфа-Банка: «{r[5]}», стр. {r[6]}")
            print(f"   ⚡ Действие: {r[7]}")
    else:
        print("   (Записей по фильтру не найдено. Запустите python seed.py)")

    conn.close()
    print("\n" + "=" * 70)
    print(" ✅ Диагностика успешно завершена!")
    print("=" * 70)


if __name__ == "__main__":
    run_diagnostics()
