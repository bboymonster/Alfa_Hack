"""Хранилище датасетов кейса.

Поля компаний (`df_Uid_data_hack.csv`) дополняют профиль из запроса (``merge_missing``),
а платежи (`df_Uid_payment_hack.csv`) дают контрагентов (``top_counterparties``).
Все чтения ленивые и отказоустойчивые: при отсутствии файлов или ошибке парсинга
хранилище ведёт себя как ``NullDatasetStore`` — сервис продолжает работать offline.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Protocol

from ai_service.logging import get_logger
from ai_service.schemas.company import CompanyProfile, Counterparty

log = get_logger(__name__)

# Строковые поля CompanyProfile, которые можно дополнить из CSV (snake_case → столбец CSV).
_OPTIONAL_STR_FIELDS = [
    "org_type",
    "okfs_name",
    "company_age_years_gradation",
    "eco_mark_label",
    "amount_workers_fns_gradation",
    "amount_workers_spark_gradation",
    "cl_type",
    "fts_country_name",
    "group_id",
    "city",
    "region",
]

# Признаки (mark) 0/1, которые дополняются, только когда у профиля их нет (False).
_MARK_FIELDS = [
    "negativemark",
    "cl_product_rko_mark",
    "cl_product_gar_mark",
    "cl_product_lea_mark",
    "cl_product_dep_mark",
    "cl_product_zpp_mark",
    "factoring_mark",
]


def _csv_true(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "1.0", "true", "да", "yes"}
    try:
        return float(value) != 0.0  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


class Datasets(Protocol):
    @property
    def available(self) -> bool: ...

    def merge_missing(self, company: CompanyProfile) -> tuple[CompanyProfile, list[str]]: ...

    def top_counterparties(self, synthetic_u: str, n: int = 5) -> list[Counterparty]: ...


class NullDatasetStore:
    """Датасеты не подключены: профиль и контрагенты берутся только из запроса."""

    @property
    def available(self) -> bool:
        return False

    def merge_missing(self, company: CompanyProfile) -> tuple[CompanyProfile, list[str]]:
        return company, []

    def top_counterparties(self, synthetic_u: str, n: int = 5) -> list[Counterparty]:
        return []


class DatasetStore:
    """Ленивое чтение CSV кейса. Файлы ищутся в ``datasets_dir``."""

    def __init__(self, datasets_dir: Path) -> None:
        self._dir = datasets_dir
        self._loaded = False
        self._companies: dict[str, dict[str, str]] | None = None
        self._payments: Any | None = None

    # ------------------------------------------------------------------ loading
    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self._companies = self._load_companies()
        self._payments = self._load_payments()
        if self._companies is None:
            log.info("datasets.unavailable", dir=str(self._dir))

    def _load_companies(self) -> dict[str, dict[str, str]] | None:
        path = self._dir / "df_Uid_data_hack.csv"
        if not path.exists():
            return None
        try:
            rows: dict[str, dict[str, str]] = {}
            with path.open(encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle, delimiter=";"):
                    rows[row["SYNTHETIC_U"]] = row
            log.info("datasets.companies_loaded", count=len(rows))
            return rows
        except Exception as exc:
            log.warning("datasets.companies_error", error=type(exc).__name__)
            return None

    def _load_payments(self) -> Any | None:
        path = self._dir / "df_Uid_payment_hack.csv"
        if not path.exists():
            return None
        try:
            import pandas as pd

            frame = pd.read_csv(
                path,
                sep=";",
                dtype={"BENEFICIARY": str, "PAYER": str},
                usecols=["BENEFICIARY", "PAYER", "PAY_AMT", "PAY_CNT"],
            )
            log.info("datasets.payments_loaded", rows=len(frame))
            return frame
        except Exception as exc:
            log.warning("datasets.payments_error", error=type(exc).__name__)
            return None

    # ------------------------------------------------------------------ interface
    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._companies is not None

    def get_profile(self, synthetic_u: str, *, name: str | None = None) -> CompanyProfile | None:
        """Профиль из CSV; пустые необязательные поля нормализует CompanyProfile."""
        self._ensure_loaded()
        row = (self._companies or {}).get(synthetic_u)
        if row is None:
            return None
        data: dict[str, Any] = {
            column.lower(): value
            for column, value in row.items()
            if column.lower() in CompanyProfile.model_fields
        }
        data.update(synthetic_u=synthetic_u, name=name or synthetic_u)
        return CompanyProfile.model_validate(data)

    def merge_missing(self, company: CompanyProfile) -> tuple[CompanyProfile, list[str]]:
        self._ensure_loaded()
        if self._companies is None:
            return company, []
        row = self._companies.get(company.synthetic_u)
        if row is None:
            return company, []

        updates: dict[str, object] = {}
        filled: list[str] = []

        for field in _OPTIONAL_STR_FIELDS:
            if getattr(company, field) in (None, ""):
                value = (row.get(field.upper()) or "").strip()
                if value:
                    updates[field] = value
                    filled.append(field)

        for field in _MARK_FIELDS:
            if not getattr(company, field) and _csv_true(row.get(field.upper())):
                updates[field] = True
                filled.append(field)

        if company.revenue_company == 0:
            raw = (row.get("REVENUE_COMPANY") or "").strip()
            if raw:
                try:
                    updates["revenue_company"] = float(raw)
                    filled.append("revenue_company")
                except ValueError:
                    pass

        if not filled:
            return company, []
        return company.model_copy(update=updates), filled

    def top_counterparties(self, synthetic_u: str, n: int = 5) -> list[Counterparty]:
        self._ensure_loaded()
        payments = self._payments
        if payments is None:
            return []
        try:
            import pandas as pd

            frame = payments
            incoming = (
                frame[frame["BENEFICIARY"] == synthetic_u]
                .groupby("PAYER", as_index=False)
                .agg(pay_amt=("PAY_AMT", "sum"), pay_cnt=("PAY_CNT", "sum"))
                .rename(columns={"PAYER": "counterparty"})
            )
            incoming["direction"] = "payer"
            outgoing = (
                frame[frame["PAYER"] == synthetic_u]
                .groupby("BENEFICIARY", as_index=False)
                .agg(pay_amt=("PAY_AMT", "sum"), pay_cnt=("PAY_CNT", "sum"))
                .rename(columns={"BENEFICIARY": "counterparty"})
            )
            outgoing["direction"] = "beneficiary"
            merged = pd.concat([incoming, outgoing], ignore_index=True)
            merged = merged.sort_values("pay_amt", ascending=False).head(n)

            companies = self._companies or {}
            result: list[Counterparty] = []
            for _, item in merged.iterrows():
                uid = str(item["counterparty"])
                company_row = companies.get(uid, {})
                result.append(
                    Counterparty(
                        synthetic_u=uid,
                        direction=item["direction"],
                        pay_amt=float(item["pay_amt"]),
                        pay_cnt=int(item["pay_cnt"]),
                        mainokved_code=(company_row.get("MAINOKVED_CODE") or None),
                        mainokved_name=(company_row.get("MAINOKVED_NAME") or None),
                    )
                )
            return result
        except Exception as exc:
            log.warning("datasets.counterparties_error", error=type(exc).__name__)
            return []


def build_datasets(datasets_dir: Path) -> Datasets:
    """Фабрика: реальный ``DatasetStore`` поверх папки с CSV кейса."""
    return DatasetStore(datasets_dir)
