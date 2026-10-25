# Swim Lab — development log

This file tracks plans, observable changes, outcomes, and concise reasons for implementation choices. It is not a private step-by-step reasoning transcript.

## 2026-10-23 — first dashboard

### Plan

1. Add a responsive dashboard in Russian for the current swim-analysis API.
2. Include in-browser upload so the user can import the Apple Health export without using `curl`.
3. Show history and session/split metrics already available from the export, with uncertainty visible.
4. Document completed work, architecture decisions, and the next milestones.

### Changes

- Added `/` as the dashboard page and `/static/*` for its local assets; the JSON API remains under `/api`.
- Added a summary header, four metric cards, weekly volume chart, latest-session card, per-length chart, observations, and workout history table.
- Added ZIP/XML upload by sending the selected file directly to `POST /api/import`.
- Added responsive styles for mobile and desktop, keyboard/semantic controls, reduced-motion handling, and visible import errors/status.
- Removed remote font loading so the interface does not need third-party requests.
- Extended analysis output with length-by-length samples for charting; parsed the pool length from Apple Health metadata.
- Added `PROJECT_PLAN.md` and this development log.

### Decisions and rationale

- The dashboard is plain HTML/CSS/JavaScript served by FastAPI: this avoids a separate frontend server and build setup for a single-user local project.
- Russian is the initial UI language to match the user's interaction language.
- Charts are rendered with SVG in the browser without a charting dependency; current data size is small, and this keeps the app self-contained.
- The dashboard uses sample-based heart rate and displays whole-session and recorded-moving pace separately because rest intervals make them materially different.
- No full user health records or personal workout values are copied into this log.

### Status

- Implementation is in place. A browser review and user feedback are still needed; this turn did not start Docker or claim a live-page visual verification.

## 2026-10-23 — swim analytics prototype and first integration

### Plan

1. Build an offline prototype that reads Apple Health XML/ZIP and reports swim-specific split, stroke, pace, and heart-rate patterns.
2. Run it against the latest provided archive and inspect data quality before changing the web service.
3. Port useful, explainable observations into the existing FastAPI analysis payload and dashboard.
4. Record the repeatable workflow and consider a reusable Skill after the prototype works.

### Changes

- Added `prototypes/swim-analytics-lab/analyze.py`, a standalone CLI/report generator that reuses the app's export parser and does not connect to PostgreSQL.
- Added a prototype README with run instructions and metric rules. Generated report/JSON output is local and git-ignored.
- The analysis reports explicit workout distance when available and labels its sample-sum fallback, keeps whole-workout and recorded-length pace separate, calculates paired stroke/SWOLF metrics, summarizes per-length gaps and HR samples, and flags within-session changes cautiously.
- Added first-to-last-quarter stroke change, descriptive HR change, unattributed duration, and per-length gaps to the main analysis response. Added stroke and HR observations to the dashboard.
- Ran the prototype on the latest ZIP export. It found one swim with 24 timed 25 m lengths and 398 HR samples. The timed lengths cover 10:30 of the 35:52 workout; the remaining time is left unattributed because records cannot distinguish rest from missing length data. The sample HR average and workout summary agree within 1 bpm, so no mismatch is reported.
- On this single session, the last six lengths averaged 35.3 s versus 22.8 s in the first six (+54.7%); recorded strokes averaged 12.5 versus 10.2 (+23.0%). These are within-session observations only.

### Decisions and rationale

- Kept the prototype isolated from the web service and database first, then ported the established calculations into the existing service layer.
- Matched stroke samples to distance samples by the Apple Health start timestamp, consistent with the current parser's record representation; this pairing still needs confirmation across additional export variants.
- Kept source conflicts and uncovered workout duration visible instead of guessing. This archive's HR summary does not materially conflict with its sample series.
- Logged findings at an aggregate level only; no raw export records or full sample series are included here.
- Private step-by-step reasoning is not recorded. This log captures the plan, decisions, changes, and observable outcomes.

### Status

- Offline prototype ran successfully and produced an HTML report plus machine-readable JSON under its ignored output directory.
- Core observations are now included in the service analysis response and dashboard insight list. Database-backed page verification remains pending because Docker was not started.
- Added and installed the `apple-health-swim-analysis` Skill at `~/.codex/skills/apple-health-swim-analysis`, with metric definitions in a reference file.
- The Skill creator's validator could not run because PyYAML is unavailable in the bundled/system Python environments. Validated the YAML frontmatter and UI metadata with Ruby's YAML parser, checked for unfinished TODO placeholders, and compiled the changed Python modules successfully.
