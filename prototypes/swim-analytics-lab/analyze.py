#!/usr/bin/env python3
"""Offline prototype for exploring swimming-specific Apple Health metrics.

Reads Apple Health ZIP/XML locally, keeps only swimming workouts and the
selected samples attached to their time intervals, and can write a standalone
HTML report. This prototype intentionally does not connect to PostgreSQL or
the web service; validated analysis rules can later be ported into app/services.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.apple_health_importer import extract_xml, parse_export  # noqa: E402


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def analyze_export(payload: bytes, filename: str) -> dict[str, Any]:
    parsed = parse_export(extract_xml(payload, filename))
    measurements_by_workout: dict[str, list[Any]] = defaultdict(list)
    for measurement in parsed.measurements:
        measurements_by_workout[measurement.workout_id].append(measurement)

    # Apple Health includes one workout-level HR statistic in addition to the
    # time series. Compare both sources and surface disagreements explicitly.
    workout_hr_stats = _read_workout_hr_statistics(extract_xml(payload, filename))
    sessions: list[dict[str, Any]] = []
    for workout in parsed.workouts:
        measurements = measurements_by_workout[workout.id]
        distances = sorted(
            (sample for sample in measurements if "DistanceSwimming" in sample.type),
            key=lambda sample: sample.started_at,
        )
        strokes = {
            sample.started_at: sample.value
            for sample in measurements
            if "SwimmingStrokeCount" in sample.type
        }
        heart_rate = sorted(
            (sample for sample in measurements if "HeartRate" in sample.type),
            key=lambda sample: sample.started_at,
        )
        lengths = []
        for index, sample in enumerate(distances, start=1):
            elapsed = max(
                0.0,
                (_parse_datetime(sample.ended_at) - _parse_datetime(sample.started_at)).total_seconds(),
            )
            lengths.append({
                "index": index,
                "distance_m": sample.value,
                "duration_seconds": elapsed,
                "stroke_count": strokes.get(sample.started_at),
                "started_at": sample.started_at,
                "ended_at": sample.ended_at,
            })

        pool_lengths = [
            length for length in lengths
            if workout.pool_length_m is not None
            and math.isclose(length["distance_m"], workout.pool_length_m, abs_tol=0.1)
            and length["duration_seconds"] > 0
            and length["stroke_count"] is not None
        ]
        # Some exports omit a workout-level distance statistic while keeping
        # one distance sample per pool length. Use that sum only as a clearly
        # labeled fallback; never replace an explicit workout summary.
        distance_from_lengths = sum(length["distance_m"] for length in lengths) or None
        effective_distance = workout.total_distance_m or distance_from_lengths
        swim_seconds = sum(length["duration_seconds"] for length in pool_lengths)
        swim_distance = sum(length["distance_m"] for length in pool_lengths)
        gaps = []
        for previous, following in zip(pool_lengths, pool_lengths[1:]):
            gap = (_parse_datetime(following["started_at"]) - _parse_datetime(previous["ended_at"])).total_seconds()
            gaps.append(max(0.0, gap))

        early_late = _compare_first_last_quarter(pool_lengths)
        heart_values = [sample.value for sample in heart_rate]
        heart_trend = _heart_rate_trend(heart_rate)
        summary_hr = workout_hr_stats.get(workout.id)
        sample_avg_hr = statistics.mean(heart_values) if heart_values else None
        hr_discrepancy = (
            abs(summary_hr - sample_avg_hr)
            if summary_hr is not None and sample_avg_hr is not None
            else None
        )
        swolf_values = [length["duration_seconds"] + length["stroke_count"] for length in pool_lengths]
        sessions.append({
            "date": workout.started_at[:10],
            "distance_m": effective_distance,
            "distance_source": "workout_summary" if workout.total_distance_m is not None else ("distance_samples" if distance_from_lengths is not None else None),
            "duration_seconds": workout.duration_seconds,
            "overall_pace_seconds_per_100m": (
                workout.duration_seconds / (effective_distance / 100)
                if effective_distance and workout.duration_seconds > 0 else None
            ),
            "pool_length_m": workout.pool_length_m,
            "length_count": len(pool_lengths),
            "lengths": pool_lengths,
            "recorded_swim_seconds": swim_seconds if pool_lengths else None,
            "recorded_swim_pace_seconds_per_100m": (
                swim_seconds / (swim_distance / 100) if swim_seconds and swim_distance else None
            ),
            "unattributed_seconds": (
                max(0.0, workout.duration_seconds - swim_seconds) if swim_seconds else None
            ),
            "between_length_gaps_seconds": gaps,
            "average_strokes_per_length": statistics.mean(length["stroke_count"] for length in pool_lengths) if pool_lengths else None,
            "average_swolf": statistics.mean(swolf_values) if swolf_values else None,
            "split_comparison": early_late,
            "heart_rate": {
                "sample_count": len(heart_values),
                "sample_average_bpm": sample_avg_hr,
                "median_bpm": statistics.median(heart_values) if heart_values else None,
                "min_bpm": min(heart_values) if heart_values else None,
                "max_bpm": max(heart_values) if heart_values else None,
                "early_late_change_bpm": heart_trend,
                "workout_summary_average_bpm": summary_hr,
                "summary_vs_samples_difference_bpm": hr_discrepancy,
            },
            "active_energy_kcal": workout.total_energy_kcal,
            "insights": [],
        })
        sessions[-1]["insights"] = _build_insights([sessions[-1]])

    return {
        "session_count": len(sessions),
        "measurement_count": len(parsed.measurements),
        "sessions": sessions,
        "insights": [insight for session in sessions for insight in session["insights"]],
        "quality_notes": _quality_notes(sessions),
    }


def _read_workout_hr_statistics(xml_bytes: bytes) -> dict[str, float]:
    root = ET.fromstring(xml_bytes)
    stats: dict[str, float] = {}
    for workout in root.iter("Workout"):
        source = workout.get("sourceName", "")
        key = f"{source}:{workout.get('startDate', '')}:{workout.get('endDate', '')}"
        for statistic in workout.findall("WorkoutStatistics"):
            if "HeartRate" in statistic.get("type", "") and statistic.get("average"):
                stats[key] = float(statistic.get("average", "0"))
    return stats


def _compare_first_last_quarter(lengths: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(lengths) < 8:
        return None
    quarter_size = max(2, len(lengths) // 4)
    early, late = lengths[:quarter_size], lengths[-quarter_size:]
    early_time = statistics.mean(item["duration_seconds"] for item in early)
    late_time = statistics.mean(item["duration_seconds"] for item in late)
    early_strokes = statistics.mean(item["stroke_count"] for item in early)
    late_strokes = statistics.mean(item["stroke_count"] for item in late)
    return {
        "lengths_in_each_quarter": quarter_size,
        "early_avg_seconds": early_time,
        "late_avg_seconds": late_time,
        "time_change_percent": (late_time / early_time - 1) * 100 if early_time else None,
        "early_avg_strokes": early_strokes,
        "late_avg_strokes": late_strokes,
        "stroke_change_percent": (late_strokes / early_strokes - 1) * 100 if early_strokes else None,
    }


def _heart_rate_trend(samples: list[Any]) -> float | None:
    if len(samples) < 10:
        return None
    first_time = _parse_datetime(samples[0].started_at)
    last_time = _parse_datetime(samples[-1].started_at)
    span = (last_time - first_time).total_seconds()
    if span <= 0:
        return None
    first = [sample.value for sample in samples if (_parse_datetime(sample.started_at) - first_time).total_seconds() <= span * 0.2]
    last = [sample.value for sample in samples if (last_time - _parse_datetime(sample.started_at)).total_seconds() <= span * 0.2]
    if not first or not last:
        return None
    return statistics.mean(last) - statistics.mean(first)


def _build_insights(sessions: list[dict[str, Any]]) -> list[dict[str, str]]:
    insights: list[dict[str, str]] = []
    for session in sessions:
        comparison = session["split_comparison"]
        if comparison and comparison["time_change_percent"] is not None and comparison["time_change_percent"] >= 15:
            insights.append({
                "kind": "within_session_pace_fade",
                "title": "Отрезки в конце заняли больше времени",
                "detail": (
                    f"Первые {comparison['lengths_in_each_quarter']} длины: "
                    f"{comparison['early_avg_seconds']:.1f} с в среднем; последние: "
                    f"{comparison['late_avg_seconds']:.1f} с "
                    f"(+{comparison['time_change_percent']:.1f}%)."
                ),
            })
        if comparison and comparison["stroke_change_percent"] is not None and comparison["stroke_change_percent"] >= 15:
            insights.append({
                "kind": "stroke_count_increase",
                "title": "В конце стало больше гребков на длину",
                "detail": (
                    f"Среднее выросло с {comparison['early_avg_strokes']:.1f} до "
                    f"{comparison['late_avg_strokes']:.1f} гребков на длину "
                    f"(+{comparison['stroke_change_percent']:.1f}%). Это стоит сравнить "
                    "со следующими тренировками; одна сессия не объясняет причину."
                ),
            })
        hr = session["heart_rate"]
        if hr["summary_vs_samples_difference_bpm"] is not None and hr["summary_vs_samples_difference_bpm"] > 15:
            insights.append({
                "kind": "heart_rate_source_mismatch",
                "title": "Пульс в сводке расходится с измерениями",
                "detail": (
                    f"Среднее в сводке Apple: {hr['workout_summary_average_bpm']:.0f} уд/мин; "
                    f"среднее {hr['sample_count']} временных измерений: {hr['sample_average_bpm']:.0f} уд/мин. "
                    "В отчёте отдельно показаны оба значения."
                ),
            })
    if len(sessions) < 3 and sessions:
        insights.append({
            "kind": "baseline_only",
            "title": "Пока формируем базовую линию",
            "detail": "Между тренировками пока рано искать устойчивый тренд. После нескольких сессий добавим сравнения по темпу и объёму.",
        })
    return insights


def _quality_notes(sessions: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    if not sessions:
        return ["В экспортированном XML не найдено плавательных тренировок."]
    if any(session["unattributed_seconds"] and session["unattributed_seconds"] > 0 for session in sessions):
        notes.append("Время по длинам покрывает только часть длительности тренировки; остаток может включать паузы и интервалы без метрик.")
    if any(session["heart_rate"]["summary_vs_samples_difference_bpm"] and session["heart_rate"]["summary_vs_samples_difference_bpm"] > 15 for session in sessions):
        notes.append("Сводный пульс Apple заметно отличается от среднего по временным измерениям; значения не объединяются.")
    notes.append("Сравнение первых и последних длин описывает только эту тренировку и не устанавливает причину изменения.")
    return notes


def _svg_chart(values: list[float], color: str, label: str) -> str:
    width, height, left, right, top, bottom = 760, 220, 42, 18, 18, 28
    if not values:
        return '<div class="chart-empty">Нет записей для графика</div>'
    low, high = min(values), max(values)
    span = max(high - low, 1)
    plot_w, plot_h = width - left - right, height - top - bottom
    points = [
        (left + plot_w * (i / max(len(values) - 1, 1)), top + plot_h * (1 - (value - low) / span))
        for i, value in enumerate(values)
    ]
    path = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))
    grids = "".join(
        f'<line x1="{left}" y1="{top + plot_h * i / 2:.1f}" x2="{width-right}" y2="{top + plot_h*i/2:.1f}" stroke="#e9efeb"/>'
        for i in range(3)
    )
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{color}"/>' for x, y in points)
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(label)}">{grids}<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>{dots}<text x="{left}" y="{height-6}" fill="#8d9e9b" font-size="10">1</text><text x="{width-right}" y="{height-6}" text-anchor="end" fill="#8d9e9b" font-size="10">{len(values)}</text></svg>'


def render_report(result: dict[str, Any]) -> str:
    session_cards = []
    for session in result["sessions"]:
        hr = session["heart_rate"]
        lengths = session["lengths"]
        highlights = "".join(
            f'<li>{html.escape(item["title"])}<span>{html.escape(item["detail"])}</span></li>'
            for item in session["insights"]
        ) or "<li>Пока нет статистически полезных наблюдений.</li>"
        session_cards.append(f"""
        <section class="session">
          <div class="section-head"><div><span class="eyebrow">ТРЕНИРОВКА · {html.escape(session['date'])}</span><h2>{session['distance_m'] or 0:.0f} м <small>· {session['pool_length_m'] or 0:.0f} м бассейн</small></h2></div><div class="tag">{session['length_count']} длин</div></div>
          <div class="metrics">
            <div><label>ОБЩИЙ ТЕМП / 100 М</label><strong>{_pace(session['overall_pace_seconds_per_100m'])}</strong><span>вместе с паузами</span></div>
            <div><label>ТЕМП ПО ОТРЕЗКАМ</label><strong>{_pace(session['recorded_swim_pace_seconds_per_100m'])}</strong><span>только учтённое время длин</span></div>
            <div><label>ГРЕБКОВ / ДЛИНУ</label><strong>{_num(session['average_strokes_per_length'], 1)}</strong><span>среднее по парным записям</span></div>
            <div><label>SWOLF</label><strong>{_num(session['average_swolf'], 1)}</strong><span>время длины + гребки</span></div>
          </div>
          <div class="chart-grid"><article class="chart-card"><h3>Время на 25 м</h3><p>Сравнивай с другими тренировками, не только со скоростью.</p>{_svg_chart([item['duration_seconds'] for item in lengths], '#dd806b', 'Время на каждую длину')}</article><article class="chart-card"><h3>Пульс по измерениям</h3><p>{hr['sample_count']} записей · среднее {_num(hr['sample_average_bpm'])} уд/мин · диапазон {_num(hr['min_bpm'])}–{_num(hr['max_bpm'])}</p>{_svg_chart([item["value"] for item in _session_hr_samples(session)], '#4b9b91', 'Пульс по точкам измерения')}</article></div>
          <div class="observations"><h3>Что заметно</h3><ul>{highlights}</ul></div>
          <p class="data-note">Плавательные интервалы заняли {_duration(session['recorded_swim_seconds'])}; вне них в тренировке осталось около {_duration(session['unattributed_seconds'])}. Это может быть отдых и/или промежутки без записей длины. Сводный пульс Apple: {_num(hr['workout_summary_average_bpm'])} уд/мин; разница с измерениями: {_num(hr['summary_vs_samples_difference_bpm'])} уд/мин.</p>
        </section>""")
    all_notes = "".join(f"<li>{html.escape(note)}</li>" for note in result["quality_notes"])
    content = "".join(session_cards) or '<div class="empty">Плавательные тренировки в экспорте не найдены.</div>'
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Swim Analytics Lab · прототип</title><style>
    :root{{--ink:#153540;--muted:#71868a;--paper:#f2f6f2;--line:#e3ebe5;--mint:#9cd6c5;--coral:#dd806b}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1100px;margin:auto;padding:45px 30px 70px}}header{{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:20px}}.brand{{font-size:12px;letter-spacing:.12em;font-weight:800}}.tag{{background:#e2f2e9;border-radius:100px;padding:8px 12px;color:#398d7e;font-size:11px;font-weight:700}}h1{{font-size:40px;letter-spacing:-.055em;margin:42px 0 8px}}.subtitle{{color:var(--muted);margin:0 0 30px;line-height:1.6}}.session{{background:white;border:1px solid var(--line);border-radius:14px;padding:28px;margin-top:20px}}.section-head{{display:flex;align-items:center;justify-content:space-between}}.eyebrow{{font:10px ui-monospace,monospace;color:#609a8c;letter-spacing:.1em}}h2{{font-size:25px;margin:10px 0 24px}}h2 small{{font-size:12px;font-weight:500;color:var(--muted)}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.metrics div{{padding:17px;background:#f5f8f5;border-radius:9px}}.metrics label{{display:block;font:9px ui-monospace,monospace;color:#839894;letter-spacing:.06em}}.metrics strong{{display:block;font-size:25px;margin-top:12px}}.metrics span{{display:block;color:var(--muted);font-size:10px;margin-top:5px}}.chart-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px}}.chart-card{{border:1px solid var(--line);border-radius:10px;padding:18px;min-width:0}}h3{{font-size:14px;margin:0 0 6px}}.chart-card p{{color:var(--muted);font-size:10px;line-height:1.5;min-height:30px}}svg{{width:100%;height:auto;margin-top:10px}}.observations{{margin-top:19px;padding:20px;background:#eef5f0;border-radius:10px}}.observations ul,.quality ul{{padding-left:18px;margin:12px 0 0}}.observations li{{margin:12px 0;font-weight:700;font-size:12px}}.observations li span{{display:block;margin-top:4px;color:var(--muted);font-weight:400;font-size:11px;line-height:1.5}}.data-note{{color:var(--muted);font-size:10px;line-height:1.6;margin:17px 0 0}}.quality{{margin-top:20px;color:var(--muted);font-size:11px;line-height:1.7}}.empty{{padding:35px;background:#fff;border:1px solid var(--line);border-radius:14px;color:var(--muted)}}footer{{margin-top:25px;border-top:1px solid var(--line);padding-top:18px;color:#99a9a5;font-size:10px}}@media(max-width:700px){{main{{padding:25px 15px}}h1{{font-size:32px;margin-top:32px}}.session{{padding:18px}}.metrics{{grid-template-columns:1fr 1fr}}.chart-grid{{grid-template-columns:1fr}}}}
    </style></head><body><main><header><div class="brand">SWIM / ANALYTICS LAB</div><div class="tag">ИЗОЛИРОВАННЫЙ ПРОТОТИП</div></header><h1>Что рассказывает тренировка</h1><p class="subtitle">Экспериментальные метрики отделяют плавание по длинам от полного времени сессии и показывают, где данные требуют осторожности.<br>Обнаружено тренировок: {result['session_count']} · выбранных измерений: {result['measurement_count']}</p>{content}<aside class="quality"><strong>Ограничения и качество данных</strong><ul>{all_notes}</ul><p>Отчёт построен локально из плавательных записей; медицинские записи других категорий не включались.</p></aside><footer>Swim Lab · аналитический прототип · без сетевых запросов</footer></main></body></html>"""


