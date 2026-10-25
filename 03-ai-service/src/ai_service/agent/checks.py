"""Правила самопроверки: противоречия профилю и неподтверждённые утверждения.

Проверяются утверждения о компании (q2) и риски (q3_risks): если текст говорит о
признаке, которого у компании нет (значение «0»), и рядом нет отрицания — нарушение.
Позиция банка принимается только с дословной цитатой из найденного фрагмента.
"""

import re
from dataclasses import dataclass

from ai_service.agent.context import DraftContext
from ai_service.schemas.insight import SixQuestions

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")

# Ключевые слова, которые утверждают наличие признака у компании.
FEATURE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "CL_PRODUCT_LOA_MARK": ("кредит", "долг", "займ", "заём", "рефинансир", "процентн"),
    "FTS_FLAG": ("импорт", "экспорт", "таможн", "внешнеторг", "зарубеж", "валютн"),
    "CL_PRODUCT_ZPP_MARK": ("зарплатн", "зарплатного проекта"),
    "CL_PRODUCT_DEP_MARK": ("депозит", "овернайт"),
    "CL_PRODUCT_LEA_MARK": ("лизинг",),
    "FACTORING_MARK": ("факторинг",),
    "CL_PRODUCT_GAR_MARK": ("гаранти",),
}

NEGATION_MARKERS: tuple[str, ...] = (
    "нет",
    "отсутств",
    "=0",
    "= 0",
    "не имеет",
    "не ведёт",
    "не ведет",
    "без ",
    "косвенн",
    "не использует",
)

# Признаки компании, значение которых «0» делает утверждение противоречием.
_FLAG_FIELDS = {
    "CL_PRODUCT_LOA_MARK": "cl_product_loa_mark",
    "FTS_FLAG": "fts_flag",
    "CL_PRODUCT_ZPP_MARK": "cl_product_zpp_mark",
    "CL_PRODUCT_DEP_MARK": "cl_product_dep_mark",
    "CL_PRODUCT_LEA_MARK": "cl_product_lea_mark",
    "FACTORING_MARK": "factoring_mark",
    "CL_PRODUCT_GAR_MARK": "cl_product_gar_mark",
}


@dataclass(frozen=True)
class Violation:
    code: str
    location: str  # "q2[0]", "q3_risks[1]", "q5", "q1"
    message: str

    def as_text(self) -> str:
        return f"{self.location}: {self.message}"


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _mentions_missing_feature(sentence: str, ctx: DraftContext) -> str | None:
    lowered = sentence.lower()
    if any(marker in lowered for marker in NEGATION_MARKERS):
        return None
    for feature, attr in _FLAG_FIELDS.items():
        if getattr(ctx.company, attr):
            continue
        if any(keyword in lowered for keyword in FEATURE_KEYWORDS[feature]):
            return feature
    return None


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUMBER.findall(text)}


def rule_violations(ctx: DraftContext, draft: SixQuestions) -> list[Violation]:
    violations: list[Violation] = []

    for idx, sentence in enumerate(_sentences(draft.q2_why_matters_for_company)):
        feature = _mentions_missing_feature(sentence, ctx)
        if feature:
            violations.append(
                Violation(
                    "feature_absent",
                    f"q2[{idx}]",
                    f"утверждение опирается на {feature}, которого у компании нет (значение 0)",
                )
            )

    for idx, risk in enumerate(draft.q3_risks):
        feature = _mentions_missing_feature(risk, ctx)
        if feature:
            violations.append(
                Violation(
                    "feature_absent",
                    f"q3_risks[{idx}]",
                    f"риск опирается на {feature}, которого у компании нет (значение 0)",
                )
            )

    news_numbers = _numbers(ctx.news.text_for_analysis)
    for number in sorted(_numbers(draft.q1_what_happened) - news_numbers):
        violations.append(
            Violation("fact_not_in_news", "q1", f"число {number} отсутствует в новости")
        )

    position = draft.q5_alfa_bank_position
    if position is not None:
        chunk = next((c for c in ctx.chunks if c.chunk_id == position.chunk_id), None)
        if chunk is None:
            violations.append(
                Violation(
                    "position_unverified",
                    "q5",
                    "позиция банка ссылается на фрагмент, которого нет среди найденных",
                )
            )
        else:
            if position.quote.strip() not in chunk.text:
                violations.append(
                    Violation(
                        "position_unverified", "q5", "цитата не является подстрокой фрагмента"
                    )
                )
            if position.page != chunk.page or position.report_file != chunk.file:
                violations.append(
                    Violation("position_unverified", "q5", "страница или файл не совпадают")
                )
            allowed = _numbers(chunk.text) | _numbers(chunk.title) | {str(chunk.page)}
            for number in sorted(_numbers(position.statement) - allowed):
                violations.append(
                    Violation(
                        "number_not_in_source",
                        "q5",
                        f"число {number} в позиции банка отсутствует во фрагменте",
                    )
                )
    return violations


def sanitize(
    draft: SixQuestions, violations: list[Violation], ctx: DraftContext
) -> tuple[SixQuestions, list[str]]:
    """Принудительная зачистка после неудачной повторной генерации."""
    fixed: list[str] = []
    data = draft.model_dump()

    q2_sentences = _sentences(draft.q2_why_matters_for_company)
    drop_q2 = {int(v.location[3:-1]) for v in violations if v.location.startswith("q2[")}
    if drop_q2:
        kept = [s for i, s in enumerate(q2_sentences) if i not in drop_q2]
        if not kept:
            kept = [
                f"Для {ctx.company.name} ({ctx.company.mainokved_name}, выручка "
                f"{ctx.company.revenue_human}) событие имеет косвенное значение."
            ]
        data["q2_why_matters_for_company"] = " ".join(kept)
        fixed.append(f"q2: удалено предложений — {len(drop_q2)}")

    drop_risks = {int(v.location[9:-1]) for v in violations if v.location.startswith("q3_risks[")}
    if drop_risks:
        data["q3_risks"] = [r for i, r in enumerate(draft.q3_risks) if i not in drop_risks]
        fixed.append(f"q3_risks: удалено пунктов — {len(drop_risks)}")

    if any(v.location == "q1" for v in violations):
        data["q1_what_happened"] = " ".join(_sentences(ctx.news.summary_facts)[:3])
        fixed.append("q1: заменено на факты из новости")

    if any(v.location == "q5" for v in violations):
        data["q5_alfa_bank_position"] = None
        fixed.append("q5: позиция банка снята — источник не подтверждён")

    return SixQuestions.model_validate(data), fixed
