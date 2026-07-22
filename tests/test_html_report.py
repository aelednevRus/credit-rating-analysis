"""Тесты для dashboard/html_report.py: статический HTML-дашборд без сервера."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.html_report import generate, render_html


def test_render_html_empty_state():
    doc = render_html([], source_label="data/input")
    assert "Нет данных для отображения" in doc
    assert "<script>" in doc  # тема всё равно переключаема
    assert 'class="nav-item nav-summary active" data-key="__summary__"' in doc
    assert "Компании (" not in doc  # нет компаний — секция в сайдбаре не выводится


def test_render_html_contains_all_companies_and_is_self_contained():
    results = [
        {
            "company": 'ООО "Альфа"', "inn": "111", "source_file": "a.xlsx",
            "score_cur": 80.0, "score_prev": 60.0, "class_cur": "A",
            "class_desc": "высокая кредитоспособность",
            "ratios_cur": {"current_ratio": 2.0}, "ratios_prev": {"current_ratio": 1.5},
            "scores_cur": {"current_ratio": 1.0}, "scores_prev": {"current_ratio": 1.0},
            "conclusions": ["Тест-вывод 1"],
        },
        {
            "company": 'АО "Бета"', "inn": "222", "source_file": "b.xlsx",
            "score_cur": 10.0, "score_prev": 20.0, "class_cur": "D",
            "class_desc": "низкая кредитоспособность (высокий риск)",
            "ratios_cur": {"current_ratio": 0.3}, "ratios_prev": {"current_ratio": 0.5},
            "scores_cur": {"current_ratio": 0.0}, "scores_prev": {"current_ratio": 0.0},
            "conclusions": ["Тест-вывод 2"],
        },
    ]
    doc = render_html(results, source_label="data/input")

    # Нет внешних запросов — самодостаточный файл
    assert "http://" not in doc and "https://" not in doc
    assert "<link" not in doc

    # Обе компании присутствуют статически (не требуют выполнения JS для чтения)
    assert 'ООО &quot;Альфа&quot;' in doc
    assert 'АО &quot;Бета&quot;' in doc
    assert "Тест-вывод 1" in doc and "Тест-вывод 2" in doc

    # Отсортировано по убыванию балла: Альфа (80.0) должна идти раньше Беты (10.0)
    assert doc.index('ООО &quot;Альфа&quot;') < doc.index('АО &quot;Бета&quot;')

    # Сайдбар: закладка «Свод» сверху и активна по умолчанию, ниже — компании
    assert doc.index('data-key="__summary__"') < doc.index('data-key="a.xlsx"')
    assert 'class="nav-item nav-summary active" data-key="__summary__"' in doc
    assert '<span class="nav-item-label">ООО &quot;Альфа&quot;</span>' in doc
    assert '<span class="nav-item-label">АО &quot;Бета&quot;</span>' in doc

    # Страница «Свод» активна по умолчанию, страницы компаний скрыты до клика
    assert 'class="page page-summary active" data-key="__summary__"' in doc
    assert 'class="page page-company" data-key="a.xlsx"' in doc
    assert 'class="page page-company" data-key="b.xlsx"' in doc

    # Класс-бейджи используют статусную палитру (good=A, critical=D)
    assert "#0ca30c" in doc  # good — класс A
    assert "#d03b3b" in doc  # critical — класс D


def test_generate_writes_file_and_handles_missing_input_dir(tmp_path):
    out = generate(input_dir=tmp_path / "nonexistent", output_path=tmp_path / "out" / "report.html")
    assert out.exists()
    content = out.read_text("utf-8")
    assert "Нет данных для отображения" in content
