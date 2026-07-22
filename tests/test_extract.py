"""Тесты для credit_analysis.extract: нормализация чисел и чтение .xlsx."""

from __future__ import annotations

from pathlib import Path

import pytest

from credit_analysis.extract import _to_number, extract_report

ROOT = Path(__file__).resolve().parents[1]
REAL_INPUT_DIR = ROOT / "data" / "input"


@pytest.mark.parametrize("raw,expected", [
    (None, 0.0),
    ("-", 0.0),
    ("—", 0.0),  # длинное тире
    ("", 0.0),
    (123, 123.0),
    (123.5, 123.5),
    ("1 234", 1234.0),
    ("1 234,56", 1234.56),  # NBSP-разделитель тысяч + запятая
    ("(123)", -123.0),
    ("(1 234,5)", -1234.5),
])
def test_to_number(raw, expected):
    assert _to_number(raw) == pytest.approx(expected)


def test_extract_report_reads_codes_from_generated_workbook(workbook_factory):
    """Показатели читаются по коду строки, а не по фиксированной колонке."""
    path = workbook_factory(
        "demo.xlsx",
        info={"name": 'ООО "Тест"', "inn": "1234567890"},
        balance_rows=[
            ("Оборотные активы", "1200", [420000, 390000, 360000]),
            ("Капитал и резервы", "1300", [360000, 320000, 290000]),
            ("Баланс (активы)", "1600", [600000, 560000, 520000]),
        ],
        pl_rows=[
            ("Выручка", "2110", [850000, 780000]),
            ("Чистая прибыль", "2400", [95000, 78000]),
        ],
    )
    report = extract_report(path)

    assert report.b("current_assets", 0) == 420000.0
    assert report.b("current_assets", 1) == 390000.0
    assert report.b("current_assets", 2) == 360000.0
    assert report.p("revenue", 0) == 850000.0
    assert report.p("net_profit", 1) == 78000.0
    # Не запрошенный в этом отчёте код должен возвращать 0, а не падать
    assert report.b("inventory", 0) == 0.0


def test_extract_report_missing_key_returns_zero_not_error(workbook_factory):
    path = workbook_factory(
        "empty.xlsx",
        info={"name": "Пусто", "inn": ""},
        balance_rows=[],
        pl_rows=[],
    )
    report = extract_report(path)
    assert report.b("total_assets") == 0.0
    assert report.p("revenue") == 0.0


@pytest.mark.skipif(not REAL_INPUT_DIR.exists(), reason="нет data/input")
def test_extract_report_reads_all_real_files_without_empty_balance():
    """Регрессия: openpyxl read_only=True молча отдавал пустой лист для
    части реальных выгрузок ГИР БО (см. docs/METHODOLOGY.md, извлечение по
    полному режиму чтения книги)."""
    files = sorted(REAL_INPUT_DIR.glob("*.xlsx"))
    files = [f for f in files if not f.name.startswith("~$")]
    if not files:
        pytest.skip("нет реальных .xlsx в data/input")
    for path in files:
        report = extract_report(path)
        assert report.balance, f"{path.name}: баланс пуст"
        assert report.pl, f"{path.name}: ОФР пуст"
