from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean, median
from typing import Any


def build_summary(workouts: list[dict[str, Any]], measurement_stats: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(workouts)
    distances = [item["total_distance_m"] for item in workouts if item["total_distance_m"] is not None]
    paces = [
        item["duration_seconds"] / (item["total_distance_m"] / 100)
        for item in workouts
        if item["total_distance_m"] and item["duration_seconds"] > 0
    ]
    return {
        "workout_count": count,
        "total_distance_m": round(sum(distances), 1) if distances else 0,
        "average_distance_m": round(sum(distances) / len(distances), 1) if distances else None,
        "average_pace_seconds_per_100m": round(sum(paces) / len(paces), 1) if paces else None,
        "average_duration_seconds": round(sum(item["duration_seconds"] for item in workouts) / count, 1) if count else None,
        "measurement_stats": measurement_stats,
        "note": "Workout average pace includes recorded duration, including pauses if present.",
    }


def build_training_analysis(
    workouts: list[dict[str, Any]], measurements: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build explainable training metrics and only emit insights with enough data."""
    sessions: list[dict[str, Any]] = []
    by_week: dict[str, dict[str, float | int]] = defaultdict(lambda: {"distance_m": 0.0, "sessions": 0})
    workout_hr: dict[str, list[float]] = defaultdict(list)
    workout_strokes: dict[str, float] = defaultdict(float)
    length_samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    length_strokes: dict[str, dict[str, float]] = defaultdict(dict)
    insights: list[dict[str, Any]] = []
    measurement_types = {item["type"] for item in measurements}
    for item in measurements:
        kind = item["type"]
        if "HeartRate" in kind:
            workout_hr[item["workout_id"]].append(float(item["value"]))
        elif "SwimmingStrokeCount" in kind:
            workout_strokes[item["workout_id"]] += float(item["value"])
            length_strokes[item["workout_id"]][item["started_at"]] = float(item["value"])
        elif "DistanceSwimming" in kind:
            try:
                seconds = (
                    datetime.fromisoformat(item["ended_at"])
                    - datetime.fromisoformat(item["started_at"])
                ).total_seconds()
            except (TypeError, ValueError):
                seconds = 0
            length_samples[item["workout_id"]].append({
                "started_at": item["started_at"],
                "ended_at": item["ended_at"],
                "distance_m": float(item["value"]),
                "duration_seconds": max(0, seconds),
            })

    for workout in workouts:
        try:
            started = datetime.fromisoformat(workout["started_at"])
        except (TypeError, ValueError):
            continue
        distance = workout["total_distance_m"]
        duration = float(workout["duration_seconds"] or 0)
        pace = duration / (distance / 100) if distance and duration > 0 else None
        week_start = started.date() - timedelta(days=started.weekday())
        week_key = week_start.isoformat()
        by_week[week_key]["sessions"] = int(by_week[week_key]["sessions"]) + 1
        if distance:
            by_week[week_key]["distance_m"] = float(by_week[week_key]["distance_m"]) + float(distance)
        hr_values = workout_hr.get(workout["id"], [])
        lengths = sorted(length_samples.get(workout["id"], []), key=lambda row: row["started_at"])
        strokes_by_start = length_strokes.get(workout["id"], {})
        paired_lengths = [
            {**length, "stroke_count": strokes_by_start.get(length["started_at"])}
            for length in lengths
        ]
        standard_lengths = [
            row for row in paired_lengths
            if workout["pool_length_m"]
            and abs(row["distance_m"] - workout["pool_length_m"]) < 0.1
            and row["duration_seconds"] > 0
            and row["stroke_count"] is not None
        ]
        moving_time = sum(row["duration_seconds"] for row in standard_lengths) if standard_lengths else None
        moving_distance = sum(row["distance_m"] for row in standard_lengths) if standard_lengths else None
        swolf_values = [row["duration_seconds"] + row["stroke_count"] for row in standard_lengths]
        pace_fade_pct = None
        stroke_change_pct = None
        first_quarter_avg_strokes = None
        last_quarter_avg_strokes = None
        if len(standard_lengths) >= 8:
            quarter_size = max(2, len(standard_lengths) // 4)
            first_quarter = standard_lengths[:quarter_size]
            last_quarter = standard_lengths[-quarter_size:]
            first_time = sum(row["duration_seconds"] for row in first_quarter) / len(first_quarter)
            last_time = sum(row["duration_seconds"] for row in last_quarter) / len(last_quarter)
            if first_time > 0:
                pace_fade_pct = (last_time / first_time - 1) * 100
                if pace_fade_pct >= 15:
                    insights.append({
                        "kind": "within_session_pace_fade",
                        "title": "Pace slowed in the final lengths",
                        "detail": f"Your last quarter of recorded lengths averaged {last_time:.1f} seconds per {workout['pool_length_m']:g} m, versus {first_time:.1f} seconds in the first quarter.",
                        "evidence": {
                            "workout_id": workout["id"],
                            "length_count": len(standard_lengths),
                            "first_quarter_avg_seconds": round(first_time, 1),
                            "last_quarter_avg_seconds": round(last_time, 1),
                            "pace_fade_percent": round(pace_fade_pct, 1),
                        },
                    })
            first_quarter_avg_strokes = mean(row["stroke_count"] for row in first_quarter)
            last_quarter_avg_strokes = mean(row["stroke_count"] for row in last_quarter)
            if first_quarter_avg_strokes > 0:
                stroke_change_pct = (last_quarter_avg_strokes / first_quarter_avg_strokes - 1) * 100
                if stroke_change_pct >= 15:
                    insights.append({
                        "kind": "within_session_stroke_increase",
                        "title": "More strokes per length near the finish",
                        "detail": f"The final quarter averaged {last_quarter_avg_strokes:.1f} strokes per length, versus {first_quarter_avg_strokes:.1f} in the first quarter. This describes one session and does not establish why the count changed.",
                        "evidence": {
                            "workout_id": workout["id"],
                            "first_quarter_avg_strokes": round(first_quarter_avg_strokes, 1),
                            "last_quarter_avg_strokes": round(last_quarter_avg_strokes, 1),
                            "stroke_change_percent": round(stroke_change_pct, 1),
                        },
                    })
        heart_rate_trend = None
        if len(hr_values) >= 10:
            timed_hr = sorted(
                (item for item in measurements if item["workout_id"] == workout["id"] and "HeartRate" in item["type"]),
                key=lambda row: row["started_at"],
            )
            try:
                first_time = datetime.fromisoformat(timed_hr[0]["started_at"])
                last_time = datetime.fromisoformat(timed_hr[-1]["started_at"])
                span = (last_time - first_time).total_seconds()
                if span > 0:
                    first_values = [float(row["value"]) for row in timed_hr if (datetime.fromisoformat(row["started_at"]) - first_time).total_seconds() <= span * 0.2]
                    last_values = [float(row["value"]) for row in timed_hr if (last_time - datetime.fromisoformat(row["started_at"])).total_seconds() <= span * 0.2]
                    if first_values and last_values:
                        heart_rate_trend = round(mean(last_values) - mean(first_values), 1)
            except (TypeError, ValueError):
                heart_rate_trend = None
        if heart_rate_trend is not None and abs(heart_rate_trend) >= 10:
            direction = "higher" if heart_rate_trend > 0 else "lower"
            insights.append({
                "kind": "within_session_heart_rate_shift",
                "title": "Heart rate changed during the swim",
                "detail": f"The average in the final time window was {abs(heart_rate_trend):.1f} bpm {direction} than in the opening window. This is a descriptive comparison of recorded samples.",
                "evidence": {
                    "workout_id": workout["id"],
                    "early_late_change_bpm": heart_rate_trend,
                },
            })
        sessions.append({
            "workout_id": workout["id"],
            "started_at": workout["started_at"],
            "distance_m": distance,
            "duration_seconds": round(duration, 1),
            "pace_seconds_per_100m": round(pace, 1) if pace is not None else None,
            "average_heart_rate_bpm": round(sum(hr_values) / len(hr_values), 1) if hr_values else None,
            "heart_rate_samples": len(hr_values),
            "stroke_count": round(workout_strokes[workout["id"]], 1) if workout["id"] in workout_strokes else None,
            "pool_length_m": workout["pool_length_m"],
            "lengths_recorded": len(lengths),
            "length_series": [
                {
                    "length_index": index,
                    "distance_m": row["distance_m"],
                    "duration_seconds": round(row["duration_seconds"], 1),
                    "stroke_count": row["stroke_count"],
                }
                for index, row in enumerate(paired_lengths, start=1)
            ],
            "recorded_moving_time_seconds": round(moving_time, 1) if moving_time is not None else None,
            "estimated_moving_pace_seconds_per_100m": round(moving_time / (moving_distance / 100), 1) if moving_time and moving_distance else None,
            "average_strokes_per_length": round(mean(row["stroke_count"] for row in standard_lengths), 1) if standard_lengths else None,
            "average_swolf": round(mean(swolf_values), 1) if swolf_values else None,
            "pace_fade_first_to_last_quarter_percent": round(pace_fade_pct, 1) if pace_fade_pct is not None else None,
            "stroke_change_first_to_last_quarter_percent": round(stroke_change_pct, 1) if stroke_change_pct is not None else None,
            "heart_rate_early_late_change_bpm": heart_rate_trend,
            "unattributed_duration_seconds": round(max(0, duration - moving_time), 1) if moving_time is not None else None,
            "between_length_gaps_seconds": [
                round(max(0, (datetime.fromisoformat(following["started_at"]) - datetime.fromisoformat(previous["ended_at"])).total_seconds()), 1)
                for previous, following in zip(standard_lengths, standard_lengths[1:])
            ],
            "location_type": workout["location_type"],
        })

    sessions.sort(key=lambda row: row["started_at"])
    dated = [datetime.fromisoformat(row["started_at"]).date() for row in sessions]
    qualified = [row for row in sessions if row["pace_seconds_per_100m"] is not None]
    if sessions:
        longest = max((row for row in sessions if row["distance_m"] is not None), key=lambda row: row["distance_m"], default=None)
        if longest:
            insights.append({
                "kind": "personal_best_distance",
                "title": "Longest recorded swim",
                "detail": f"Your longest imported session was {longest['distance_m']:.0f} m.",
                "evidence": {"workout_id": longest["workout_id"], "started_at": longest["started_at"]},
            })
        if len(dated) >= 3:
            gaps = [(right - left).days for left, right in zip(dated, dated[1:])]
            insights.append({
                "kind": "training_frequency",
                "title": "Typical time between swims",
                "detail": f"The median gap between recorded swim sessions is {median(gaps):g} days.",
                "evidence": {"sessions": len(dated), "median_gap_days": median(gaps)},
            })
    if len(qualified) >= 8:
        previous, recent = qualified[-8:-4], qualified[-4:]
        old_pace = sum(row["pace_seconds_per_100m"] for row in previous) / len(previous)
        new_pace = sum(row["pace_seconds_per_100m"] for row in recent) / len(recent)
        delta_pct = (new_pace - old_pace) / old_pace * 100 if old_pace else 0
        if abs(delta_pct) >= 3:
            direction = "slower" if delta_pct > 0 else "faster"
            insights.append({
                "kind": "recent_pace_change",
                "title": "Recent pace shift",
                "detail": f"Average whole-workout pace in your latest four distance-recorded swims is {abs(delta_pct):.1f}% {direction} than the four before them.",
                "evidence": {
                    "previous_avg_seconds_per_100m": round(old_pace, 1),
                    "recent_avg_seconds_per_100m": round(new_pace, 1),
                    "change_percent": round(delta_pct, 1),
                    "sessions_per_period": 4,
                },
            })

    weeks = [
        {"week_start": week, "distance_m": round(float(values["distance_m"]), 1), "sessions": int(values["sessions"])}
        for week, values in sorted(by_week.items())
    ]
    missing_distance = sum(row["distance_m"] is None for row in sessions)
    missing_duration = sum(row["duration_seconds"] <= 0 for row in sessions)
    return {
        "session_count": len(sessions),
        "sessions": sessions,
        "weekly_training": weeks,
        "insights": insights,
        "data_coverage": {
            "workouts_with_distance": len(sessions) - missing_distance,
            "workouts_missing_distance": missing_distance,
            "workouts_missing_duration": missing_duration,
            "heart_rate_samples": sum("HeartRate" in item["type"] for item in measurements),
            "stroke_count_available": any("SwimmingStrokeCount" in kind for kind in measurement_types),
            "limitations": [
                "Whole-workout pace uses recorded duration and may include rests.",
                "Apple Health exports may not include lap-level splits or all stroke details.",
                "Comparisons are descriptive and are not adjusted for pool length, workout intent, or conditions.",
            ],
        },
    }
