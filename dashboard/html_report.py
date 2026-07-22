"""Статический HTML-дашборд кредитного рейтинга (без сервера).

Альтернатива Streamlit-дашборду (`dashboard/app.py`): один самодостаточный
.html-файл (инлайн CSS/JS, без внешних запросов), который можно открыть
прямо в браузере (file://) или выложить как статику. Использует ту же
методику из `credit_analysis/`, что и `app.py`, — только представление
другое, расчётная логика не дублируется.

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
    </table>"""


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


def build_company_panel(res: dict, active: bool) -> str:
    cls = res["class_cur"]
    conclusions = "".join(f"<li>{esc(c)}</li>" for c in res["conclusions"])
    return f"""
    <section class="company-panel{' active' if active else ''}" data-key="{esc(res['_key'])}">
      <div class="panel-header">
        <h2>{esc(res['company'])}</h2>
        {class_badge(cls)}
        <span class="muted">ИНН {esc(res['inn'] or '—')}</span>
      </div>
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
          <div class="stat-tile-label">Источник данных</div>
          <div class="stat-tile-value small">{esc(res['source_file'])}</div>
        </div>
      </div>
      <h3>Показатели (светофор)</h3>
      {build_metrics_table(res)}
      <h3>Качественные выводы</h3>
      <ul class="conclusions">{conclusions or '<li>Нет замечаний.</li>'}</ul>
    </section>"""


def build_company_selector(results: list[dict]) -> str:
    chips = "".join(
        f'<button class="chip{" active" if i == 0 else ""}" data-key="{esc(r["_key"])}" type="button">'
        f'{esc(r["company"])}</button>'
        for i, r in enumerate(results)
    )
    return f'<div class="chip-row">{chips}</div>'


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
body {
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--page-plane);
  color: var(--text-primary);
}
.wrap { max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }
header.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 24px; flex-wrap: wrap;
}
h1 { font-size: 1.6rem; margin: 0 0 4px; }
.subtitle { color: var(--text-secondary); font-size: 0.9rem; margin: 0; }
.theme-toggle {
  border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary);
  border-radius: 8px; padding: 6px 12px; font-size: 0.85rem; cursor: pointer;
}
.card {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 12px; padding: 20px; margin-bottom: 24px;
}
.muted { color: var(--text-muted); }

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
.summary-row.active { background: color-mix(in srgb, var(--text-primary) 7%, transparent); }
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

/* Company chips + panels */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.chip {
  border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary);
  border-radius: 999px; padding: 6px 14px; font-size: 0.85rem; cursor: pointer;
}
.chip.active { background: var(--text-primary); color: var(--surface-1); border-color: var(--text-primary); }
.company-panel { display: none; }
.company-panel.active { display: block; }
.panel-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.panel-header h2 { margin: 0; font-size: 1.25rem; }
.panel-metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }
.metric-box { border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }
h3 { font-size: 1rem; margin: 20px 0 10px; }
.conclusions { margin: 0; padding-left: 20px; }
.conclusions li { margin-bottom: 6px; line-height: 1.4; }

.empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
footer { margin-top: 32px; font-size: 0.78rem; color: var(--text-muted); }
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

  function selectCompany(key) {
    document.querySelectorAll('.company-panel').forEach(function (p) {
      p.classList.toggle('active', p.dataset.key === key);
    });
    document.querySelectorAll('.chip').forEach(function (c) {
      c.classList.toggle('active', c.dataset.key === key);
    });
    document.querySelectorAll('.summary-row').forEach(function (r) {
      r.classList.toggle('active', r.dataset.key === key);
    });
  }

  document.querySelectorAll('.chip, .summary-row').forEach(function (el) {
    el.addEventListener('click', function () { selectCompany(el.dataset.key); });
  });
})();
"""


def render_html(results: list[dict], source_label: str) -> str:
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")

    if not results:
        body = f"""
        <div class="empty-state">
          <h1>Кредитный рейтинг компаний</h1>
          <p>Нет данных для отображения. Положите файлы БФО (.xlsx) в
          <code>{esc(source_label)}</code> и перезапустите генерацию отчёта.</p>
        </div>"""
        return _wrap(body, generated_at, source_label, count=0)

    for r in results:
        r["_key"] = r["source_file"]

    results_sorted = sorted(results, key=lambda r: r["score_cur"], reverse=True)

    body = f"""
    <header class="page-header">
      <div>
        <h1>Кредитный рейтинг компаний</h1>
        <p class="subtitle">Сгенерировано {esc(generated_at)} &middot; источник:
        {esc(source_label)} ({len(results)} компаний) &middot; методика:
        docs/METHODOLOGY.md</p>
      </div>
      <button class="theme-toggle" id="theme-toggle" type="button">Светлая / тёмная тема</button>
    </header>

    {build_kpi_row(results_sorted)}

    <div class="card">
      <h3 style="margin-top:0">Сводная таблица</h3>
      {build_summary_table(results_sorted)}
    </div>

    <div class="card chart-card-wrap">
      {build_score_chart(results_sorted)}
    </div>

    <div class="card">
      <h3 style="margin-top:0">Детальный анализ компании</h3>
      {build_company_selector(results_sorted)}
      {''.join(build_company_panel(r, active=(i == 0)) for i, r in enumerate(results_sorted))}
    </div>

    <footer>
      Пороги, веса и классы кредитоспособности — см. docs/METHODOLOGY.md.
      Модель рассчитана на нефинансовые организации по РСБУ; веса заданы
      экспертно и не откалиброваны на выборке дефолтов.
    </footer>"""

    return _wrap(body, generated_at, source_label, count=len(results))


def _wrap(body: str, generated_at: str, source_label: str, count: int) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Кредитный рейтинг компаний</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
{body}
</div>
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
