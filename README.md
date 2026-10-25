# Swim Lab

A local-first pet project for collecting and analyzing Apple Watch swimming workouts.

## How data gets here

The first version uses Apple Health's built-in export. On iPhone, open **Health → profile picture → Export All Health Data**, then transfer the resulting ZIP to this Mac. The importer accepts either that ZIP or its `export.xml`. It extracts swimming workouts and selected swimming, heart-rate, and energy samples into PostgreSQL. Re-importing the same export is safe; existing records are skipped.

This is an initial collection path, not live Watch streaming. A later iPhone companion app can read HealthKit with explicit per-data-type permission and sync new workouts to this service. Starting with the built-in export lets us validate the analysis against real data before taking on iOS app distribution and background sync.

## Run on this Mac

With Docker Desktop running:

```bash
docker compose up --build
```

The API is at <http://localhost:8000> and interactive docs are at <http://localhost:8000/docs>. PostgreSQL runs as a separate container; its named Docker volume persists data across container restarts and rebuilds.

To connect to this PostgreSQL database from a desktop client such as DBeaver, use host `localhost`, port `5433`, database `swimlab`, username `swimlab`, and the local development password `swimlab-dev`. The port is bound only to this Mac. Port `5432` is used by another local project on this machine.

The dashboard is at <http://localhost:8000>. It shows workout totals, weekly distance, session history, split timing, heart-rate samples, SWOLF where the export has matching length and stroke samples, and data-backed observations. Use **Импорт** to choose an Apple Health ZIP/XML in the browser or drag it into the upload area. The browser sends the export directly to the local API; the original file is not saved by the service.

To import the Apple Health ZIP:

```bash
curl -X POST --data-binary @export.zip http://localhost:8000/api/import
```

Or import the extracted XML:

```bash
curl -X POST --data-binary @export.xml 'http://localhost:8000/api/import?filename=export.xml'
```

Useful endpoints:

- `GET /api/workouts` — recent swimming workouts.
- `GET /api/summary` — workout count, total and average distance, average pace and duration, and sample statistics.
- `GET /api/analysis` — per-session pace and heart rate, weekly distance, data coverage, and evidence-backed training observations.
- `POST /api/import` — raw ZIP or XML request body.

## Code layout

```text
app/
  api/routes/       HTTP endpoints and request handling
  core/             application configuration
  db/               PostgreSQL connection lifecycle and ORM table definitions
  domain/           core workout and measurement entities
  repositories/     SQL queries and persistence
  schemas/          API request and response models
  services/         Apple Health parsing and swim analysis logic
  web/static/       self-contained Russian-language dashboard (HTML/CSS/JS)
  main.py           FastAPI application factory and startup lifecycle
```

Route handlers translate HTTP requests and responses. Services contain parsing and analysis rules, while repositories own SQL. This keeps the domain work reusable if the API or database changes later.

## Analysis roadmap

1. **Foundation (done):** import Apple Health exports, store workouts and samples in PostgreSQL, and calculate baseline summaries.
2. **First analysis (done):** per-session distance/pace, length timing, heart rate, stroke count, and SWOLF when the required inputs are present.
3. **Dashboard (first version):** overview, weekly chart, split chart, workout history, and in-browser import. Next: refine from your feedback and add date/location filters.
4. **Automatic collection (future):** build an iPhone companion using HealthKit read access, then securely sync new workouts to this Mac or another chosen host.

The project plan and concise development/decision log live in [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) and [`docs/DEVELOPMENT_LOG.md`](docs/DEVELOPMENT_LOG.md). They record observable decisions and outcomes, not private step-by-step reasoning.

## How Apple Watch data reaches the project

Today, there is no direct Apple Watch connection in this repository. The Apple Watch records workouts and sensor samples in HealthKit. The paired iPhone's Health app can export the Health database as a ZIP containing `export.xml`; you manually transfer that file to the Mac and POST it to `/api/import`. The server opens the XML in memory, selects swim workouts, attaches measurement records whose timestamps fall within each workout, then writes normalized workout and measurement rows to PostgreSQL. The original ZIP/XML is not stored.

The future automatic path is an iPhone app with Apple's HealthKit capability. After you grant read access to workout, swimming distance, stroke count, heart rate, and energy types, the app queries HealthKit for new swim workouts and their associated samples. It then sends those structured records to an authenticated sync endpoint on this API. The watch itself does not send data to this FastAPI server; HealthKit on the iPhone is the bridge. HealthKit permissions are per data type and can be revoked, and Apple may give an app only a limited historical window.

Current import fields come from workout summaries (activity, start/end, duration, total distance, energy, and swim location metadata) plus time-series health records (heart rate, swimming distance, stroke count, and energy). Metrics that Apple does not include in the export cannot be calculated from this import alone.

Apple Health may omit some fine-grained split or stroke details from an export. The analysis will show which metrics are actually present rather than infer missing values. HealthKit access for a companion app requires explicit user authorization for each requested data type.

## Privacy and storage

The service binds to the local Docker port and stores data on this Mac. Do not expose it to the public internet as-is: there is no authentication or transport encryption yet. The raw export is processed in memory and is not retained; only swimming workout rows and selected measurements are stored in PostgreSQL. Keep the original export somewhere private until you have confirmed the import.
