# Round 4 — what was done, the decisions still open, and where this stops

This file is the closing statement of round 4. It is not generated: every row
below refers to a commit, a test run or a measurement file committed in this
repository. Nothing is claimed that was not executed.

## What round 4 delivered

| step | outcome | commit |
| --- | --- | --- |
| modified/untracked work committed in logical groups, `git status` shown before and after each, affected tests run after each | done — six groups (tests for four pinned fixes, batch-report test, param probe + inventories, audit narrative, sides/schedules test split, run-now 503) | `2e76aff`, `534be39`, `7e69a52`, `7013a69`, `b0379b3`, `d32e71c` |
| 155 path-parameterised routes exercised with valid / missing / malformed / other-user ids, recorded in `findings/param_routes.csv`, inventories refreshed | done — 660 rows, 0 findings, 9 not-implemented (501), 65 skipped for missing fixtures; same probe on `370cde7` produces 8 findings, all fixed on HEAD | `7e69a52` |
| measurements only: `EXPLAIN (ANALYZE, BUFFERS)` for the ten heaviest queries, N+1 counting, pagination at 100k rows, failure injection (PostgreSQL stopped mid-ingest, app restarted mid-job) | done — numbers in `findings/performance_measurements.md`, raw runs in `evidence_scale/*.json` | `31baafe` |
| documented priority rule matched in code, test unedited | done — SQL and Python agree on all 8 ladder rows | `49e9d0c` (verified in `7e69a52`) |
| no generated docs/translations/licensing text committed | kept — `docs/` and `.cache/` remain untracked | — |

`git diff 2670f3b -- database/migrations` is empty after every commit. The
schema is untouched.

## D-1 … D-10, re-stated with the recommended default

| ID | what is open | recommended default | status after round 4 |
| --- | --- | --- | --- |
| **D-1** | `tests/integration/test_scenario_engine_pg.py` helper selects `alerts.rule_id` / `rule_evaluation_id` (4 failures); `test_sql_priority_agrees_with_the_python_rule` used to disagree (real defect) | **rewrite the helper onto the frozen columns** (`scenario_id`, `scenario_evaluation_id`, `metadata`); the priority disagreement is already fixed in code | 4 helper failures remain (re-measured this round: `UndefinedColumn: column "rule_id" does not exist`); the priority test **passes** |
| **D-2** | 14 tests assert constraint/index names the frozen schema spells differently | **update the tests to the live names** — a rename migration would break every deployed database for names no production code reads | 17 cases still red, unchanged |
| **D-3** | ~6 tests assume migrations `m0009`, `m0010`, `m0021`, `m0038`, `m0039` | **rewrite them against `m0001–m0003`**; do not invent migration history | unchanged |
| **D-4** | Places: `data/gazetteer/SOURCES.md` demanded as a seed input, `place:<id>` keys as a documented stopgap, 5 do-not-edit place tests | **add the packaging file and keep `place:<id>` documented as a stopgap**; the replacement design (category types + single-word terms + multi-word keywords) stays deferred | unchanged — `test_places_crud_pg::test_place_search_sort_pagination_and_mutation_authorization` still fails |
| **D-5** | `core.reporting` is imported by 2 tests and 2 tools but does not exist | **build the thin facade over `services/reporting`** | unchanged |
| **D-6** | Licensing gaps (`pyproject`, README, vendored notices, `pymupdf-layout` metadata) | **fill the metadata and notices only** — no behaviour change | unchanged |
| **D-7** | 24+ tests read generated docs that are not committed (38 failing cases) | **commit after your review**, with `DATABASE_SCHEMA.md` regenerated from the frozen chain | unchanged; `docs/` still untracked by design |
| **D-8** | 5 duplicate index shapes in the baseline | **register them in `docs/database/DUPLICATION_REGISTER.md`**, do not drop via migration | unchanged |
| **D-9** | Notification titles: stored title verbatim vs the old type labels | **keep the stored title** | applied |
| **D-10** | `tests/unit/test_notification_volume_guards.py` had been edited against the rule | **keep the revert to `2670f3b`**; it still fails, which is the honest state under the frozen chain | unchanged (still failing) |

