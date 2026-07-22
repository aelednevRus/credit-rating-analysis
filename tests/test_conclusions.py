"""Тесты для credit_analysis.conclusions: качественные текстовые выводы.

См. docs/METHODOLOGY.md, раздел 6 — признак холдинговой модели сознательно
ограничен одним критерием (долгосрочные финансовые вложения > 50% активов),
второй критерий из старой редакции документа не реализуется намеренно.
"""

from __future__ import annotations

from credit_analysis.conclusions import build_conclusions


def _run(report, ratios_cur, ratios_prev=None, score_cur=50.0, score_prev=50.0):
    ratios_prev = ratios_prev or ratios_cur
    return build_conclusions(
        report, ratios_cur, ratios_prev,
        score_cur, score_prev, "B", "B",
    )


def test_holding_flag_triggers_on_long_investments_over_half_assets(report_factory):
    report = report_factory(balance={
        "long_investments": [600.0], "total_assets": [1000.0],
    })
    ratios = {"current_ratio": 2.0, "debt_to_assets": 0.3, "leverage": 0.3,
              "icr": 2.0, "net_profit": 10.0}
    out = _run(report, ratios)
    assert any("холдинговой модели" in c for c in out)
    assert not any("поручительств" in c for c in out)


def test_holding_flag_absent_when_investments_below_half(report_factory):
    report = report_factory(balance={
        "long_investments": [100.0], "total_assets": [1000.0],
    })
    ratios = {"current_ratio": 2.0, "debt_to_assets": 0.3, "leverage": 0.3,
              "icr": 2.0, "net_profit": 10.0}
    out = _run(report, ratios)
    assert not any("холдинговой модели" in c for c in out)


def test_profit_quality_flag_on_large_other_income(report_factory):
    report = report_factory(pl={"other_income": [30.0]})
    ratios = {"current_ratio": 2.0, "debt_to_assets": 0.3, "leverage": 0.3,
              "icr": 2.0, "net_profit": 100.0}
    out = _run(report, ratios)
    assert any("качеству прибыли" in c for c in out)


def test_no_profit_quality_flag_when_other_income_small(report_factory):
    report = report_factory(pl={"other_income": [5.0]})
    ratios = {"current_ratio": 2.0, "debt_to_assets": 0.3, "leverage": 0.3,
              "icr": 2.0, "net_profit": 100.0}
    out = _run(report, ratios)
    assert not any("качеству прибыли" in c for c in out)


def test_loss_flagged_regardless_of_other_income(report_factory):
    report = report_factory(pl={"other_income": [0.0]})
    ratios = {"current_ratio": 2.0, "debt_to_assets": 0.3, "leverage": 0.3,
              "icr": 2.0, "net_profit": -50.0}
    out = _run(report, ratios)
    assert any("Убыток" in c for c in out)


def test_score_dynamics_wording(report_factory):
    report = report_factory()
    ratios = {"current_ratio": 2.0, "debt_to_assets": 0.3, "leverage": 0.3,
              "icr": 2.0, "net_profit": 10.0}
    improved = _run(report, ratios, score_cur=80.0, score_prev=50.0)
    assert any("улучшилась" in c for c in improved)

    worsened = _run(report, ratios, score_cur=40.0, score_prev=70.0)
    assert any("ухудшилась" in c for c in worsened)
