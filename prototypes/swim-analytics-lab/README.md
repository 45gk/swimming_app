# Swim Analytics Lab

An offline analysis prototype for Apple Health swim exports. It reuses the
project's XML/ZIP parser, calculates experimental split, stroke, pace, heart
rate, SWOLF, and data-quality metrics, and can render a standalone HTML report.
It does not connect to PostgreSQL or change the FastAPI service.

## Run locally

```bash
python prototypes/swim-analytics-lab/analyze.py /path/to/export.xml \
  --report prototypes/swim-analytics-lab/output/report.html \
  --json prototypes/swim-analytics-lab/output/analysis.json
```

The report and JSON are generated locally and excluded from version control.
The export is read-only. The tool only analyzes swimming workouts and a small
set of measurements attached to those workout intervals.

## Prototype rules

- Prefer explicit workout summary distance. If it is absent, sum the available
  swimming distance samples and mark their source in the output.
- Use paired length time and stroke samples for per-length stroke and SWOLF
  metrics; do not infer missing values.
- Keep workout-level pace separate from pace across timed length samples.
- Treat time not covered by length records as unattributed; it may include
  rests or gaps in recording.
- Show workout HR summary and sample-series average separately when they
  disagree.
- Within-session changes describe one session only. Session-to-session trends
  need a growing baseline.

## Next step

Review these calculations against the exported records and the user's
interpretation. Only then port selected rules into `app/services/swim_analysis.py`
and the main dashboard/API.
