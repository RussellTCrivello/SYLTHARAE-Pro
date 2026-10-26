# G. Defect Register (Markdown)

Prioritized findings from the SYLTHARAE-Pro audit. Machine-readable copy: `G_defect_register.csv`.

Verification statuses used:
- `VERIFIED UNFIXED` — reproduced or established present in the current checkout.
- `UNVERIFIED` — insufficient evidence to establish correctness or failure.
- `BLOCKED` — an environmental/safety constraint prevents verification.
- `NOT APPLICABLE` — does not apply to the actual architecture.

---

## F-01 — Application cannot import or start without a running PostgreSQL server

- **Severity:** P1 — High
- **Status:** VERIFIED UNFIXED
- **Subsystem:** Backend / startup / database
- **Reproduction prerequisites:** Python 3.11 with psycopg2-binary installed; no PostgreSQL server on localhost:5432; network limited to PyPI/npm/GitHub (PostgreSQL not installable via apt).
- **Exact reproduction steps:**
  1. Create a venv and install `flask` + `psycopg2-binary` from PyPI.
  2. From the repo root run: `python -c "from apps.web.app import app"`.
  3. Observe the traceback.
- **Expected behavior:** The Flask app object constructs (or fails with a clear, actionable configuration error) without requiring a live database at import time.
- **Actual behavior:** `psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused`. The failure originates in `Api/utils/utils.py` → `DatabaseHub()` → `database.Database._initialize_pool()` → `ThreadedConnectionPool`, and is compounded by `core/security/bootstrap_admin.py::ensure_initial_admin()` querying the `users` table at startup. No graceful degradation or offline/setup-only mode exists.
- **Evidence source:** Import traceback captured during attempted execution (2026-10-23 07:43); same error during `pytest tests/unit` runs ("connection to server at localhost:5432 failed: Connection refused"). `verify_readiness.py` database checks cannot execute.
- **Relevant objects:** `Api/utils/utils.py`, `database/database/database.py`, `core/security/bootstrap_admin.py`, `apps/web/app.py`, `run_web.py`.
- **Root cause:** Hard hard-coded database dependency at module import time; no fallback; no lazy initialization.
- **User/operational impact:** The operator cannot launch the UI or API at all without first provisioning and migrating a PostgreSQL database. The system is non-functional out of the box in any environment lacking PostgreSQL. This blocks every runtime verification step (backend, browser, e2e).
- **Recommended remediation:** Document PostgreSQL as a hard prerequisite; ideally add lazy/failing-soft database initialization so the app can at least construct and show a clear setup/maintenance page when the database is unavailable. Guard `bootstrap_admin` and `DatabaseHub` so a missing database does not abort import.
- **Regression risk:** High — blocks all runtime verification.
- **Follow-up:** Re-attempt import and `verify_readiness.py` after PostgreSQL is available; confirm `/health` returns 200/503 appropriately.

---

## F-02 — Changelog and documentation describe migrations and documents that do not exist in the current checkout

- **Severity:** P1 — High
- **Status:** VERIFIED UNFIXED
- **Subsystem:** Documentation / schema / changelog
- **Reproduction prerequisites:** None (static inspection of the current checkout).
- **Exact reproduction steps:**
  1. Read `CHANGELOG.md` section "v2.2.0 — unreleased".
  2. List `database/migrations/*`.
  3. Check for `docs/` directory and `docs/reference/DATABASE_SCHEMA.md`.
- **Expected behavior:** The CHANGELOG describes only changes present in the current checkout, or is clearly marked planned/unimplemented.
- **Actual behavior:** `CHANGELOG.md` v2.2.0 unreleased describes migrations `m0038` "redundant_enforcement_removal" and `m0039` "vocabulary_constraints", states "docs/reference/DATABASE_SCHEMA.md regenerated from a freshly migrated database; tools/docs/generate_schema.py --check is clean", and claims these are "on the current branch". The checkout contains only migrations `m0001`–`m0003`. There is no `docs/` directory at all, and while `tools/docs/generate_schema.py` exists, no generated `DATABASE_SCHEMA.md` is present. The `deliverables/interface_inventory.md` likewise references `docs/INTERFACE_REGISTRY.md` and a screenshot snapshot commit `aa2b865a...` that is not the current HEAD (`2670f3b`).
- **Evidence source:** `CHANGELOG.md` lines 21–49; `deliverables/interface_inventory.md`; directory listing of `database/migrations/` (m0001–m0003 only) and `docs/` (absent).
- **Relevant objects:** `CHANGELOG.md`, `deliverables/interface_inventory.md`, `database/migrations/`, `docs/` (absent).
- **Root cause:** Documentation drift — the changelog describes work not present in the code.
- **User/operational impact:** An operator or auditor relying on the changelog would believe uniqueness/vocabulary constraints (m0038/m0039) and a schema reference document exist when they do not — a data-integrity and audit-risk concern.
- **Recommended remediation:** Reconcile `CHANGELOG.md` with the actual migration set (either apply m0038/m0039 and generate `DATABASE_SCHEMA.md`, or mark the changelog entries as planned/not-in-this-checkout). Regenerate or remove stale docs references.
- **Regression risk:** Medium — documentation drift can mislead operators and auditors about the enforced schema.
- **Follow-up:** Verify that every migration named in `CHANGELOG.md` either exists in `database/migrations/` or is explicitly marked planned.

