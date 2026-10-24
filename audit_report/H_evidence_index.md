# H. Evidence Index

**Sanitization:** No secrets, credentials, production endpoints, or customer data appear in this report or in any captured artifact. `.env` does not exist in the checkout; no `.flask_secret_key` or `data/settings.json` was left behind (created during testing, then removed). No real credentials were captured because no live application was reachable.

## Artifacts produced in this audit

| Artifact | Path | Description |
|----------|------|-------------|
| Defect register (CSV) | `audit_report/G_defect_register.csv` | Machine-readable findings (F-01…F-07) with all required fields |
| Defect register (Markdown) | `audit_report/G_defect_register.md` | (included below/see A–J sections) — findings summarized in A and detailed in B–J |
| Executive assessment | `audit_report/A_executive_assessment.md` | Project condition, verified items, top defects, security concerns, blockers |
| Baseline | `audit_report/B_baseline.md` | Commit/branch/tree, tech stack, entrypoints, routes, DB/migrations, runtimes, executed commands |
| Feature matrix | `audit_report/C_feature_matrix.md` | All 30+ interfaces with route/template/role/coverage and verification status |
| Browser report | `audit_report/D_browser_report.md` | BLOCKED — no browser/Playwright; evidence of blocker |
| Backend & DB report | `audit_report/E_backend_db.md` | Source-inspected API/auth/business logic/schema/security; runtime BLOCKED |
| Performance report | `audit_report/F_performance.md` | BLOCKED — nothing measured; provisional targets noted |
| Coverage & blind spots | `audit_report/I_coverage_blindspots.md` | Tested vs not-tested, why, and what's needed |
| Repair roadmap | `audit_report/J_roadmap.md` | Mandatory vs optional repairs, dependencies, regression checks |

## External logs captured

| Log | Location | Content |
|-----|----------|---------|
| Unit test run output | `/tmp/unit_results.log` | `pytest tests/unit --continue-on-collection-errors` full output (100 failed + 61 errored; exit 1). Most failures are environmental (no PostgreSQL, missing tesseract/fixtures). |
| venv | `/tmp/sylth-venv` | Isolated Python 3.11 environment used for dependency install and test execution (outside the repo; not persisted in the repo) |

## Command transcripts (summary)

All executed commands and their exit statuses are recorded in `B_baseline.md` section B.10. The two state-changing commands (test runs) temporarily modified `map_data/registry.db` and created `.cache/`, `data/settings.json`, `.flask_secret_key`; all were reverted/removed and the working tree is clean (`git status` empty).

## Screenshots / browser artifacts

**None captured.** Real interactive browser testing is blocked (F-04). The pre-existing `deliverables/interface_screenshots.zip`, `deliverables/screenshots/`, and `deliverables/screenshot_manifest.csv` are tied to snapshot `aa2b865a` (2026-10-16), not the current HEAD `2670f3b`, and were not used as evidence of the current state.

## Database before/after observations

**None.** No database was available, so no database state was read or written during this audit. No migration was applied to any database.

## Artifact hashes

No binary artifacts were produced that require hashing. The repository HEAD is `2670f3b` ("updates for main all"); working tree clean at baseline.

## Reproduction package

To reproduce the confirmed findings:
1. Clone https://github.com/RussellTCrivello/SYLTHARAE-Pro.git and checkout `2670f3b` (or branch `arena/a5145290-syltharae-pro`).
2. Confirm no PostgreSQL is running on localhost:5432.
3. `python -c "from apps.web.app import app"` → `psycopg2.OperationalError: connection to server at "localhost" port 5432 failed` (reproduces F-01).
4. `git log --oneline -1` → `2670f3b`; `ls docs/` → "No such file"; `ls database/migrations/` → m0001–m0003 only (reproduces F-02).
5. `pytest tests/unit` → integration suite skipped / unit failures environmental (reproduces F-03).
6. `which chromium google-chrome firefox` and `python -m playwright --version` → not found (reproduces F-04).