Known failing do-not-edit tests, re-measured this round, one line each:
`test_places_crud_pg` 1, `test_title_parent_linkage` 1, `test_signal_explorer_pg` 1,
`test_notification_volume_guards` 1, `test_scenario_engine_pg` 4 (all from the
D-1 helper). `test_identifiers_intel` and `test_alert_indexes_exist` pass in
this checkout.

## New this round — findings the measurements raised (M-1 … M-8)

Full evidence in `findings/performance_measurements.md` §8 and
`findings/measurements_r4.csv`.

| ID | finding | recommended default |
| --- | --- | --- |
| **M-1** | `POST /api/import-export/batch-import` counts a file as *accepted* even when it cannot be queued: 30 files → `accepted: 30, queued: 5, rejected: 0`, 25 entries `status: error, "Failed to queue processing task"` (concurrent-task cap), dropped with no retry | **fix in a follow-up commit**: count queue failures in `rejected`/a new `dropped` field and refuse the request rather than silently discarding; needs your agreement because it changes an API response shape |
| **M-2** | Imports write nothing to `jobs`/`job_events`; a killed process loses the queue and nothing resumes; `GET /api/jobs` is always empty for imports | **needs a decision**: persist import jobs (bigger change) or document that imports are process-local and not resumable. Default: document now, propose persistence separately |
| **M-3** | Ingestion is superlinear above 512 KB — each doubling costs 3–4× the time (128 KB 2.0 s … 4 MB 321 s), 35 signals per KB; an 8 MB document produced no row in 300 s and would exceed the 1200 s timeout | **measure per-analyser timings before changing anything**; the fix is a performance task, not a one-line patch. Not attempted this round |
| **M-4** | All ten heaviest statements scan `paths` + `hash_contexts` in full; three spill sorts to disk (2.3–5.8 MB) | **no change** — schema frozen; index proposals belong in the deferred design proposal |
| **M-5** | `/api/signals` aggregates all signals per request; latency flat ~200–330 ms regardless of `limit`/`offset` | **no change** — same reason as M-4 |
| **M-6** | During a database outage `/health` answers 503 once, then hangs to the 30 s pool timeout; the body exposes the driver class name `OperationalError` | **small fix**: return 503 immediately on pool-exhaustion and keep the class name out of the body |
| **M-7** | A database outage signs every user out and the API answers `401 unauthenticated` with no hint that the cause was the outage | **product decision**: keep fail-closed 401, add `Retry-After`/a reason code, or keep as is. Default: keep the 401, add a reason code |
| **M-8** | `evidence->>'kind'` (identifier kinds) is a Parallel Seq Scan: ~26 ms at 75 000 signals, linear, not indexable without a schema change | **rely on it at this size**; anything larger needs an expression index, which is a schema change and therefore yours to approve |

## The four open questions, with the recommended default

| question | recommended default | what it costs |
| --- | --- | --- |
| **Commit the generated docs?** (D-7) | **commit only what you have read** — the three documents needing your review (`SECURITY.md`, `CONFIGURATION.md`, `DEVELOPMENT.md`) first, `DATABASE_SCHEMA.md` regenerated from the frozen chain (`--check` exit 0) | committing everything clears 38 red cases at once but publishes unread documents; leaving them uncommitted keeps 38 red and lets them drift |
| **Fill the 564 i18n gaps?** (en/ar 286, he/fa 465, hr 384) | **wait for a translator**; I invented no translation and will not machine-translate legal/intel screens | machine translation would turn the test green and degrade the product |
| **Licensing metadata?** (D-6) | **fill `pyproject`, README, `THIRD_PARTY_NOTICES.md`** and record `pymupdf-layout`'s missing metadata as a known gap | metadata only, no behaviour change; 4–5 tests green |
| **Does `core.reporting` need to exist?** (D-5) | **build the facade over `services/reporting`** (registry constants + dataset ids) | small; makes `tools/perf/keyness_perf.py` work again |

## Where this stops

Round 4's measurement step is finished: the numbers above were produced by the
committed harnesses against a real PostgreSQL and a real web process, and the
raw output of each run is committed next to them. The five items that need your
word before code moves — **M-1** (API response shape), **M-2** (persist import
jobs or document them as process-local), **M-3** (performance work), **M-6**
and **M-7** (outage behaviour), plus **D-1 … D-10** — are listed above with a
default for each. Nothing further is changed until you choose.
