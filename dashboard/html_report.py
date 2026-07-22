"""Статический HTML-дашборд кредитного рейтинга (без сервера).

Один самодостаточный .html-файл (инлайн CSS/JS, без внешних запросов),
который можно открыть прямо в браузере (file://) или выложить как
статику. Расчётная логика полностью в `credit_analysis/` — этот модуль
только представление.

Слева — закладки: «Свод» (сводный анализ по всем компаниям) сверху,
ниже — по одной закладке на каждую компанию с детализацией расчёта.

Запуск:
    python dashboard/html_report.py [папка_с_xlsx] [путь_к_html]

По умолчанию: data/input -> data/output/report.html
"""

from __future__ import annotations

import html
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from credit_analysis.pipeline import analyze_folder
from credit_analysis.metrics import LABELS, PERCENT_KEYS
from credit_analysis.rating import WEIGHTS

DEFAULT_INPUT = ROOT / "data" / "input"
DEFAULT_OUTPUT = ROOT / "data" / "output" / "report.html"

SUMMARY_KEY = "__summary__"

# --- Статусная палитра -------------------------------------------------
# Фиксированные, не темизируемые цвета состояния (см. .claude skill
# dataviz, references/palette.md — «Status palette»). Один и тот же набор
# hex работает и на светлой, и на тёмной поверхности.
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}
STATUS_TEXT = {
    "good": "#ffffff",
    "warning": "#1a1a19",
    "serious": "#1a1a19",
    "critical": "#ffffff",
}
CLASS_STATUS = {"A": "good", "B": "warning", "C": "serious", "D": "critical"}
CLASS_DESC = {
    "A": "высокая кредитоспособность",
    "B": "приемлемая кредитоспособность",
    "C": "пониженная кредитоспособность",
    "D": "низкая (высокий риск)",
}
SCORE_STATUS = {1.0: "good", 0.5: "warning", 0.0: "critical"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def fmt_value(key: str, value: float) -> str:
    if key == "net_profit":
        return f"{value:,.0f}".replace(",", " ")
    if key in PERCENT_KEYS:
        return f"{value * 100:.1f}%"
    if key == "icr" and value >= 999:
        return "н/д (нет долга)"
    return f"{value:.2f}"


def class_badge(cls: str) -> str:
    status = CLASS_STATUS[cls]
    return (
        f'<span class="badge" style="background:{STATUS[status]};'
        f'color:{STATUS_TEXT[status]}">{esc(cls)}</span>'
    )


def score_dot(score: float) -> str:
    status = SCORE_STATUS.get(score, "critical")
    return f'<span class="dot" style="background:{STATUS[status]}"></span>'


# --- Сайдбар -------------------------------------------------------------

def build_sidebar(results: list[dict]) -> str:
    summary_item = f"""
      <button class="nav-item nav-summary active" data-key="{SUMMARY_KEY}" type="button">
        Свод
      </button>"""

    company_items = "".join(
        f"""
      <button class="nav-item" data-key="{esc(r['_key'])}" type="button">
        <span class="nav-dot" style="background:{STATUS[CLASS_STATUS[r['class_cur']]]}"></span>
        <span class="nav-item-label">{esc(r['company'])}</span>
      </button>"""
        for r in results
    )
    companies_group = (
        f'<div class="nav-group-label">Компании ({len(results)})</div>{company_items}'
        if results else ""
    )

    return f"""
    <nav class="sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-title">Кредитный рейтинг</div>
        <div class="sidebar-subtitle">компаний по РСБУ</div>
      </div>
      <div class="nav-group">{summary_item}</div>
      <div class="nav-group nav-companies">{companies_group}</div>
      <div class="sidebar-footer">
        <button class="theme-toggle" id="theme-toggle" type="button">Светлая / тёмная тема</button>
      </div>
    </nav>"""


# --- Страница «Свод» -------------------------------------------------------

def build_kpi_row(results: list[dict]) -> str:
    counts = {c: 0 for c in "ABCD"}
    for r in results:
        counts[r["class_cur"]] = counts.get(r["class_cur"], 0) + 1
    tiles = "".join(
        f"""
        <div class="stat-tile" style="--tile-accent:{STATUS[CLASS_STATUS[cls]]}">
          <div class="stat-tile-label">Класс {cls} &mdash; {esc(CLASS_DESC[cls])}</div>
          <div class="stat-tile-value">{counts[cls]}</div>
        </div>"""
        for cls in "ABCD"
    )
    total_tile = f"""
        <div class="stat-tile stat-tile-muted">
          <div class="stat-tile-label">Всего компаний</div>
          <div class="stat-tile-value">{len(results)}</div>
        </div>"""
    return f'<div class="kpi-row">{tiles}{total_tile}</div>'


def build_summary_table(results: list[dict]) -> str:
    rows = []
    for r in results:
        delta = round(r["score_cur"] - r["score_prev"], 1)
        if delta > 0:
            delta_cls, delta_txt = "delta-up", f"+{delta:.1f}"
        elif delta < 0:
            delta_cls, delta_txt = "delta-down", f"{delta:.1f}"
        else:
            delta_cls, delta_txt = "delta-flat", "0.0"
        rows.append(f"""
        <tr class="summary-row" data-key="{esc(r['_key'])}">
          <td>{esc(r['company'])}</td>
          <td class="num">{esc(r['inn'] or '—')}</td>
          <td class="center">{class_badge(r['class_cur'])}</td>
          <td class="num">{r['score_cur']:.1f}</td>
          <td class="num">{r['score_prev']:.1f}</td>
          <td class="num {delta_cls}">{delta_txt}</td>
          <td>{esc(r['class_desc'])}</td>
        </tr>""")
    return f"""
    <table class="summary-table">
      <thead>
        <tr>
          <th>Компания</th><th>ИНН</th><th class="center">Класс</th>
          <th>Балл (тек.)</th><th>Балл (пред.)</th><th>&Delta;</th><th>Оценка</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    <p class="chart-caption">Клик по строке открывает детализацию расчёта компании.</p>"""


def build_score_chart(results: list[dict]) -> str:
    """Горизонтальные столбцы: сравнение комплексного балла по компаниям."""
    bars = []
    for r in results:
        score = r["score_cur"]
        status = CLASS_STATUS[r["class_cur"]]
        width = max(score, 1.5)  # видимая полоска даже при близком к 0 балле
        bars.append(f"""
        <div class="bar-row">
          <div class="bar-label">{esc(r['company'])}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:{width:.1f}%;background:{STATUS[status]}"></div>
          </div>
          <span class="bar-value">{score:.1f}</span>
        </div>""")
    ticks = "".join(
        f'<span class="bar-tick" style="left:{t}%">{t}</span>' for t in (0, 25, 50, 75, 100)
    )
    return f"""
    <div class="chart-card">
      <div class="chart-title">Комплексный балл по компаниям</div>
      <div class="bar-chart">{''.join(bars)}</div>
      <div class="bar-axis">{ticks}</div>
      <p class="chart-caption">Цвет столбца соответствует классу кредитоспособности (см. плитки выше).</p>
    </div>"""


def build_summary_page(results: list[dict], generated_at: str, source_label: str) -> str:
    if not results:
        content = f"""
        <div class="empty-state">
          <p>Нет данных для отображения. Положите файлы БФО (.xlsx) в
          <code>{esc(source_label)}</code> и перезапустите генерацию отчёта.</p>
        </div>"""
    else:
        content = f"""
        {build_kpi_row(results)}
        <div class="card">
          <h3 style="margin-top:0">Сводная таблица</h3>
          {build_summary_table(results)}
        </div>
        <div class="card">
          {build_score_chart(results)}
        </div>"""

    return f"""
    <section class="page page-summary active" data-key="{SUMMARY_KEY}">
      <header class="page-header">
        <div>
          <h1>Свод</h1>
          <p class="subtitle">Сгенерировано {esc(generated_at)} &middot; источник:
          {esc(source_label)} ({len(results)} компаний) &middot; методика:
          docs/METHODOLOGY.md</p>
        </div>
      </header>
      {content}
    </section>"""


# --- Страница компании (детализация расчёта) --------------------------------

def build_metrics_table(res: dict) -> str:
    rows = []
    for key, (label, norm) in LABELS.items():
        val_cur = res["ratios_cur"].get(key, 0.0)
        val_prev = res["ratios_prev"].get(key, 0.0)
        score = res["scores_cur"].get(key, 0.0)
        weight = WEIGHTS.get(key)
        weight_cell = f'<span class="weight-badge">{int(weight * 100)}%</span>' if weight else '<span class="muted">справочно</span>'
        rows.append(f"""
        <tr>
          <td>{score_dot(score)}{esc(label)}</td>
          <td class="muted">{esc(norm)}</td>
          <td class="num">{fmt_value(key, val_cur)}</td>
          <td class="num">{fmt_value(key, val_prev)}</td>
          <td class="center">{weight_cell}</td>
        </tr>""")
    return f"""
    <table class="metrics-table">
      <thead>
        <tr><th>Показатель</th><th>Норматив</th><th>Текущий</th><th>Предыдущий</th><th>Вес в рейтинге</th></tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def build_company_page(res: dict) -> str:
    cls = res["class_cur"]
    conclusions = "".join(f"<li>{esc(c)}</li>" for c in res["conclusions"])
    return f"""
    <section class="page page-company" data-key="{esc(res['_key'])}">
      <header class="page-header">
        <div>
          <h1>{esc(res['company'])}</h1>
          <p class="subtitle">
            {class_badge(cls)}
            <span class="muted">&nbsp;ИНН {esc(res['inn'] or '—')} &middot; источник: {esc(res['source_file'])}</span>
          </p>
        </div>
      </header>
      <div class="panel-metrics-grid">
        <div class="metric-box">
          <div class="stat-tile-label">Комплексный балл</div>
          <div class="stat-tile-value">{res['score_cur']:.1f}</div>
        </div>
        <div class="metric-box">
          <div class="stat-tile-label">Класс кредитоспособности</div>
          <div class="stat-tile-value">{esc(CLASS_DESC[cls])}</div>
        </div>
        <div class="metric-box">
          <div class="stat-tile-label">Балл (предыдущий год)</div>
          <div class="stat-tile-value">{res['score_prev']:.1f}</div>
        </div>
      </div>
      <div class="card">
        <h3 style="margin-top:0">Детализация расчёта: показатели (светофор)</h3>
        {build_metrics_table(res)}
      </div>
      <div class="card">
        <h3 style="margin-top:0">Качественные выводы</h3>
        <ul class="conclusions">{conclusions or '<li>Нет замечаний.</li>'}</ul>
      </div>
    </section>"""


CSS = """
:root {
  color-scheme: light;
  --surface-1:      #fcfcfb;
  --page-plane:     #f9f9f7;
  --text-primary:   #0b0b0b;
  --text-secondary: #52514e;
  --text-muted:     #898781;
  --gridline:       #e1e0d9;
  --baseline:       #c3c2b7;
  --border:         rgba(11,11,11,0.10);
  --delta-good:     #006300;
  --delta-bad:      #d03b3b;
  --sidebar-width:  260px;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface-1:      #1a1a19;
    --page-plane:     #0d0d0d;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted:     #898781;
    --gridline:       #2c2c2a;
    --baseline:       #383835;
    --border:         rgba(255,255,255,0.10);
    --delta-good:     #0ca30c;
    --delta-bad:      #e66767;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-1:      #1a1a19;
  --page-plane:     #0d0d0d;
  --text-primary:   #ffffff;
  --text-secondary: #c3c2b7;
  --text-muted:     #898781;
  --gridline:       #2c2c2a;
  --baseline:       #383835;
  --border:         rgba(255,255,255,0.10);
  --delta-good:     #0ca30c;
  --delta-bad:      #e66767;
}

* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--page-plane);
  color: var(--text-primary);
}
.muted { color: var(--text-muted); }