---

## F-03 — Existing verification suite cannot run end-to-end (no PostgreSQL, no optional binaries)

- **Severity:** P1 — High
- **Status:** VERIFIED UNFIXED
- **Subsystem:** Testing / CI
- **Reproduction prerequisites:** No PostgreSQL server installable (no apt permission; network restricted to PyPI/npm/GitHub); no tesseract/OCR binary; no pytest-playwright.
- **Exact reproduction steps:**
  1. Run `pytest tests/unit` from the repo root.
  2. Observe `tests/conftest.py` `pg_settings` fixture: it probes pgserver / `DB_HOST` / application config and skips the entire integration suite when no PostgreSQL is reachable.
  3. Observe unit tests fail/error on missing database and missing optional modules.
- **Expected behavior:** The test suite executes and reports pass/fail for the public API contract and integration behavior.
- **Actual behavior:** Integration suite is skipped wholesale ("No reachable PostgreSQL for the integration suite"). Unit run: 100 failed + 61 errored (of those collected), overwhelmingly due to database connection refusal or missing optional dependencies (e.g. PIL/Pillow previously installed mid-session; tesseract OCR binary; test fixtures). A subset passed (e.g. `test_version_consistency`, `test_session_cookie_config`, `test_passwords_and_errors`).
- **Evidence source:** `tests/conftest.py` (`pg_settings`, `pg_db` fixtures skip when no PostgreSQL); pytest run log `/tmp/unit_results.log`; `tests/unit/*.py` failures.
- **Relevant objects:** `tests/conftest.py`, `tests/integration/*`, `tests/security/*`, `pytest`.
- **Root cause:** The test suite is hard-coupled to a disposable PostgreSQL server; this environment cannot provide one.
- **User/operational impact:** The existing verification cannot validate the public API contract, business logic, or persistence in this environment. Test effectiveness (Phase 7) cannot be assessed by execution here.
- **Recommended remediation:** Either provision a disposable PostgreSQL for the test environment, or mark DB-dependent tests and provide a DB-free subset that can run in locked-down environments. Do not treat skipped integration tests as coverage.
- **Regression risk:** High — most of the suite cannot execute, so defect detection via tests is not demonstrable here.
- **Follow-up:** If PostgreSQL is provisioned, rerun the full suite and re-classify each failure as environmental or a real defect.

---

## F-04 — Real interactive browser testing cannot be performed

- **Severity:** P1 — High
- **Status:** VERIFIED UNFIXED
- **Subsystem:** Frontend / browser automation
- **Reproduction prerequisites:** No browser binary (Chrome/Chromium/Firefox) installed; no Playwright; no XVFB; network restricted to PyPI/npm/GitHub so browsers cannot be downloaded.
- **Exact reproduction steps:**
  1. Check for browser binaries (`which chromium google-chrome firefox`).
  2. Check for Playwright (`python -m playwright --version`, `npm`).
  3. Confirm none are present.
- **Expected behavior:** The mandatory Phase 3 interactive browser testing is executable in a real browser.
- **Actual behavior:** No browser and no browser-automation framework are available. Playwright is not installed (`python -m playwright --version`: "No module named playwright"); no chromium/firefox binaries on PATH; no XVFB; `apt-get update` fails with permission denied on `/var/lib/apt/lists/partial`.
- **Evidence source:** `which`/browser checks; `python -m playwright`; `apt-get update` failure.
- **Relevant objects:** No browser tooling; `static/js/*` and `templates/` exist but cannot be exercised in a real browser.
- **Root cause:** Absence of browser/automation tooling plus network restrictions.
- **User/operational impact:** Phase 3 (real interactive frontend testing) and Phase 6 (browser-side performance measurement) are blocked. No screenshots, console-error capture, or network-trace evidence from a live browser can be produced here.
- **Recommended remediation:** Install Playwright with a browser, or provide a browser binary and XVFB, in an environment with network access to download browsers.
- **Regression risk:** High — the mandatory interactive browser phase cannot be executed.
- **Follow-up:** Document the blocker (this report); if a browser environment is provided, execute Phase 3 workflows and capture evidence.

---

## F-05 — Deliverables describe a different snapshot than the current checkout

- **Severity:** P2 — Medium
- **Status:** VERIFIED UNFIXED
- **Subsystem:** Documentation / deliverables
- **Reproduction prerequisites:** None (static inspection).
- **Exact reproduction steps:**
  1. Read `deliverables/interface_inventory.md` first line.
  2. Read `git log` / HEAD commit.
