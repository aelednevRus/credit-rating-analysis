"""Сквозной тест пайплайна: .xlsx -> CompanyResult -> JSON."""

from __future__ import annotations

import json

from credit_analysis.pipeline import CompanyResult, analyze_file, analyze_folder, save_json


def test_analyze_file_returns_company_result(workbook_factory):
    path = workbook_factory(
        "company.xlsx",
        info={"name": 'ООО "Стабильные Технологии"', "inn": "7701234567"},
        balance_rows=[
            ("Оборотные активы", "1200", [420000, 390000, 360000]),
            ("Запасы", "1210", [120000, 110000, 100000]),
            ("Денежные средства", "1250", [90000, 70000, 60000]),
            ("Краткосрочные обязательства", "1500", [150000, 140000, 120000]),
            ("Капитал и резервы", "1300", [360000, 320000, 290000]),
            ("Баланс (активы)", "1600", [600000, 560000, 520000]),
            ("Долгосрочные заёмные средства", "1410", [80000, 90000, 100000]),
            ("Краткосрочные заёмные средства", "1510", [40000, 45000, 40000]),
        ],
        pl_rows=[
            ("Выручка", "2110", [850000, 780000]),
            ("Прибыль от продаж", "2200", [140000, 120000]),
            ("Проценты к уплате", "2330", [-18000, -20000]),
            ("Чистая прибыль", "2400", [95000, 78000]),
        ],
    )

    result = analyze_file(path)

    assert isinstance(result, CompanyResult)
    assert result.company == 'ООО "Стабильные Технологии"'
    assert result.inn == "7701234567"
    assert 0 <= result.score_cur <= 100
    assert result.class_cur in {"A", "B", "C", "D"}
    assert "current_ratio" in result.ratios_cur
    assert isinstance(result.conclusions, list) and result.conclusions


def test_analyze_folder_processes_all_files_and_skips_temp(tmp_path, workbook_factory):
    workbook_factory(
        "one.xlsx", info={"name": "Компания Один", "inn": "1"},
        balance_rows=[("Баланс (активы)", "1600", [100, 100, 100])],
        pl_rows=[("Выручка", "2110", [10, 10])],
    )
    workbook_factory(
        "two.xlsx", info={"name": "Компания Два", "inn": "2"},
        balance_rows=[("Баланс (активы)", "1600", [200, 200, 200])],
        pl_rows=[("Выручка", "2110", [20, 20])],
    )
    (tmp_path / "~$temp.xlsx").write_bytes(b"")  # временный файл Excel — должен игнорироваться

    results = analyze_folder(tmp_path)

    assert len(results) == 2
    assert {r.company for r in results} == {"Компания Один", "Компания Два"}


def test_save_json_writes_expected_structure(tmp_path, workbook_factory):
    path = workbook_factory(
        "company.xlsx", info={"name": "Компания", "inn": "123"},
        balance_rows=[("Баланс (активы)", "1600", [100, 100, 100])],
        pl_rows=[("Выручка", "2110", [10, 10])],
    )
    results = [analyze_file(path)]
    out_path = tmp_path / "out" / "results.json"

    save_json(results, out_path)

    assert out_path.exists()
    data = json.loads(out_path.read_text("utf-8"))
    assert len(data) == 1
    assert data[0]["company"] == "Компания"
    assert "score_cur" in data[0] and "class_cur" in data[0]