/* Layout: сайдбар слева + контент справа */
.layout { display: flex; min-height: 100vh; align-items: stretch; }

.sidebar {
  width: var(--sidebar-width); flex: 0 0 var(--sidebar-width);
  background: var(--surface-1); border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
.sidebar-brand { padding: 20px 18px 12px; }
.sidebar-title { font-weight: 700; font-size: 1.05rem; }
.sidebar-subtitle { font-size: 0.78rem; color: var(--text-secondary); margin-top: 2px; }
.nav-group { display: flex; flex-direction: column; padding: 4px 10px; }
.nav-companies { flex: 1 1 auto; }
.nav-group-label {
  font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--text-muted); padding: 12px 10px 6px;
}
.nav-item {
  display: flex; align-items: center; gap: 8px; text-align: left;
  border: none; background: transparent; color: var(--text-primary);
  padding: 9px 10px; border-radius: 8px; font-size: 0.88rem; cursor: pointer;
  width: 100%;
}
.nav-item:hover { background: color-mix(in srgb, var(--text-primary) 6%, transparent); }
.nav-item.active {
  background: color-mix(in srgb, var(--text-primary) 10%, transparent);
  font-weight: 600;
}
.nav-summary { font-weight: 700; font-size: 0.95rem; }
.nav-dot { flex: 0 0 auto; display: inline-block; height: 8px; width: 8px; border-radius: 50%; }
.nav-item-label {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sidebar-footer { padding: 12px; border-top: 1px solid var(--border); }

.content { flex: 1 1 auto; min-width: 0; padding: 32px 32px 64px; }
.page { display: none; }
.page.active { display: block; }
.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 1.5rem; margin: 0 0 6px; }
.subtitle { color: var(--text-secondary); font-size: 0.9rem; margin: 0; }

