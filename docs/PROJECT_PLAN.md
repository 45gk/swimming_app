# Swim Lab — project plan

**Goal:** a private, local-first tool that collects Apple Watch swimming workouts, stores them on a chosen device, and helps spot patterns in training.

## Current scope

- [x] FastAPI service split into API, domain, service, repository, database, and web layers.
- [x] PostgreSQL persistence through Docker Compose.
- [x] Apple Health ZIP/XML import, retaining swimming workouts and selected in-session measurements.
- [x] First analysis pass: workout summaries, 25 m length timing, sample-based heart rate, stroke totals, SWOLF where paired data is present, and cautious within-session observations.
- [x] Russian-language responsive dashboard served by the same FastAPI app.
- [x] Browser upload for an Apple Health ZIP or `export.xml`.
- [x] Development decisions and completed work recorded in `DEVELOPMENT_LOG.md`.
- [x] Offline analysis prototype for pace fade, stroke-count changes, heart-rate distribution, and data coverage.
- [x] Ported validated within-session pace, stroke, and heart-rate observations into the main analysis API/dashboard.

## Next milestones

1. **Review this dashboard:** refine labels and chart behavior based on actual use.
2. **Improve analysis:** validate length/stroke pairing across more export variants; refine work/rest intervals; compare sessions after enough workouts exist.
3. **Reusable workflow:** refine the installed swim-analysis Skill against future export variants.
4. **Add exploration controls:** date range, pool length, indoor/open-water filters, and exportable summaries.
5. **Automatic collection:** create an iPhone companion with explicit HealthKit read permissions and an authenticated sync protocol to this API.
6. **Deployment hardening:** credentials through local environment/secrets, authenticated remote access, schema migrations, and backup/restore guidance before using another device.

## Current constraints

- Apple Health export is manual; the Watch does not stream directly to this server.
- Apple exports may omit lap, stroke, or other detailed data.
- Whole-workout pace includes recorded rests; split-level pace uses only time-bounded distance samples.
- First-session observations describe one workout and are not longitudinal conclusions.
- The prototype treats heart-rate changes as descriptive sample comparisons, not fitness or medical conclusions.
- The app has no authentication. Keep it on a trusted local network until remote access is secured.

## Architecture decisions

- Serve a static HTML/CSS/JavaScript dashboard from FastAPI. This keeps one local origin, avoids CORS setup and a frontend build chain, and simplifies Docker use.
- Keep the visual layer dependency-free and self-hosted; health data and UI assets do not need third-party CDN requests.
- Make observations explainable by returning their evidence values alongside their labels.
- Treat missing or conflicting source metrics as data-quality notes rather than silently filling them with estimates.
