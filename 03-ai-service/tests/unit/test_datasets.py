from pathlib import Path

from ai_service.datasets.store import DatasetStore, build_datasets
from ai_service.schemas.company import CompanyProfile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "datasets"


def test_build_datasets_null_when_missing(tmp_path: Path) -> None:
    store = build_datasets(tmp_path / "nope")
    assert store.available is False
    assert store.top_counterparties("U_1595") == []


def test_get_profile_from_csv() -> None:
    store = DatasetStore(FIXTURES)
    assert store.available
    profile = store.get_profile("U_1595", name="Ритейл")
    assert profile is not None
    assert profile.name == "Ритейл"
    assert profile.mainokved_code == "47.71"
    assert profile.cl_product_loa_mark is True
    assert profile.cl_product_dep_mark is False
    assert profile.fts_flag is True and profile.fts_country_name == "ТУРЦИЯ, НИДЕРЛАНДЫ"
    assert profile.amount_workers_spark_gradation is None  # пустая колонка → None
    assert profile.revenue_company == 16461799989.0
    assert store.get_profile("U_404") is None


def test_merge_missing_fills_only_empty_fields(company_u80: CompanyProfile) -> None:
    store = DatasetStore(FIXTURES)
    sparse = company_u80.model_copy(
        update={"region": None, "amount_workers_fns_gradation": None, "cl_product_lea_mark": False}
    )
    merged, filled = store.merge_missing(sparse)
    assert set(filled) == {
        "amount_workers_fns_gradation",
        "cl_product_lea_mark",
        "group_id",  # в фикстуре компании нет group_id — дополняется из датасета
        "region",
    }
    assert merged.region == "Свердловская область"
    assert merged.amount_workers_fns_gradation == "16-100"
    assert merged.cl_product_lea_mark is True
    assert merged.name == company_u80.name  # имя из запроса не трогаем
    assert merged.revenue_company == company_u80.revenue_company


def test_top_counterparties_sorted_with_okved() -> None:
    store = DatasetStore(FIXTURES)
    items = store.top_counterparties("U_1595", n=3)
    assert [c.synthetic_u for c in items] == ["U_3263", "U_80", "U_9999"]
    assert items[0].direction == "beneficiary" and items[0].pay_amt == 74300000.0
    assert items[1].mainokved_code == "25.61"
    assert items[2].direction == "payer" and items[2].mainokved_code is None
