# F. Performance Report (PHASE 6 — BLOCKED)

## Status: BLOCKED — no running application

No performance measurement was possible. The Flask application cannot be imported or started without PostgreSQL (F-01), and no browser is available for client-side measurement (F-04). Consequently:

- Application startup time: not measured.
- Page navigation / render latency: not measured.
- API response latency: not measured.
- Database query duration: not measured.
- Search performance: not measured.
- Critical workflow completion time: not measured.
- Throughput / memory / CPU: not measured.
- Cold-start vs warm-run: not distinguished.

## Basis for future measurement (from source inspection)

- `apps/web/app.py` logs requests slower than 1.0s (`after_request`) and endpoints slower than 2.0s (common.py), and adds an `X-Response-Time` header.
- Waitress (`WSGI_SERVER=waitress`) with `WAITRESS_THREADS` (default 32) is the recommended production server; each open Jobs page holds an SSE thread, justifying the high thread count.
- The job system is single-process, in-process threads; exactly one process per database. This caps concurrent job throughput and means a long-running job blocks a worker thread.
- `core/compute/` provides back-pressure admission control (`max_concurrency`, `queue_depth`, `admission_timeout_s`) and a compute gateway for device selection.
- Search uses cursor pagination and an explicit count mode — relevant for pagination-performance testing.

## Recommended provisional targets (for review, not acceptance criteria)

These are placeholders to be validated once the app runs against a real database:
- `/health` ≤ 500ms (single `SELECT 1` probe).
- Authenticated page GET ≤ 2s (above which the app already logs "SLOW ENDPOINT").
- API search results (first page) ≤ 2s on a representative corpus.
- Job creation (ingest) accepted ≤ 1s; job completion depends on corpus size and workers.

## What is needed to measure

1. PostgreSQL server + migrated test database.
2. Representative corpus of files for ingest/search benchmarks.
3. A load/measurement harness (Locust, `ab`, or simple timed `curl`/`pytest-benchmark`) — run only against isolated test databases, never production.
4. Browser + Playwright for client-side navigation/render latency.
