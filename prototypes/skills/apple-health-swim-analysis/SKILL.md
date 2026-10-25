---
name: apple-health-swim-analysis
description: Analyze Apple Health swimming exports for split pace, stroke, heart-rate, and training patterns. Use when a user provides Apple Watch or Apple Health swim data for analysis.
---

# Apple Health Swim Analysis

Analyze Apple Health swimming workout exports locally and explain what the records support. This skill is for descriptive swim training analysis; it does not diagnose health conditions or infer why a metric changed.

## Workflow

- Identify the provided `export.xml` or Apple Health ZIP. Prefer the project's `prototypes/swim-analytics-lab/analyze.py` when it is present; otherwise parse only swimming workouts and their relevant time-bounded measurements.
- Keep the export local. Do not copy raw records or full time series into documentation, logs, remote services, or unrelated files.
- Produce an aggregate report with workout date, distance, pool length, elapsed duration, timed length splits, stroke counts when present, heart-rate samples, and coverage/quality notes.
- Separate whole-workout pace from pace calculated only over timed distance samples. Label uncovered workout time as unattributed; it may include rests or recording gaps.
- Pair per-length stroke data by matching its timestamp to the distance sample. If pairing or coverage is uncertain, report the limitation and omit derived stroke/SWOLF values instead of guessing.
- Compare early and late lengths only within a session. Describe heart-rate shifts as changes in recorded samples, not as a medical or fitness conclusion.
- Compare sessions only when multiple suitable workouts exist; state the sample size and avoid strong trend claims from a small baseline.
- Explain notable findings with the values and calculation used. Distinguish observations from hypotheses and recommendations.
- When working in the Swim Lab repository, update `docs/DEVELOPMENT_LOG.md` with the plan, implementation outcomes, and concise decisions; do not write private step-by-step reasoning or include raw health records.
- Change the main web service only when that is part of the user's request. Keep reusable analysis in the service layer and expose its evidence through the existing API/dashboard patterns.

## Metric definitions

Read [references/metrics.md](references/metrics.md) when calculating or explaining split, pace, SWOLF, gaps, or heart-rate comparisons.
