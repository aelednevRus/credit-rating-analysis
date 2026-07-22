"""Модуль расчёта кредитного рейтинга по РСБУ-отчётности.

Реализует методику из docs/METHODOLOGY.md:
- extract.py     — чтение БФО из .xlsx (3 листа) в нормализованные показатели
- metrics.py     — 11 коэффициентов + балльная оценка «светофор»
- rating.py      — комплексный балл (0–100) и класс кредитоспособности A/B/C/D
- conclusions.py — текстовые качественные выводы
- pipeline.py    — сквозной прогон: файл(ы) -> результат для дашборда
"""

from .extract import extract_report, RawReport
from .metrics import compute_ratios, score_ratios, THRESHOLDS
from .rating import composite_score, credit_class, WEIGHTS
from .conclusions import build_conclusions
from .pipeline import analyze_file, analyze_folder, CompanyResult

__all__ = [
    "extract_report",
    "RawReport",
    "compute_ratios",
    "score_ratios",
    "THRESHOLDS",
    "composite_score",
    "credit_class",
    "WEIGHTS",
    "build_conclusions",
    "analyze_file",
    "analyze_folder",
    "CompanyResult",
]
