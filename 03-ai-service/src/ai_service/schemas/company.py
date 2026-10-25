from typing import Literal

from pydantic import BaseModel, Field

from ai_service.schemas.common import Mark, OptStr

LARGE_BUSINESS_REVENUE = 15_000_000_000.0


class Counterparty(BaseModel):
    synthetic_u: str
    direction: Literal["payer", "beneficiary"] = Field(
        description="Роль контрагента относительно компании: payer платит ей, beneficiary получает"
    )
    pay_amt: float = Field(ge=0)
    pay_cnt: int = Field(ge=0)
    mainokved_code: OptStr = None
    mainokved_name: OptStr = None


class CompanyProfile(BaseModel):
    """Профиль клиента: поля датасета df_Uid_data_hack.csv (snake_case как в backend)."""

    synthetic_u: str = Field(min_length=1)
    name: str = Field(min_length=1)
    org_type: OptStr = None
    okfs_name: OptStr = None
    company_age_years_gradation: OptStr = None
    eco_mark_label: OptStr = None
    mainokved_code: str = Field(min_length=1)
    mainokved_name: str = Field(min_length=1)
    negativemark: Mark = False
    amount_workers_fns_gradation: OptStr = None
    amount_workers_spark_gradation: OptStr = None
    cl_type: OptStr = None
    cl_product_rko_mark: Mark = False
    cl_product_gar_mark: Mark = False
    cl_product_loa_mark: Mark
    cl_product_lea_mark: Mark = False
    cl_product_dep_mark: Mark = False
    cl_product_zpp_mark: Mark = False
    fts_flag: Mark
    fts_country_name: OptStr = None
    factoring_mark: Mark = False
    revenue_company: float = Field(ge=0)
    group_id: OptStr = None
    city: OptStr = None
    region: OptStr = None
    counterparties: list[Counterparty] = []

    @property
    def is_large_business(self) -> bool:
        return self.revenue_company >= LARGE_BUSINESS_REVENUE

    @property
    def industry_prefix(self) -> str:
        return self.mainokved_code.split(".")[0][:2]

    @property
    def revenue_human(self) -> str:
        billions = self.revenue_company / 1_000_000_000
        if billions >= 1:
            return f"{billions:.2f} млрд ₽".replace(".", ",")
        millions = self.revenue_company / 1_000_000
        return f"{millions:.0f} млн ₽"

    @property
    def workers_label(self) -> str | None:
        return self.amount_workers_fns_gradation or self.amount_workers_spark_gradation
