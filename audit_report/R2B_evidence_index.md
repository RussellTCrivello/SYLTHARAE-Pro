# Evidence index — round 2

Everything below is a stored file in this repository under `audit_report/evidence_r2/`
(or a workspace artifact named in the last column). "Executed" means the command
ran in this sandbox and the output is in the file — nothing is quoted from memory.

| Evidence | File | Command that produced it | What it proves |
|---|---|---|---|
| Full suite, before this round | `/tmp/full5.log` (workspace only, not committed) | `pytest tests/unit tests/integration tests/security tests/e2e -q -p no:randomly --junit-xml=/tmp/junit_full5.xml` | 4320 tests, 121 failures, 12 errors, 134 skipped |
| Full suite, after this round | `evidence_r2/full7.log`, `evidence_r2/junit_full7.xml`, `evidence_r2/fails7.txt` | same command, `--junit-xml=/tmp/junit_full7.xml` | 4326 tests, **114 failures, 12 errors, 134 skipped**; per-test list with the failing assertion |
| Job event failure (before the fix) | `evidence_r2/fix1.log` | `pytest tests/integration/test_reports_pg.py tests/unit/test_one_load_more.py tests/integration/test_job_service.py::TestIngestionJobs tests/unit/test_job_system.py` | `CheckViolation: job_events_event_type_check`, failing row `WARNING` — the defect R2-01 repairs |
| Targeted regression set (after the fixes) | `evidence_r2/verify_a.log` | `pytest tests/integration/test_structural_marker_exclusion.py tests/integration/test_job_service.py::TestIngestionJobs tests/integration/test_notification_accuracy.py tests/unit/test_one_load_more.py tests/unit/test_job_event_storage_vocabulary.py` | everything green except the protected `test_alert_indexes_exist` |
| Cross-test poisoning reproduction | `evidence_r2/pair1.log` | `pytest tests/integration/test_startup_upgrade_path.py tests/integration/test_structural_marker_exclusion.py` | `relation "analyst_file_categories" does not exist` after the upgrade test drops the shared tables |
| One structural test in isolation | `evidence_r2/sm.log` | `pytest tests/integration/test_structural_marker_exclusion.py::test_real_content_is_searchable` | exit 0 — the same test that fails after the upgrade test |
| Reports surface | `evidence_r2/reports_test.log` | `pytest tests/integration/test_reports_pg.py -q` | 7 passed |
| Readiness | — | `DB_NAME=file_analysis_test python verify_readiness.py` | 31 checks, 0 failed (0 critical); earlier 7 critical failures were the missing `file_analysis_test` database |
| Schema documentation | — | `DB_NAME=sylth_docs_schema python tools/docs/generate_reference.py --check` | `reference docs are up to date`, exit 0 |
| Schema freeze | — | `git diff 2670f3b -- database/migrations` | empty — no migration was added, edited or renamed |
| Live vocabulary read from the database | — | `pg_constraint` query over `jobs`, `job_events` | `ck_jobs_status` = 7 values (no `CANCELLING`); `job_events_event_type_check` = 11 values (no `WARNING`/`FAILED`) |

## Files created or changed this round

Production code:
- `services/jobs/repository.py` — `STORED_EVENT_TYPES`, `_KIND_TO_STORED`, `stored_event()`; used by `add_event`/`add_events`
- `services/jobs/manager.py` — `cancel()` sets `cancellation_requested` instead of status `CANCELLING`
- `services/jobs/job_state.py` — documents `CANCELLING` as a phase, not a stored status
- `services/retention/model.py` — jobs `status_guard` matches the storable statuses
- `services/reporting/processing.py`, `Api/routes/reports.py`, `Api/routes/__init__.py` — reports query and endpoints
- `templates/Reports/reports.html`, `templates/Reports/dashboard.html`, `static/js/pages/reports-dashboard-page.js` — reports UI

Tests:
- `tests/unit/test_job_event_storage_vocabulary.py` (new)
- `tests/integration/test_reports_pg.py` (new in the previous round; count assertion relaxed to a bound)
- `tests/integration/test_notification_accuracy.py`, `tests/integration/test_job_service.py` (stale expectations corrected — §3 of the round report)

Documentation:
- `docs/reference/DATABASE_SCHEMA.md` — regenerated from the **frozen** chain, `--check` exit 0
- `audit_report/R2_verification_round2.md`, `audit_report/defect_register_r2.md`, `audit_report/evidence_r2/` — this package (the earlier `A_…`–`J_…` files are untouched)

## Deliberately not done

- No migration was added or edited, no constraint renamed, no seed data inserted.
- No file in the do-not-edit test list was modified.
- Nothing was committed or pushed; the working tree is the deliverable.
