"""Качественные текстовые выводы по результатам анализа.

Формирует выводы о динамике класса, ликвидности, долговой нагрузке,
покрытии процентов и качестве прибыли. Проверяет контекстные признаки
холдинговой модели и разовых доходов. См. docs/METHODOLOGY.md, раздел 6.
"""

from __future__ import annotations

from .extract import RawReport


def build_conclusions(
    report: RawReport,
    ratios_cur: dict[str, float],
    ratios_prev: dict[str, float],
    score_cur: float,
    score_prev: float,
    class_cur: str,
    class_prev: str,
) -> list[str]:
    """Возвращает список текстовых выводов (маркированные пункты)."""
    out: list[str] = []

    # 1. Динамика класса кредитоспособности
    if score_cur > score_prev + 1:
        out.append(
            f"Кредитоспособность улучшилась: балл вырос с {score_prev} до "
            f"{score_cur} (класс {class_prev} → {class_cur})."
        )
    elif score_cur < score_prev - 1:
        out.append(
            f"Кредитоспособность ухудшилась: балл снизился с {score_prev} до "
            f"{score_cur} (класс {class_prev} → {class_cur})."
        )
    else:
        out.append(
            f"Кредитоспособность стабильна: балл ~{score_cur} (класс {class_cur})."
        )

    # 2. Ликвидность
    cr = ratios_cur["current_ratio"]
    if cr >= 1.5:
        out.append(f"Ликвидность в норме: текущая ликвидность {cr:.2f} (≥ 1,5).")
    elif cr >= 1.0:
        out.append(
            f"Ликвидность умеренная: текущая ликвидность {cr:.2f} "
            f"(ниже норматива 1,5)."
        )
    else:
        out.append(
            f"Дефицит ликвидности: текущая ликвидность {cr:.2f} < 1,0 — "
            f"риск неисполнения краткосрочных обязательств."
        )

    # 3. Долговая нагрузка
    dta = ratios_cur["debt_to_assets"]
    lev = ratios_cur["leverage"]
    if dta <= 0.7:
        out.append(f"Долговая нагрузка приемлемая: Долг/Активы {dta:.2f} (≤ 0,7).")
    elif dta <= 0.85:
        out.append(f"Повышенная долговая нагрузка: Долг/Активы {dta:.2f}.")
    else:
        out.append(
            f"Высокая долговая нагрузка: Долг/Активы {dta:.2f}; "
            f"финансовый рычаг {lev:.2f}."
        )

    # 4. Покрытие процентов
    icr = ratios_cur["icr"]
    if icr >= 1.5:
        out.append(f"Покрытие процентов достаточное: ICR {icr:.2f} (≥ 1,5).")
    elif icr >= 0.75:
        out.append(f"Покрытие процентов на грани: ICR {icr:.2f}.")
    else:
        out.append(
            f"Проценты не покрываются операционной прибылью: ICR {icr:.2f} < 0,75."
        )

    # 5. Качество прибыли
    net = ratios_cur["net_profit"]
    if net <= 0:
        out.append("Убыток по итогам периода — отрицательный фактор устойчивости.")
    else:
        other_income = report.p("other_income", 0)
        if net > 0 and other_income > 0.2 * net:
            out.append(
                "Внимание к качеству прибыли: прочие (возможно разовые) доходы "
                f"({other_income:,.0f} тыс. руб.) превышают 20% чистой прибыли — "
                "устойчивость результата под вопросом."
            )

    # 6. Признак холдинговой модели
    noncurrent = report.b("noncurrent_assets", 0)
    long_inv = report.b("long_investments", 0)
    total_assets = report.b("total_assets", 0)
    if total_assets > 0 and long_inv > 0.5 * total_assets:
        out.append(
            "Признак холдинговой модели: долгосрочные финансовые вложения "
            f"({long_inv:,.0f} тыс. руб.) > 50% активов. Коэффициенты головной "
            "компании могут не отражать операционные риски — требуется анализ "
            "консолидированной отчётности группы."
        )

    return out
