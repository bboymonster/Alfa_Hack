from ai_service.agent.tools import MAX_CHUNKS_PER_REPORT, rerank
from ai_service.schemas.reports import ReportChunk


def _chunk(chunk_id: str, report_id: str, title: str, text: str, score: float) -> ReportChunk:
    return ReportChunk(
        chunk_id=chunk_id,
        report_id=report_id,
        title=title,
        file=f"{report_id}.pdf",
        page=1,
        index=0,
        text=text,
        score=score,
        dense_score=0.6,
    )


RATE_TITLE = "Ключевая ставка ЦБ РФ: ставка без изменения на 14,0%, риторика стала жестче"
BOND_TITLE = "Бонд Бриф: итоги недели"
NEWS = (
    "Банк России сохранил ключевую ставку на уровне 14,0% годовых. Инфляционные ожидания повышены."
)


def test_relevant_chunk_overtakes_higher_rrf_score() -> None:
    polyus = _chunk(
        "b:2:0",
        "bond",
        BOND_TITLE,
        "Агентство выделяет высокие показатели маржинальности и низкий уровень долга компании "
        "Полюс — одной из ведущих золотодобывающих компаний мира.",
        0.9,
    )
    rate = _chunk(
        "r:1:0",
        "rate",
        RATE_TITLE,
        "ЦБ РФ принял решение оставить ключевую ставку неизменной на уровне 14,0%. Риторика "
        "регулятора стала жестче, инфляционные ожидания остаются повышенными.",
        0.5,
    )
    ranked = rerank([polyus, rate], ["ключевую ставк", "банк россии"], NEWS)
    assert ranked[0].chunk_id == "r:1:0"
    assert (ranked[0].score or 0) > (ranked[1].score or 0)


def test_noise_is_penalised_and_reports_capped() -> None:
    noisy = _chunk(
        "n:1:0", "long", "Долговой рынок", "20% 24% ame С 19% 18% ar Gal 15% —— 12%", 0.8
    )
    many = [
        _chunk(
            f"l:{i}:0", "long", "Долговой рынок", f"Текст про облигации и ставку номер {i}.", 0.7
        )
        for i in range(5)
    ]
    other = _chunk("o:1:0", "other", "Инфляция", "Недельная инфляция замедлилась.", 0.3)
    ranked = rerank([noisy, *many, other], [], "")
    assert sum(1 for c in ranked if c.report_id == "long") == MAX_CHUNKS_PER_REPORT
    assert any(c.report_id == "other" for c in ranked)
    assert all(c.chunk_id != "n:1:0" for c in ranked)  # шумный чанк вытеснен штрафом и лимитом


def test_topic_match_boost() -> None:
    labor = _chunk("l:1:0", "labor", "Макростатистика 7М26", "Рынок труда остаётся сильным.", 0.5)
    labor = labor.model_copy(update={"topics": ["labor_market"]})
    other = _chunk("c:1:0", "cons", "Потребление на пике", "Безработица выросла до 2,2%.", 0.6)
    ranked = rerank([other, labor], [], "", topic="labor_market")
    assert ranked[0].chunk_id == "l:1:0"
