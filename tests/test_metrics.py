"""Тесты для credit_analysis.metrics: пороги, светофор, edge-cases."""

from __future__ import annotations

import pytest

from credit_analysis.metrics import (
    THRESHOLDS, LOWER_IS_BETTER, compute_ratios, score_one, score_ratios,
    score_color,
)


@pytest.mark.parametrize("key", THRESHOLDS.keys())
def test_score_one_full_and_half_thresholds(key):
    """На пороговых значениях балл ровно 1.0 / 0.5, чуть хуже — ниже."""
    full, half = THRESHOLDS[key]
    lower_is_better = key in LOWER_IS_BETTER

    if key == "net_profit":
        assert score_one(key, 1.0) == 1.0
        assert score_one(key, 0.0) == 0.5
        assert score_one(key, -1.0) == 0.0
        return

    step = -0.01 if lower_is_better else 0.01
    assert score_one(key, full) == 1.0
    assert score_one(key, half) == 0.5
    assert score_one(key, half - step) == 0.0


def test_score_one_leverage_mirrored():
    """leverage — «чем меньше, тем лучше», зеркальная логика порогов."""
    assert score_one("leverage", 0.5) == 1.0
    assert score_one("leverage", 1.0) == 1.0
    assert score_one("leverage", 1.5) == 0.5
    assert score_one("leverage", 2.0) == 0.5
    assert score_one("leverage", 2.1) == 0.0


def test_score_ratios_maps_every_key():
    ratios = {"current_ratio": 2.0, "leverage": 0.5}
    scores = score_ratios(ratios)
    assert scores == {"current_ratio": 1.0, "leverage": 1.0}


def test_score_color():
    assert score_color(1.0) == "green"
    assert score_color(0.5) == "yellow"
    assert score_color(0.0) == "red"


def test_icr_sentinel_when_no_interest(report_factory):
    """При нулевых процентах к уплате ICR = 999 («нет долга»), а не деление на 0."""
    report = report_factory(
        balance={"total_assets": [1000.0]},
        pl={"sales_profit": [100.0], "interest_paid": [0.0]},
    )
    ratios = compute_ratios(report, period=0)
    assert ratios["icr"] == 999.0


def test_compute_ratios_safe_division_on_zero_denominator(report_factory):
    """Нулевые краткосрочные обязательства не приводят к делению на ноль."""
    report = report_factory(
        balance={"current_assets": [500.0], "short_liabilities": [0.0]},
        pl={},
    )
    ratios = compute_ratios(report, period=0)
    assert ratios["current_ratio"] == 0.0


def test_compute_ratios_full_example(report_factory):
    report = report_factory(
        balance={
            "current_assets": [420000.0], "inventory": [120000.0], "vat": [8000.0],
            "cash": [90000.0], "short_investments": [30000.0],
            "short_liabilities": [150000.0], "equity": [360000.0, 320000.0],
            "total_assets": [600000.0, 560000.0], "long_liabilities": [90000.0],
            "long_debt": [80000.0], "short_debt": [40000.0],
        },
        pl={
            "revenue": [850000.0], "sales_profit": [140000.0],
            "interest_paid": [-18000.0], "net_profit": [95000.0],
        },
    )
    ratios = compute_ratios(report, period=0)
    assert ratios["current_ratio"] == pytest.approx(420000 / 150000)
    assert ratios["quick_ratio"] == pytest.approx((420000 - 120000 - 8000) / 150000)
    assert ratios["autonomy"] == pytest.approx(360000 / 600000)
    assert ratios["leverage"] == pytest.approx((80000 + 40000) / 360000)
    assert ratios["icr"] == pytest.approx(140000 / 18000)
    assert ratios["roe"] == pytest.approx(95000 / ((360000 + 320000) / 2))