.theme-toggle {
  width: 100%;
  border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary);
  border-radius: 8px; padding: 8px 12px; font-size: 0.82rem; cursor: pointer;
}
.card {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 12px; padding: 20px; margin-bottom: 24px;
}

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 24px; }
.stat-tile {
  background: var(--surface-1); border: 1px solid var(--border); border-top: 3px solid var(--tile-accent, var(--baseline));
  border-radius: 10px; padding: 14px 16px;
}
.stat-tile-muted { border-top-color: var(--baseline); }
.stat-tile-label { font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 6px; }
.stat-tile-value { font-size: 1.6rem; font-weight: 600; }
.stat-tile-value.small { font-size: 0.85rem; font-weight: 500; word-break: break-all; }

/* Таблицы */
table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--gridline); }
th { color: var(--text-secondary); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.02em; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
td.center, th.center { text-align: center; }
.summary-row { cursor: pointer; }
.summary-row:hover { background: color-mix(in srgb, var(--text-primary) 4%, transparent); }
.delta-up { color: var(--delta-good); font-weight: 600; }
.delta-down { color: var(--delta-bad); font-weight: 600; }
.delta-flat { color: var(--text-muted); }

.badge {
  display: inline-block; padding: 2px 10px; border-radius: 999px; font-weight: 700; font-size: 0.85rem;
}
.dot { display: inline-block; height: 10px; width: 10px; border-radius: 50%; margin-right: 8px; }
.weight-badge {
  display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 0.78rem;
  background: color-mix(in srgb, var(--text-primary) 8%, transparent); color: var(--text-secondary);
}

/* Bar chart */
.chart-title { font-weight: 600; margin-bottom: 14px; }
.bar-chart { display: flex; flex-direction: column; gap: 10px; }
.bar-row { display: grid; grid-template-columns: 200px 1fr 52px; align-items: center; gap: 10px; }
.bar-label { font-size: 0.85rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-track { position: relative; height: 20px; background: var(--gridline); border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; }
.bar-value { font-size: 0.82rem; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }
.bar-axis { position: relative; height: 18px; margin-top: 4px; margin-left: 210px; margin-right: 62px; border-top: 1px solid var(--gridline); }
.bar-tick { position: absolute; top: 4px; transform: translateX(-50%); font-size: 0.72rem; color: var(--text-muted); }
.chart-caption { font-size: 0.78rem; color: var(--text-muted); margin: 14px 0 0; }

/* Страница компании */
.panel-metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
.metric-box { border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; background: var(--surface-1); }
h3 { font-size: 1rem; margin: 0 0 10px; }
.conclusions { margin: 0; padding-left: 20px; }
.conclusions li { margin-bottom: 6px; line-height: 1.4; }

.empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
.report-footer { margin-top: 32px; font-size: 0.78rem; color: var(--text-muted); }

@media (max-width: 760px) {
  .layout { flex-direction: column; }
  .sidebar {
    width: 100%; flex: 0 0 auto; position: static; height: auto;
    flex-direction: row; flex-wrap: nowrap; overflow-x: auto; align-items: center;
  }
  .sidebar-brand { padding: 12px 14px; flex: 0 0 auto; }
  .nav-group { flex-direction: row; padding: 6px; }
  .nav-companies { flex: 0 0 auto; }
  .nav-group-label { display: none; }
  .nav-item { width: auto; white-space: nowrap; }
  .nav-item-label { max-width: 160px; }
  .sidebar-footer { border-top: none; border-left: 1px solid var(--border); flex: 0 0 auto; }
  .content { padding: 20px 16px 48px; }
  .bar-row { grid-template-columns: 120px 1fr 52px; }
  .bar-label { display: none; }
}
"""

JS = """
(function () {
  var root = document.documentElement;
  var stored = null;
  try { stored = localStorage.getItem('cr-theme'); } catch (e) {}
  if (stored) root.setAttribute('data-theme', stored);

  var toggle = document.getElementById('theme-toggle');
  if (toggle) {
    toggle.addEventListener('click', function () {
      var current = root.getAttribute('data-theme');
      var systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      var effectiveDark = current ? current === 'dark' : systemDark;
      var next = effectiveDark ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('cr-theme', next); } catch (e) {}
    });
  }

  function selectPage(key) {
    document.querySelectorAll('.page').forEach(function (p) {
      p.classList.toggle('active', p.dataset.key === key);
    });
    document.querySelectorAll('.nav-item').forEach(function (n) {
      n.classList.toggle('active', n.dataset.key === key);
    });
    window.scrollTo(0, 0);
  }

  document.querySelectorAll('.nav-item, .summary-row').forEach(function (el) {
    el.addEventListener('click', function () { selectPage(el.dataset.key); });
  });
})();
"""


def render_html(results: list[dict], source_label: str) -> str:
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")

    for r in results:
        r["_key"] = r["source_file"]

    results_sorted = sorted(results, key=lambda r: r["score_cur"], reverse=True)

    body = f"""
    <div class="layout">
      {build_sidebar(results_sorted)}
      <main class="content">
        {build_summary_page(results_sorted, generated_at, source_label)}
        {''.join(build_company_page(r) for r in results_sorted)}
        <footer class="report-footer">
          Пороги, веса и классы кредитоспособности — см. docs/METHODOLOGY.md.
          Модель рассчитана на нефинансовые организации по РСБУ; веса заданы
          экспертно и не откалиброваны на выборке дефолтов.
        </footer>
      </main>
    </div>"""

    return _wrap(body)


def _wrap(body: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Кредитный рейтинг компаний</title>
<style>{CSS}</style>
</head>
<body>
{body}
<script>{JS}</script>
</body>
</html>
"""


def generate(input_dir: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> Path:
    results = [r.to_dict() for r in analyze_folder(input_dir)] if input_dir.exists() else []
    html_doc = render_html(results, source_label=str(input_dir.relative_to(ROOT)) if input_dir.is_relative_to(ROOT) else str(input_dir))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    in_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    saved = generate(in_dir, out_path)
    print(f"Сохранено: {saved}")
