# 100k measurement, re-run 2026-10-25

Database rebuilt from the frozen schema: `file_analysis_scale`, 100 000 `paths`
rows, 75 000 `content_signals`, built in 28.6 s
(`tools/audit/measure_scale_db.py`). Measured with `tools/audit/measure_queries.py`
against the application's own endpoints; 33 requests, 260 statements.
Raw: `audit_report/r14/performance_r14.json` (previous run of 2026-10-24 kept in
the same file under `prev_ms`).

## Slowest requests (ms, whole request)

| endpoint | now | previous | delta |
|---|---:|---:|---:|
| /api/lexis/manage/dashboard | 323.4 | 372.0 | -48.6 |
| /api/signals?limit=50&offset=1000 | 292.1 | 248.1 | +44.0 |
| /api/signals?limit=50&offset=49950 | 278.0 | 328.3 | -50.3 |
| /api/lexis/manage/files?page=2 | 263.9 | 297.4 | -33.5 |
| /api/lexis/manage/files?page=20 | 261.1 | 332.9 | -71.8 |
| /api/lexis/manage/files?page=1 | 254.5 | 298.0 | -43.5 |
| /api/signals?limit=50 | 242.0 | 247.5 | -5.5 |
| /api/reports/dashboard | 213.5 | 205.8 | +7.7 |
| /api/reports/overview | 182.6 | 204.5 | -21.9 |
| /files?page=40 | 106.4 | 124.5 | -18.1 |
| /files?page=1 | 99.4 | 127.2 | -27.8 |

The `+/-` column is wall-clock on a shared 2-vCPU sandbox: differences under
about 10% are noise, not improvements. Two signals are stable in both runs:
`/api/signals` with `identifier_kind` is the JSONB filter the frozen schema
cannot index (`evidence->>'kind'`, measured at 89-98 ms, unchanged), and
`/api/lexis/manage/*` remain the slowest pages (254-323 ms).

## Pagination at the ends of the table (ms)

| request | now | previous |
|---|---:|---:|
| /api/paths?offset=0&limit=50 | 10.4 | 9.4 |
| /api/paths?offset=50000&limit=50 | 16.5 | 16.5 |
| /api/paths?offset=99500&limit=50 | 20.9 | 25.9 |
| /api/paths?offset=0&limit=500 | 12.3 | 17.5 |
| /api/paths?offset=99500&limit=500 | 21.4 | 29.9 |
| /files?page=1 / page=5 / page=40 | 99.4 / 105.7 / 106.4 | 127.2 / 115.8 / 124.5 |

Offset paging stays flat: the last page of 100 000 rows costs 2x the first page
at `limit=50` and the server-rendered files list is page-position independent
(99-106 ms for pages 1, 5 and 40).

## N+1

`/api/signals`, `/api/signals/horizon`, `/api/paths`, `/api/places`,
`/api/reports/*`, `/api/scenarios`, `/api/sources`, `/api/sides`,
`/dashboard/charts`, `/dashboard/comprehensive`, `/api/search/suggestions`:
statement count flat with row count, nothing repeated.

Two requests repeat one statement per request rather than per row:
`/files` (17 statements, one repeated 7x) and `/api/lexis/manage/dashboard`
(13 statements, one repeated 5x) - constants, not per-row work.
