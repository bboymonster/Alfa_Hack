#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04-infra-db: Sample Data Exporter
Утилита для экспорта компактных сэмплов из тяжелых датасетов (30+ МБ CSV)
в легкие JSON-файлы для использования фронтендом, бэкендом и AI-модулем.
"""

import os
import sys
import json
import pandas as pd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATASETS_DIR = os.path.join(PROJECT_ROOT, "datasets")
SAMPLES_DIR = os.path.join(SCRIPT_DIR, "samples")

UID_CSV = os.path.join(DATASETS_DIR, "df_Uid_data_hack.csv")
PAYMENTS_CSV = os.path.join(DATASETS_DIR, "df_Uid_payment_hack.csv")


def export_samples():
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    print("=" * 70)
    print(" 📦 ЭКСПОРТ ДЕМОНСТРАЦИОННЫХ СЭМПЛОВ (04-infra-db)")
    print("=" * 70)

    if not os.path.exists(UID_CSV):
        print(f" [!] Файл {UID_CSV} не найден. Пропуск выгрузки.")
        return

    print(" • Чтение df_Uid_data_hack.csv...")
    df_uid = pd.read_csv(UID_CSV, sep=";", encoding="utf-8")

    # Отбираем 10 крупнейших компаний (> 15 млрд руб.)
    large = df_uid[df_uid["REVENUE_COMPANY"] >= 15_000_000_000].head(10)

    # Отбираем 15 интересных компаний среднего и малого бизнеса
    medium = df_uid[
        (df_uid["REVENUE_COMPANY"] < 15_000_000_000) & 
        (df_uid["REVENUE_COMPANY"] > 500_000_000) &
        (df_uid["CL_PRODUCT_LOA_MARK"] == 1.0)
    ].head(15)

    sample_companies_df = pd.concat([large, medium], ignore_index=True)
    sample_companies = sample_companies_df.to_dict(orient="records")

    companies_json_path = os.path.join(SAMPLES_DIR, "sample_companies.json")
    with open(companies_json_path, "w", encoding="utf-8") as f:
        json.dump(sample_companies, f, ensure_ascii=False, indent=2)
    print(f" ✓ Экспортировано {len(sample_companies)} компаний -> {companies_json_path}")

    # Платежи
    if os.path.exists(PAYMENTS_CSV):
        print(" • Чтение df_Uid_payment_hack.csv...")
        df_pay = pd.read_csv(PAYMENTS_CSV, sep=";", nrows=50000)
        uids = set(sample_companies_df["SYNTHETIC_U"])
        
        # Находим транзакции, связанные с отобранными компаниями
        linked_pay = df_pay[df_pay["PAYER"].isin(uids) | df_pay["BENEFICIARY"].isin(uids)].head(50)
        if len(linked_pay) < 10:
            linked_pay = df_pay.head(50)
            
        payments_json = linked_pay.to_dict(orient="records")
        payments_json_path = os.path.join(SAMPLES_DIR, "sample_payments.json")
        with open(payments_json_path, "w", encoding="utf-8") as f:
            json.dump(payments_json, f, ensure_ascii=False, indent=2)
        print(f" ✓ Экспортировано {len(payments_json)} связей платежей -> {payments_json_path}")

    print("\n" + "=" * 70)
    print(" ✅ Сэмплы данных успешно сохранены в 04-infra-db/samples/")
    print("=" * 70)


if __name__ == "__main__":
    export_samples()
