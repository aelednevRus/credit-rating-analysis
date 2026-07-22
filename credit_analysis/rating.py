"""Комплексный показатель кредитоспособности и класс A/B/C/D.

Итоговый балл — взвешенная сумма баллов 6 ключевых факторов, приведённая
к шкале 0–100. См. docs/METHODOLOGY.md, разделы 4–5.
"""

from __future__ import annotations

# Веса 6 ключевых факторов (в сумме = 1.0)
WEIGHTS: dict[str, float] = {
    "icr": 0.25,             # Покрытие процентов
    "current_ratio": 0.20,   # Текущая ликвидность
    "autonomy": 0.20,        # Автономия
    "debt_to_assets": 0.15,  # Долг / Активы
    "roe": 0.15,             # ROE
    "turnover": 0.05,        # Оборачиваемость активов
}


def composite_score(scores: dict[str, float]) -> float:
    """Комплексный балл 0–100 = 100 × Σ (вес_i × балл_i)."""
    total = sum(WEIGHTS[k] * scores.get(k, 0.0) for k in WEIGHTS)
    return round(100 * total, 1)


def credit_class(score: float) -> tuple[str, str]:
    """Возвращает (буква класса, описание) по комплексному баллу."""
    if score >= 70:
        return "A", "высокая кредитоспособность"
    if score >= 50:
        return "B", "приемлемая кредитоспособность"
    if score >= 30:
        return "C", "пониженная кредитоспособность"
    return "D", "низкая кредитоспособность (высокий риск)"


CLASS_COLORS = {
    "A": "#1a9850",  # зелёный
    "B": "#a6d96a",  # светло-зелёный
    "C": "#fdae61",  # оранжевый
    "D": "#d73027",  # красный
}


if __name__ == "__main__":
    demo = {"icr": 1.0, "current_ratio": 1.0, "autonomy": 0.5,
            "debt_to_assets": 1.0, "roe": 0.5, "turnover": 1.0}
    s = composite_score(demo)
    print(f"Комплексный балл: {s} -> класс {credit_class(s)}")