def _session_hr_samples(session: dict[str, Any]) -> list[dict[str, Any]]:
    # Kept separate from the report's summary object so raw series are not
    # copied into logs or documentation.
    return session.get("_heart_rate_samples", [])


def _pace(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    rounded = round(seconds)
    return f"{rounded // 60}:{rounded % 60:02d}"


def _num(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}".replace(".", ",")


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    whole = round(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="Apple Health export.xml or ZIP file")
    parser.add_argument("--report", type=Path, help="write a standalone HTML report")
    parser.add_argument("--json", type=Path, help="write machine-readable JSON analysis")
    args = parser.parse_args()

    payload = args.export.read_bytes()
    result = analyze_export(payload, args.export.name)
    # Attach heart-rate series only for report rendering; don't include it in
    # normal console output or machine-readable summaries.
    parsed = parse_export(extract_xml(payload, args.export.name))
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in parsed.measurements:
        if "HeartRate" in sample.type:
            by_id[sample.workout_id].append({"started_at": sample.started_at, "value": sample.value})
    for workout, session in zip(parsed.workouts, result["sessions"]):
        session["_heart_rate_samples"] = by_id[workout.id]

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(result), encoding="utf-8")
        for session in result["sessions"]:
            session.pop("_heart_rate_samples", None)
        print(f"HTML report written: {args.report}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        sanitized = json.loads(json.dumps(result, ensure_ascii=False))
        for session in sanitized["sessions"]:
            session.pop("_heart_rate_samples", None)
        args.json.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON analysis written: {args.json}")
    print(json.dumps({key: value for key, value in result.items() if key != "sessions"} | {"sessions": [{key: value for key, value in session.items() if key != "_heart_rate_samples"} for session in result["sessions"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
