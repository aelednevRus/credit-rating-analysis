"""Streamlit-дашборд кредитного рейтинга.

Запуск:
    streamlit run dashboard/app.py

Читает все .xlsx из data/input, прогоняет через credit_analysis и показывает:
- сводную таблицу компаний с классом A/B/C/D и баллом;
- «светофор» по 12 показателям для выбранной компании;
- динамику балла (текущий vs предыдущий год);
- качественные выводы.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Делаем корень проекта импортируемым (для запуска из любой папки)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from credit_analysis.pipeline import analyze_folder, analyze_file, CompanyResult
from credit_analysis.metrics import LABELS, PERCENT_KEYS, score_color
from credit_analysis.rating import CLASS_COLORS, WEIGHTS

INPUT_DIR = ROOT / "data" / "input"

st.set_page_config(page_title="Кредитный рейтинг компаний", layout="wide")

# --- Стили ------------------------------------------------------------------
st.markdown(
    """
    <style>
    .metric-cell {padding:6px 10px;border-radius:6px;font-weight:600;}
    .dot {height:14px;width:14px;border-radius:50%;display:inline-block;margin-right:6px;}
    </style>
    """,
    unsafe_allow_html=True,
)

COLOR_HEX = {"green": "#1a9850", "yellow": "#f9c74f", "red": "#d73027"}


@st.cache_data(show_spinner=False)
def load_results(folder: str) -> list[dict]:
    """Прогоняет папку и возвращает результаты как список dict (для кэша)."""
    return [r.to_dict() for r in analyze_folder(folder)]


def dot(color: str) -> str:
    return f'<span class="dot" style="background:{COLOR_HEX[color]}"></span>'


def fmt_value(key: str, value: float) -> str:
    if key == "net_profit":
        return f"{value:,.0f}"
    if key in PERCENT_KEYS:
        return f"{value * 100:.1f}%"
    if key == "icr" and value >= 999:
        return "н/д (нет %)"
    return f"{value:.2f}"


# --- Sidebar: источник данных ----------------------------------------------
st.sidebar.title("📊 Кредитный рейтинг")
st.sidebar.caption("Методика: docs/METHODOLOGY.md")

uploaded = st.sidebar.file_uploader(
    "Загрузить БФО (.xlsx)", type=["xlsx"], accept_multiple_files=True
)

results: list[dict] = []

if uploaded:
    tmp_dir = ROOT / "data" / "_uploaded"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for uf in uploaded:
        dest = tmp_dir / uf.name
        dest.write_bytes(uf.getbuffer())
        try:
            results.append(analyze_file(dest).to_dict())
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"{uf.name}: {exc}")
else:
    if INPUT_DIR.exists():
        results = load_results(str(INPUT_DIR))

if st.sidebar.button("🔄 Обновить из data/input"):
    load_results.clear()
    st.rerun()

if not results:
    st.info(
        "Положите файлы БФО (.xlsx) в папку **data/input** или загрузите их "
        "через панель слева."
    )
    st.stop()

# --- Сводная таблица --------------------------------------------------------
st.title("Кредитный рейтинг компаний")

summary = pd.DataFrame(
    [
        {
            "Компания": r["company"],
            "ИНН": r["inn"] or "—",
            "Класс": r["class_cur"],
            "Балл (тек.)": r["score_cur"],
            "Балл (пред.)": r["score_prev"],
            "Δ": round(r["score_cur"] - r["score_prev"], 1),
            "Оценка": r["class_desc"],
        }
        for r in results
    ]
).sort_values("Балл (тек.)", ascending=False)


def color_class(val: str) -> str:
    return f"background-color:{CLASS_COLORS.get(val, '#eee')};color:white;font-weight:700;text-align:center"


styled = summary.style.applymap(color_class, subset=["Класс"]).format(
    {"Балл (тек.)": "{:.1f}", "Балл (пред.)": "{:.1f}", "Δ": "{:+.1f}"}
)
st.dataframe(styled, use_container_width=True, hide_index=True)

# --- Распределение по классам ----------------------------------------------
c1, c2, c3, c4 = st.columns(4)
for col, cls in zip((c1, c2, c3, c4), ("A", "B", "C", "D")):
    n = int((summary["Класс"] == cls).sum())
    col.markdown(
        f"<div class='metric-cell' style='background:{CLASS_COLORS[cls]};color:white'>"
        f"Класс {cls}: <b>{n}</b></div>",
        unsafe_allow_html=True,
    )

st.divider()

# --- Детализация по компании -----------------------------------------------
choice = st.selectbox(
    "Компания для детального анализа",
    [r["company"] for r in results],
)
res = next(r for r in results if r["company"] == choice)

cls = res["class_cur"]
st.markdown(
    f"### {res['company']} &nbsp; "
    f"<span style='background:{CLASS_COLORS[cls]};color:white;padding:4px 12px;"
    f"border-radius:8px'>Класс {cls}</span>",
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)
m1.metric("Комплексный балл", res["score_cur"], round(res["score_cur"] - res["score_prev"], 1))
m2.metric("Класс кредитоспособности", res["class_cur"], res["class_desc"], delta_color="off")
m3.metric("ИНН", res["inn"] or "—")

# --- Светофор по показателям -----------------------------------------------
st.subheader("Показатели (светофор)")

rows = []
for key, (label, norm) in LABELS.items():
    val_cur = res["ratios_cur"].get(key, 0.0)
    val_prev = res["ratios_prev"].get(key, 0.0)
    sc = res["scores_cur"].get(key, 0.0)
    weight = WEIGHTS.get(key)
    rows.append(
        {
            "": dot(score_color(sc)),
            "Показатель": label + (" ⭐" if weight else ""),
            "Норматив": norm,
            "Текущий": fmt_value(key, val_cur),
            "Предыдущий": fmt_value(key, val_prev),
            "Балл": sc,
            "Вес в рейтинге": f"{int(weight * 100)}%" if weight else "справ.",
        }
    )

table = pd.DataFrame(rows)
st.markdown(
    table.to_html(escape=False, index=False), unsafe_allow_html=True
)
st.caption("⭐ — ключевой фактор, входит в комплексный балл. Остальные носят справочный характер.")

st.divider()

# --- Качественные выводы ----------------------------------------------------
st.subheader("Качественные выводы")
for c in res["conclusions"]:
    st.markdown(f"- {c}")

st.caption(f"Источник данных: {res['source_file']}")
