# B. Repository and Runtime Baseline

## B.1 Repository identity and commit

| Field | Value |
|-------|-------|
| Repository | /home/user/SYLTHARAE-Pro (clone of https://github.com/RussellTCrivello/SYLTHARAE-Pro.git) |
| Branch | `arena/a5145290-syltharae-pro` (tracking `remotes/origin/main`) |
| HEAD commit | `2670f3b` "updates for main all" |
| Commit count on branch | 1 (single squashed commit; no incremental history) |
| Remote | `origin` https://github.com/RussellTCrivello/SYLTHARAE-Pro.git (fetch + push) |
| Working tree (baseline) | Clean (`git status` = nothing to commit) |

Note: during this session the working tree was momentarily dirtied by test runs (`map_data/registry.db` modified, `.cache/` created). These were my own test artifacts, restored/removed so the tree is clean again. No user work was discarded.

## B.2 Languages and frameworks

| Layer | Technology | Evidence |
|-------|-----------|----------|
| Backend/web | Python 3.10+, Flask 3.x, Flask-WTF, Flask-Limiter, Flask-Compress, Flask-Babel, psycopg2-binary | pyproject.toml, requirements.txt, apps/web/app.py |
| Database | PostgreSQL (psycopg2 driver; raw SQL, no ORM) | database/database/database.py, requirements.txt |
| Frontend | Jinja2 templates + vanilla JS (ES modules), Bootstrap, Select2, maplibre-gl, translations | templates/, static/js/, static/vendor/map/ |
| i18n | Flask-Babel + .po catalogs in translations/ (en, ar, he, fa offered; Croatian catalog exists but not offered) | apps/web/app.py, translations/ |
| Production WSGI (opt-in) | Waitress (`WSGI_SERVER=waitress`) | apps/web/serve.py, pyproject optional `server` extra |
| Scheduler | In-process background scheduler (SYLTHARAE_SCHEDULER=1), single process per database | run_web.py, services/scheduling/scheduler.py |
| Packaging | setuptools; console scripts `file-analysis-web`, `file-analysis-cli` | pyproject.toml |

## B.3 Entrypoints and service boundaries

| Entrypoint | Purpose |
|------------|---------|
| `run_web.py` | Canonical web entry: validates deployment settings (`deployment.enforce`), initializes settings/system, starts job recovery + scheduler, serves Flask (built-in or Waitress) |
| `apps/web/app.py` | Flask app factory: auth, CSRF, rate limiting, compression, security/CSP headers, error handlers, blueprint registration, setup gate |
| `apps/web/serve.py` | Waitress vs built-in server selection |
| `apps/cli/main.py` | CLI (`file-analysis-cli`) |
| `run_cli.py` / `run_import.py` | CLI/import helpers |
| `verify_readiness.py` | Production readiness behavioral check (requires PostgreSQL) |
| `install.py` / `setup.bat` / `start.bat` / `start-web.bat` | Installer / startup scripts (Windows-oriented) |
| `services/scheduling/scheduler.py` | In-process job scheduler (report runs, rule/scenario evaluation) |
| `services/jobs/manager.py` | JobManager + crash recovery (stale jobs → FAILED) |

## B.4 API routes and middleware

Route modules live in `Api/routes/` (~36 modules): api.py, auth.py, search.py, sources.py, sides.py, keywords.py, words.py, categories.py, dashboard.py, analysis.py, archives.py, archives_api.py, operations_api.py, operations_pages.py, file_analysis.py, file_operations.py, preview.py, import_export.py, schedules.py, retention.py, scenarios.py, signals.py, places.py, analytics.py, performance.py, notifications.py, notifications_page.py, audit.py, lexis_cosmos.py, map_api.py, cursor_api.py, concurrency.py, health.py, setup.py, common.py, preferences.py, experience_api.py, interfaces_api.py, exports.py, translations.py, error_dashboard.py, sides.py.

Middleware/security (from `apps/web/app.py` + `core/security/flask_ext.py`):
- Default-deny auth; public endpoints explicitly allow-listed (`PUBLIC_ENDPOINTS`).
- Role policy: safe methods any authenticated user; mutating methods analyst/admin; admin blueprints admin-only; `must_change_password` gate.
- CSRF (Flask-WTF) with `/api/csrf-token`.
- Rate limiting (Flask-Limiter, default 60/min 600/hour).
- Compression (Flask-Compress).
- Security headers: CSP (no inline scripts, `frame-ancestors 'none'`), X-Content-Type-Options, X-Frame-Options DENY, X-XSS-Protection, Referrer-Policy, Permissions-Policy, COOP, HSTS only on TLS.
- ProxyFix only when `TRUSTED_PROXY_COUNT` set.
- `TEMPLATES_AUTO_RELOAD`; no-cache on API/HTML responses.

## B.5 Database engines, schema, migrations

- Engine: PostgreSQL via psycopg2 (`ThreadedConnectionPool`). No ORM.
- Migrations: `database/migrations/` — only `m0001_baseline.py`, `m0002_category_parent_id.py`, `m0003_sources_attachments.py` (3 files).
- `m0001` creates: words, punctuation, categorys, words_categorys, sides, sources, hashs, hash_contexts, paths, contents, titles_content, keywords, words_hashs, keywords_hashs, alerts, users, sessions, audit_log, jobs, job_events, plus many analyst/scenario/geo/signal tables (41 tables total).
- `verify_readiness.py` REQUIRED_TABLES matches the migration output (users, sessions, audit_log, jobs, job_events all present).
- **Discrepancy:** CHANGELOG.md v2.2.0 describes migrations `m0038` and `m0039` and a regenerated `docs/reference/DATABASE_SCHEMA.md`; neither the migrations nor `docs/` exist in this checkout (F-02).

## B.6 Background workers, jobs, scheduling

- `services/jobs/manager.py`: JobManager, persistent job state/events/progress, crash recovery (`recover_stale_jobs`).
- `services/scheduling/scheduler.py`: in-process scheduler; fires report/rule/scenario jobs; off unless `SYLTHARAE_SCHEDULER=1`.
- `core/checkpoint_manager.py`: checkpoints for resumable processing.
- Jobs run as threads inside the single web process; exactly one process per database supported (multi-process Gunicorn/uWSGI not supported).

## B.7 External services and integration boundaries

- PostgreSQL (required, hard dependency at import).
- Optional OCR: Tesseract (`pytesseract`, needs `tesseract.exe` + eng/heb/ara traineddata) or RapidOCR fallback (`rapidocr-onnxruntime`).
- Archives: `rarfile` (needs UnRAR/bsdtar), `py7zr`.
- Media/FFmpeg (optional, removed moviepy).
- PST/libpff-python (optional, not hard-required).
- Rollbar/Sentry (optional error reporting).
- External HTTP: none required for core operation.

## B.8 Build, test, lint, startup commands

| Command | Purpose |
|---------|---------|
| `python run_web.py` | Start web server (FLASK_HOST/FLASK_PORT, default 0.0.0.0:5000) |
| `python verify_readiness.py [--json]` | Behavioral production-readiness check (needs PostgreSQL) |
| `pytest tests/` | Test suite (integration tests need disposable PostgreSQL via pgserver) |
| `ruff` (select E,F,W,B; ignore E501) | Lint |
| `bandit` | Security lint |
| `pybabel extract/update/compile` | Translation catalog management |

## B.9 Available runtimes and tooling (this environment)

| Tool | Status |
|------|--------|
| Python 3.11.2 | Present |
| pip (PyPI access: pypi.org, files.pythonhosted.org) | Present; core + optional reader deps installable |
| Node.js v22.22.3, npm, npx, yarn | Present |
| Flask / psycopg2 / pytest | Not installed initially; installed into `/tmp/sylth-venv` for testing |
| PostgreSQL server / psql / pg_ctl / initdb | **Absent** (no apt permission; not installable) |
| Browser (Chrome/Chromium/Firefox) | **Absent** |
| Playwright | **Absent** |
| XVFB | **Absent** |
| Docker | **Absent** |
| apt-get | Present but permission-denied on package lists |

## B.10 Executed commands and results

| # | Command | Exit | Outcome |
|---|---------|------|---------|
| 1 | `python -c "import flask"` | fail | ModuleNotFoundError (not installed) |
| 2 | `python -m venv /tmp/sylth-venv` + pip install flask, psycopg2-binary, pytest, ... | 0 | Core deps installed in isolated venv |
| 3 | `python -c "from apps.web.app import app"` | fail | psycopg2.OperationalError: connection to localhost:5432 refused (DatabaseHub pool + bootstrap_admin at import) |
| 4 | `pytest tests/unit test_version_consistency test_session_cookie_config test_passwords_and_errors` | 0 | 26 passed (DB-free unit tests) |
| 5 | `pytest tests/unit --continue-on-collection-errors` | 1 | 100 failed + 61 errored, overwhelmingly environmental (no PostgreSQL; missing tesseract/fixtures). See /tmp/unit_results.log |
| 6 | Browser/Playwright checks | fail | No browser binaries; no Playwright; apt unusable |
| 7 | `git checkout -- map_data/registry.db; rm -rf .cache; rm -f data/settings.json .flask_secret_key` | 0 | Working tree restored to clean |

## B.11 Pre-existing generated/ignored items (not part of baseline)

`deliverables/` contains a pre-built briefing package (PPTX, feature_matrix.csv, interface_inventory.csv/md, interface_screenshots.zip, screenshots/, presenter_guide.md, research_limits.md) tied to snapshot `aa2b865a...` (2026-10-16) — NOT the current HEAD `2670f3b`. `test-doc/` contains synthetic sample files by type. These are not executed or modified by this audit.
