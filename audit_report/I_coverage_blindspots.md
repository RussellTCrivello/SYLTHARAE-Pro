# I. Verification Coverage and Blind Spots (PHASE 8 + Phase 10)

## What was tested / verified

| Area | What was done | Status |
|------|---------------|--------|
| Repository baseline | Commit, branch, remote, working tree, git status | VERIFIED |
| Dependency install | Core + optional reader deps installed into isolated venv from PyPI | VERIFIED |
| App import | Attempted `from apps.web.app import app` — FAILS without PostgreSQL | VERIFIED (failure reproduced) |
| Readiness check | `verify_readiness.py` — database checks cannot run | BLOCKED (no PostgreSQL) |
| Unit tests (DB-free subset) | `test_version_consistency`, `test_session_cookie_config`, `test_passwords_and_errors` passed (26 tests) | VERIFIED |
| Unit tests (full suite) | 100 failed + 61 errored, overwhelmingly environmental | BLOCKED / ENVIRONMENTAL |
| Auth/authorization design | Source-read `core/security/flask_ext.py`, `service.py` | Source-verified only |
| Interface registry | Source-read `core/interfaces/registry.py`, `inventory.py`, `model.py`, `validation.py` | Source-verified only |
| Health endpoint | Source-read `Api/routes/health.py` | Source-verified only |
| Baseline migration | Source-read `m0001` — all REQUIRED_TABLES present | Source-verified only |
| Security headers | Source-read `apps/web/app.py` after_request handlers | Source-verified only |
| Browser / interactive frontend | None attempted — no browser, no Playwright | BLOCKED |
| API contract | No request made; no response observed | BLOCKED |
| Database state | No row read or written | BLOCKED |
| Background jobs | No job created/executed/recovered | BLOCKED |
| Security testing | No live probes against a running app | BLOCKED |
| Performance | Nothing measured | BLOCKED |

## What was NOT tested and why

| Area | Why not tested | Blocker |
|------|----------------|---------|
| Full backend runtime (startup, routes, auth, validation) | App cannot import without PostgreSQL | F-01 (no PostgreSQL installable) |
| `/health` and all API endpoints | No running server | F-01 |
| All integration tests | conftest `pg_settings` skips when no PostgreSQL reachable | F-01 |
| All security tests | Need a running app + authenticated clients | F-01 |
| Real browser testing (Phase 3) | No browser binary, no Playwright, no XVFB, browsers not downloadable under network restriction | F-04 |
| Responsive/accessibility testing | No browser | F-04 |
| Client-side performance | No browser | F-04 |
| Background job execution/recovery | No running app | F-01 |
| Database integrity against live DB | No database | F-01 |
| Cross-layer truth experiment (Phase 4) | No UI/backend/DB execution | F-01 + F-04 |
| Adversarial scenarios (Phase 5) | No running system | F-01 + F-04 |

## Which conclusions remain uncertain

- Whether the default-deny auth, role enforcement, and BolA protections actually hold on a running instance.
- Whether all 30 declared interfaces' routes exist and function (registry vs live URL map could not be compared).
- Whether business-logic calculations (search ranking, dedup, job state transitions, analytics) are correct.
- Whether migrations m0001–m0003 produce a schema consistent with the app's assumptions at runtime.
- Whether security headers/rate limiting/CSRF are enforced at runtime.

## What would be needed to complete verification

1. A PostgreSQL server (16+) reachable from this environment (or permission to install one via apt).
2. A migrated, disposable test database.
3. A browser binary (Chromium/Firefox) or Playwright, plus XVFB if headless.
4. Network access sufficient to download browsers (or a pre-baked browser image).
5. Optional OCR/binaries (tesseract + eng/heb/ara traineddata; UnRAR; FFmpeg) for full reader coverage.
