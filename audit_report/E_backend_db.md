# E. Backend and Database Report (PHASES 2 + 4 — runtime portion BLOCKED)

## Status

The backend and database could **not be executed** because the Flask application cannot be imported without a running PostgreSQL server (F-01). All findings in this section are from **direct source-code inspection**, not from exercised API calls or live database state. No API request was made, no response status was observed, and no database row was read or written during this audit (the readiness check and all integration tests skip/fail for lack of PostgreSQL).

## E.1 API contract findings (source inspection)

Route surface: ~36 route modules under `Api/routes/`, plus blueprints (`Api/blueprints/paths.py`, `analytics.py`, `files.py`, `content_analysis.py`) and blueprint registrations (`operations_bp`, `archives_api_bp`, `file_analysis_bp`, `cursor_api_bp`, `concurrency_bp`, `error_dashboard_bp`).

Auth model (source-verified):
- `init_auth(app)` attaches two before-request hooks: `_load_current_user` (session token → DB-validated user; revocable sessions) and `_enforce_role_policy` (SEC-02).
- `PUBLIC_ENDPOINTS` allow-list: static, auth login/logout/me/first-admin, CSRF token, favicon, health, setup pages, translation catalog.
- Safe methods (GET/HEAD/OPTIONS): any authenticated user.
- Mutating methods (POST/PUT/PATCH/DELETE): analyst or admin.
- Admin-only blueprints: settings, settings_api, setup, concurrency, error_dashboard, translations, import_export (writes); settings + settings_api + concurrency + error_dashboard also admin for reads.
- `/api/settings/theme` and `/api/settings/system/language` are explicitly open to any authenticated user (documented rationale: theme is rendered into base.html for everyone; language switcher equivalent exists via `/set_language`).
- `must_change_password` accounts can reach only the change-password flow, `/`, `/auth/me`, `/auth/logout`, and CSRF/health (403 otherwise).
- Error handling: generic client-safe messages with server-side correlation IDs (`core/errors.py`); CSRF and 429 handlers return JSON for API callers.

Not verified at runtime: actual status codes, request/response payload shapes, pagination semantics, rate-limit headers, validation error bodies, duplicate-submission handling, authorization enforcement on live endpoints.

## E.2 Business logic findings (source inspection)

- **Content identity & dedup:** `database/services/dedup_service.py` — hash (sha256) + source/side context; duplicate content resolves to a single identity with multiple paths/contexts; `delete_path` + re-ingest supported (DB-05).
- **Jobs:** `services/jobs/manager.py` — job state machine (queued/running/completed/failed/cancelled), event throttling, pause/resume, crash recovery (`recover_stale_jobs` → FAILED). `job_state.ALL_STATES` and `EVENT_TYPES`.
- **Search:** `core/search/`, `Api/services/search_service.py` — tokenization, inverted word association, cursor pagination, explicit count mode.
- **Criteria/SQL:** `core/criteria/` — access compiler, SQL generation with identifier allowlisting (`core/sql_safety.py`).
- **Compute policy:** `core/compute/policy.py` + `gateway.py` — device selection (CPU unless a usable accelerator is probed), back-pressure (`BackpressureError` on queue saturation), admission control.
- **Serialization:** `core/serialization.py` — restricted unpickler refuses GLOBAL opcodes (SEC: unsafe deserialization blocked).
- **Archive safety:** `core/archive_safety.py` — zip-slip (path traversal) rejected (SEC-05).
- **Path safety:** `core/path_safety.py` — fails closed when `INGESTION_ROOTS` unset (SEC-06).

Not verified at runtime: calculations, filtering correctness, state transitions, totals/counters, race conditions, N+1 queries, ordering stability.

## E.3 Database integrity findings (source inspection)

- Schema in `m0001_baseline.py` (41 tables) + `m0002` (category parent_id) + `m0003` (sources attachments).
- `verify_readiness.py` REQUIRED_INDEXES pins `hashs_hash_key`, `uq_hash_contexts_identity`, and key indexes; `REQUIRED_TABLES` includes users, sessions, audit_log, jobs, job_events — all present in m0001.
- CHANGELOG claims `m0038` removed nine redundant structures and `m0039` added CHECK constraints on `alerts.type`, `alerts.priority`, `jobs.status`, `job_events.event_type` — neither migration exists in this checkout (F-02), so those CHECK constraints and deduplicated indexes **cannot be confirmed present**.

Not verified at runtime: orphaned records, foreign-key effectiveness, transaction rollback behavior, concurrent writes, schema drift against a live DB.

## E.4 Background processing and recovery (source inspection)

- JobManager crash recovery runs at startup (`_recover_jobs`, guarded — never blocks startup).
- Scheduler (`services/scheduling/scheduler.py`) starts only when `enabled_by_config()`; guarded so it cannot block the web app.
- Checkpoint manager (`core/checkpoint_manager.py`) for resumable ingestion.
- Progress ledger (`pipeline/progress_ledger.py`).

Not verified at runtime: job state transitions, checkpoint durability, resume after interruption, retry/backoff, idempotency, recovery after controlled restart.

## E.5 Security findings (source inspection + non-exploitive)

| Area | Observation | Runtime verified? |
|------|-------------|-------------------|
| Authentication | DB-backed sessions, revocable, token in session; AnonymousUser fallback | No |
| Authorization | Default-deny, role-based, admin-only endpoints | No |
| BolA | Not specifically inspectable without running instances/users | No |
| CSRF | Flask-WRF + `/api/csrf-token` | No |
| SQL injection | Identifier allowlisting in `core/sql_safety.py` | No |
| XSS | CSP `script-src 'self'` no inline; templates use gettext/autoescape | No |
| Path traversal | `core/archive_safety.py` zip-slip rejected; `core/path_safety.py` fails closed | No (code read) |
| Unsafe deserialization | Restricted unpickler in `core/serialization.py` | No |
| Secrets | None in tracked sources; `.env`/`.flask_secret_key` gitignored; SECRET_KEY auto-generated | No |
| Security headers | CSP, HSTS(conditional), X-Frame-Options DENY, etc. | No |
| Rate limiting | Flask-Limiter initialized; login/search/import-export stricter | No |

**Conclusion:** The security design appears deliberate and well-documented (SEC-01…SEC-10 annotations in code), but **zero security behavior was verified against a running system**. All security claims remain source-level observations until PostgreSQL and a browser are available.
