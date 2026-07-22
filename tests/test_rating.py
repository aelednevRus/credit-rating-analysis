"""Тесты для credit_analysis.rating: комплексный балл и классы A/B/C/D."""

from __future__ import annotations

import pytest

from credit_analysis.rating import WEIGHTS, composite_score, credit_class


def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_composite_score_all_full_scores():
    scores = {key: 1.0 for key in WEIGHTS}
    assert composite_score(scores) == 100.0


def test_composite_score_all_zero_scores():
    scores = {key: 0.0 for key in WEIGHTS}
    assert composite_score(scores) == 0.0


def test_composite_score_weighted_mix():
    scores = {"icr": 1.0, "current_ratio": 0.5, "autonomy": 0.5,
              "debt_to_assets": 1.0, "roe": 0.0, "turnover": 1.0}
    expected = 100 * (
        WEIGHTS["icr"] * 1.0 + WEIGHTS["current_ratio"] * 0.5
        + WEIGHTS["autonomy"] * 0.5 + WEIGHTS["debt_to_assets"] * 1.0
        + WEIGHTS["roe"] * 0.0 + WEIGHTS["turnover"] * 1.0
    )
    assert composite_score(scores) == pytest.approx(round(expected, 1))


def test_composite_score_missing_key_treated_as_zero():
    assert composite_score({}) == 0.0


@pytest.mark.parametrize("score,expected_class", [
    (100, "A"), (70, "A"),
    (69.9, "B"), (50, "B"),
    (49.9, "C"), (30, "C"),
    (29.9, "D"), (0, "D"),
])
def test_credit_class_boundaries(score, expected_class):
    cls, _desc = credit_class(score)
    assert cls == expected_class
