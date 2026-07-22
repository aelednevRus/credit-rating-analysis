"""Сквозной прогон: .xlsx-файл(ы) БФО -> результат для дашборда/отчёта."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .extract import extract_report, RawReport
from .metrics import compute_ratios, score_ratios, LABELS
from .rating import composite_score, credit_class
from .conclusions import build_conclusions


@dataclass
class CompanyResult:
    """Полный результат анализа одной компании."""

    company: str
    inn: str
    source_file: str
    score_cur: float
    score_prev: float
    class_cur: str
    class_desc: str
    class_prev: str
    ratios_cur: dict[str, float] = field(default_factory=dict)
    ratios_prev: dict[str, float] = field(default_factory=dict)
    scores_cur: dict[str, float] = field(default_factory=dict)
    scores_prev: dict[str, float] = field(default_factory=dict)
    conclusions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_report(report: RawReport) -> CompanyResult:
    """Прогоняет уже прочитанный RawReport через методику."""
    ratios_cur = compute_ratios(report, period=0)
    ratios_prev = compute_ratios(report, period=1)
    scores_cur = score_ratios(ratios_cur)
    scores_prev = score_ratios(ratios_prev)

    score_cur = composite_score(scores_cur)
    score_prev = composite_score(scores_prev)
    cls_cur, desc_cur = credit_class(score_cur)
    cls_prev, _ = credit_class(score_prev)

    conclusions = build_conclusions(
        report, ratios_cur, ratios_prev,
        score_cur, score_prev, cls_cur, cls_prev,
    )

    return CompanyResult(
        company=report.company,
        inn=report.inn,
        source_file=report.source_file,
        score_cur=score_cur,
        score_prev=score_prev,
        class_cur=cls_cur,
        class_desc=desc_cur,
        class_prev=cls_prev,
        ratios_cur=ratios_cur,
        ratios_prev=ratios_prev,
        scores_cur=scores_cur,
        scores_prev=scores_prev,
        conclusions=conclusions,
    )


def analyze_file(path: str | Path) -> CompanyResult:
    """Читает и анализирует один .xlsx-файл."""
    report = extract_report(path)
    return analyze_report(report)


def analyze_folder(folder: str | Path) -> list[CompanyResult]:
    """Анализирует все .xlsx-файлы в папке (кроме временных ~$)."""
    folder = Path(folder)
    results: list[CompanyResult] = []
    for path in sorted(folder.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        try:
            results.append(analyze_file(path))
        except Exception as exc:  # noqa: BLE001
            print(f"[!] Не удалось обработать {path.name}: {exc}")
    return results


def save_json(results: list[CompanyResult], out_path: str | Path) -> None:
    """Сохраняет результаты в JSON (для кэша дашборда/интеграций)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.to_dict() for r in results]
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    import sys

    src = sys.argv[1] if len(sys.argv) > 1 else "data/input"
    src_path = Path(src)
    results = (
        [analyze_file(src_path)] if src_path.is_file()
        else analyze_folder(src_path)
    )
    for r in results:
        print(f"\n=== {r.company} (ИНН {r.inn or '—'}) ===")
        print(f"Балл: {r.score_cur} (пред. {r.score_prev}) -> "
              f"класс {r.class_cur} — {r.class_desc}")
        for c in r.conclusions:
            print(f"  • {c}")
    if results:
        save_json(results, "data/output/results.json")
        print(f"\nСохранено: data/output/results.json ({len(results)} компаний)")
