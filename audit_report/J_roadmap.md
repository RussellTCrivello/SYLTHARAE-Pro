# J. Repair Roadmap

## Mandatory defect repair (blockers to any verification)

| Order | Finding | Repair | Dependency | Regression check |
|-------|---------|--------|------------|------------------|
| 1 | F-01 App cannot start without PostgreSQL | Document PostgreSQL as a hard prerequisite; evaluate lazy/failing-soft DB initialization so the app constructs and shows a setup/maintenance page when the DB is unavailable. Guard `DatabaseHub` and `bootstrap_admin` so a missing DB does not abort import. | None (design decision) | After PG provisioned: `python -c "from apps.web.app import app"` succeeds; `verify_readiness.py` passes DB checks. |
| 2 | F-02 Changelog/docs drift (m0038/m0039, DATABASE_SCHEMA.md, missing docs/) | Either apply migrations m0038/m0039 and regenerate `docs/reference/DATABASE_SCHEMA.md` (`tools/docs/generate_schema.py --check`), or mark CHANGELOG entries as planned/not-in-this-checkout. Remove or regenerate stale `docs/` references. | m0038/m0039 SQL must be written and tested against a disposable DB | `git diff` of CHANGELOG vs migrations reconciled; `generate_schema.py --check` clean; interface_inventory regenerated for HEAD 2670f3b. |
| 3 | F-03 Test suite cannot run | Provision PostgreSQL for the test environment so integration/security tests execute; do not treat skips as green. | PostgreSQL installable | Full `pytest tests/` passes (or failures re-classified as real defects vs environmental). |
| 4 | F-04 Browser testing blocked | Provide a browser + Playwright (or pre-baked browser image) to execute mandatory Phase 3 workflows. | Browser downloadable or pre-installed | Phase 3 routes/workflows exercised; console/network evidence captured. |
| 5 | F-05 Deliverables snapshot mismatch | Regenerate deliverables against HEAD 2670f3b or label them as snapshot aa2b865a. | Docs/registry available | feature_matrix.csv and interface_inventory match core/interfaces/registry.py for this checkout. |

## Optional hardening (not defect repair)

| Finding | Suggested effort | Priority |
|---------|------------------|----------|
| F-06 Bare `except: pass` blocks (setup.py:562, words.py, archives_api.py:1772, file_operations.py:85, api.py:224, common.py:153) | Review each; log + surface errors instead of swallowing. `health.py` was inspected and is NOT a silent swallow (correctly reports DB errors). | P2 — do after DB available so routes can be exercised. |
| F-07 Optional deps degrade capabilities (openpyxl → Excel export disabled; OCR/readers) | Install optional extras per requirements.txt or add user-visible degradation messages. | P3 |
| — | Real security testing (BolA, injection, authz) against running app | P1 once DB+browser available |
| — | Performance baselines | P2 once DB+browser available |

## Data-migration / compatibility risks

- Applying m0038/m0039 (if they are to be introduced) adds CHECK constraints and drops redundant indexes. `m0038` refuses to drop anything whose survivor is missing or shape-drifted; `m0039` counts violating rows and refuses with values listed. Test both on a **disposable** database before any production application. No data is touched by m0038; m0039 is additive validation.
- The app supports exactly one process per database; do not deploy multi-process Gunicorn/uWSGI against the same DB.

## Regression verification requirements

After any repair:
1. `python -c "from apps.web.app import app"` imports without PostgreSQL error (if lazy-init is added) — or starts cleanly with PostgreSQL.
2. `verify_readiness.py --json` returns all critical checks passed.
3. `pytest tests/` passes; integration/security tests run against disposable PostgreSQL.
4. Phase 3 browser CRUD/search workflows pass; console clean of errors; network payloads match DB state (cross-layer truth).
5. `git status` clean (no unintended working-tree changes).

## Explicit separation

Everything above under "Mandatory defect repair" is required to make the system verifiable and to reconcile documentation with code. "Optional hardening" is modernization/improvement and must not be conflated with defect repair. No changes were committed to this branch as part of this audit.
