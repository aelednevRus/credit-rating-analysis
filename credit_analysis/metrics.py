"""Финансовые коэффициенты и балльная оценка «светофор».

11 коэффициентов + чистая прибыль как отдельный индикатор, за текущий и
предыдущий год. Балльная оценка: 0 / 0.5 / 1 по двум пороговым значениям.
Для показателей «чем меньше, тем лучше» (leverage, debt_to_assets) логика
зеркальная. См. docs/METHODOLOGY.md, разделы 2–3.
"""

from __future__ import annotations

from .extract import RawReport

# --- Пороги балльной оценки -------------------------------------------------
# Кортеж (полный порог -> 1.0, половинный порог -> 0.5).
# Направление задаётся в LOWER_IS_BETTER.

THRESHOLDS: dict[str, tuple[float, float]] = {
    "current_ratio": (1.5, 1.0),
    "quick_ratio": (1.0, 0.7),
    "absolute_ratio": (0.2, 0.1),
    "autonomy": (0.4, 0.2),
    "leverage": (1.0, 2.0),        # меньше — лучше
    "debt_to_assets": (0.7, 0.85), # меньше — лучше
    "icr": (1.5, 0.75),
    "turnover": (0.1, 0.05),
    "roe": (0.15, 0.075),
    "roa": (0.02, 0.005),
    "margin": (0.20, 0.10),
    "net_profit": (0.0, 0.0),      # >0 -> 1; =0 -> 0.5; <0 -> 0
}

LOWER_IS_BETTER = {"leverage", "debt_to_assets"}

# Человекочитаемые названия и норматив (для дашборда)
LABELS: dict[str, tuple[str, str]] = {
    "current_ratio": ("Текущая ликвидность", "≥ 1,5"),
    "quick_ratio": ("Быстрая ликвидность", "≥ 1,0"),
    "absolute_ratio": ("Абсолютная ликвидность", "≥ 0,2"),
    "autonomy": ("Автономия", "≥ 0,4"),
    "leverage": ("Финансовый рычаг", "≤ 1,0"),
    "debt_to_assets": ("Долг / Активы", "≤ 0,7"),
    "icr": ("Покрытие процентов (ICR)", "≥ 1,5"),
    "turnover": ("Оборачиваемость активов", "выше — лучше"),
    "roe": ("ROE", "≥ 15%"),
    "roa": ("ROA", "выше — лучше"),
    "margin": ("Рентабельность продаж", "выше — лучше"),
    "net_profit": ("Чистая прибыль, тыс. руб.", "> 0"),
}

PERCENT_KEYS = {"roe", "roa", "margin"}


def _safe_div(numerator: float, denominator: float) -> float:
    """Деление с защитой от нуля (возвращает 0.0)."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_ratios(report: RawReport, period: int = 0) -> dict[str, float]:
    """Рассчитывает 11 коэффициентов + чистую прибыль за заданный период.

    period: 0 — текущий год, 1 — предыдущий год.
    Средние величины (ROE/ROA) считаются как (кон. периода + кон. пред.) / 2.
    """
    b = lambda k: report.b(k, period)      # noqa: E731
    p = lambda k: report.p(k, period)      # noqa: E731

    current_assets = b("current_assets")
    inventory = b("inventory")
    vat = b("vat")
    cash = b("cash")
    short_inv = b("short_investments")
    short_liab = b("short_liabilities")
    equity = b("equity")
    total_assets = b("total_assets")
    long_liab = b("long_liabilities")
    long_debt = b("long_debt")
    short_debt = b("short_debt")

    revenue = p("revenue")
    sales_profit = p("sales_profit")
    # Проценты к уплате в ОФР отражаются в скобках (отрицательными) —
    # для ICR нужна абсолютная величина.
    interest_paid = abs(p("interest_paid"))
    net_profit = p("net_profit")

    # Средние величины: конец текущего периода и конец предыдущего
    equity_prev = report.b("equity", period + 1)
    assets_prev = report.b("total_assets", period + 1)
    avg_equity = (equity + equity_prev) / 2 if equity_prev else equity
    avg_assets = (total_assets + assets_prev) / 2 if assets_prev else total_assets

    total_liabilities = long_liab + short_liab

    return {
        "current_ratio": _safe_div(current_assets, short_liab),
        "quick_ratio": _safe_div(current_assets - inventory - vat, short_liab),
        "absolute_ratio": _safe_div(cash + short_inv, short_liab),
        "autonomy": _safe_div(equity, total_assets),
        "leverage": _safe_div(long_debt + short_debt, equity),
        "debt_to_assets": _safe_div(total_liabilities, total_assets),
        "icr": _safe_div(sales_profit, interest_paid) if interest_paid else 999.0,
        "turnover": _safe_div(revenue, total_assets),
        "roe": _safe_div(net_profit, avg_equity),
        "roa": _safe_div(net_profit, avg_assets),
        "margin": _safe_div(sales_profit, revenue),
        "net_profit": net_profit,
    }


def score_one(key: str, value: float) -> float:
    """Балл одного показателя: 0 / 0.5 / 1.0 по порогам THRESHOLDS."""
    full, half = THRESHOLDS[key]

    if key == "net_profit":
        if value > 0:
            return 1.0
        if value == 0:
            return 0.5
        return 0.0

    if key in LOWER_IS_BETTER:
        if value <= full:
            return 1.0
        if value <= half:
            return 0.5
        return 0.0

    if value >= full:
        return 1.0
    if value >= half:
        return 0.5
    return 0.0


def score_ratios(ratios: dict[str, float]) -> dict[str, float]:
    """Возвращает баллы «светофора» для всех показателей."""
    return {key: score_one(key, val) for key, val in ratios.items()}


def score_color(score: float) -> str:
    """Цвет светофора по баллу."""
    return {1.0: "green", 0.5: "yellow", 0.0: "red"}.get(score, "red")


if __name__ == "__main__":
    # Мини-самопроверка порогов
    assert score_one("current_ratio", 1.6) == 1.0
    assert score_one("current_ratio", 1.2) == 0.5
    assert score_one("current_ratio", 0.9) == 0.0
    assert score_one("leverage", 0.8) == 1.0
    assert score_one("leverage", 1.5) == 0.5
    assert score_one("leverage", 2.5) == 0.0
    assert score_one("net_profit", -5) == 0.0
    print("metrics.py: пороги OK")