- **Expected behavior:** Deliverables correspond to the repository state being audited.
- **Actual behavior:** `interface_inventory.md` states "Repository snapshot: aa2b865a24c429e242a457a60d2aef84661389b2 (2026-10-16)" and "34 interfaces and 81 owned endpoints (33 active, 1 deprecated)". The current checkout HEAD is `2670f3b` (single squashed commit). The `core/interfaces/registry.py` in this checkout declares 30 interfaces (not 34) with a different domain set. `feature_matrix.csv` and `interface_screenshots.zip` therefore describe a different build.
- **Evidence source:** `deliverables/interface_inventory.md`; `git log`; `core/interfaces/registry.py`.
- **Relevant objects:** `deliverables/interface_inventory.md` (cites snapshot aa2b865a); current HEAD `2670f3b`.
- **Root cause:** Deliverables were generated from a different snapshot and were not regenerated for this checkout.
- **User/operational impact:** Screenshots, feature matrix, and interface counts do not match the audited checkout — confusion risk for anyone cross-referencing deliverables.
- **Recommended remediation:** Regenerate deliverables against the current checkout (`2670f3b`) or clearly label them as belonging to snapshot `aa2b865a`. Do not use them as evidence of the current state.
- **Regression risk:** Low.
- **Follow-up:** Re-derive the interface inventory from `core/interfaces/registry.py` for this checkout.

---

## F-06 — Bare `except: pass` blocks may swallow failures and report false success (suspected)

- **Severity:** P2 — Medium
- **Status:** UNVERIFIED
- **Subsystem:** Backend / route error handling
- **Reproduction prerequisites:** Source inspection only; the app cannot be started to trigger the error paths.
- **Exact reproduction steps:**
  1. Grep `Api/routes` and `core` for `except` blocks followed by `pass`.
  2. Inspect candidates: `setup.py:562`, `words.py` (multiple: :95, :209, :265, :297, :336), `archives_api.py:1772`, `file_operations.py:85`, `api.py:224`, `common.py:153`.
- **Expected behavior:** Exceptions are logged or surfaced, not silently swallowed.
- **Actual behavior:** Multiple `except: pass` blocks exist across route modules; impact not confirmed because the app cannot run.
- **Evidence source:** Static grep of `Api/routes/*.py` and `core/*.py` (found `pass` in except at the listed locations).
- **Relevant objects:** `Api/routes/setup.py`, `Api/routes/words.py`, `Api/routes/archives_api.py`, `Api/routes/file_operations.py`, `Api/routes/api.py`; note: `Api/routes/health.py` was inspected and correctly reports DB errors (NOT a silent swallow).
- **Root cause:** Defensive exception handling that swallows errors without logging.
- **User/operational impact:** Failures could be hidden, producing false-success responses or stale data.
- **Recommended remediation:** Review each `except: pass`; replace with logging + appropriate error response or re-raise.
- **Regression risk:** Medium — changing error handling could alter behavior; test each route after editing.
- **Follow-up:** Run the affected routes through the test suite once PostgreSQL is available; confirm errors surface correctly.

---

## F-07 — Optional runtime dependency absence degrades capabilities (Excel export disabled)

- **Severity:** P3 — Low
- **Status:** VERIFIED UNFIXED
- **Subsystem:** Backend / optional features
- **Reproduction prerequisites:** Run the app or import `export_service`; `openpyxl` not installed.
- **Exact reproduction steps:**
  1. Observe `export_service.py` logs "openpyxl not available, Excel export will be disabled".
  2. Confirm `openpyxl` absent from the venv.
- **Expected behavior:** Excel export is available when `openpyxl` is installed.
- **Actual behavior:** "openpyxl not available, Excel export will be disabled" warning at import/startup.
- **Evidence source:** `root:export_service.py:22` (observed in pytest output).
- **Relevant objects:** `services/export_service.py`.
- **Root cause:** `openpyxl` not installed; the export path degrades silently with only a log warning.
- **User/operational impact:** Users cannot export to Excel; other optional readers (PDF, audio, archives) may also degrade if their extras are missing.
- **Recommended remediation:** Install optional dependencies (`openpyxl`, PyMuPDF, `pytesseract`+tesseract, etc.) per `requirements.txt` extras, or degrade gracefully with a user-visible message.
- **Regression risk:** Low — disabling an export format does not corrupt data.
- **Follow-up:** Confirm which export/reader paths are exercised and whether degraded paths are clearly communicated to the user.

---

## Summary of statuses

| Finding | Severity | Status |
|---------|----------|--------|
| F-01 App cannot start without PostgreSQL | P1 High | VERIFIED UNFIXED |
| F-02 Changelog/docs drift (m0038/m0039, DATABASE_SCHEMA.md) | P1 High | VERIFIED UNFIXED |
| F-03 Verification suite cannot run end-to-end | P1 High | VERIFIED UNFIXED |
| F-04 Real browser testing cannot be performed | P1 High | VERIFIED UNFIXED |
| F-05 Deliverables snapshot mismatch | P2 Medium | VERIFIED UNFIXED |
| F-06 Bare except:pass blocks (suspected) | P2 Medium | UNVERIFIED |
| F-07 Optional dependency degrades Excel export | P3 Low | VERIFIED UNFIXED |

No P0 (Critical) findings were confirmed. No runtime security or data-integrity defects could be confirmed or refuted because the application cannot run in this environment.
