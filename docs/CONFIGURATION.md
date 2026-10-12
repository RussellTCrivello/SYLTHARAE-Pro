# Configuration

How SYLTHARAE is configured, which names the runtime actually reads, and how to
check a configuration before trusting it. `.env.example` is the annotated
template; copy it to `.env` and edit that copy. Never commit a `.env` with real
credentials.

## Precedence

Environment variables always win, and the order is the one stated at the top of
`.env.example`:

1. **OS environment variables** — highest. Also the way a container or service
   manager configures a deployment.
2. **`.env` file** — loaded at start-up with `override=False`, so it never
   overwrites a variable that already exists in the environment.
3. **`settings.json`** — the runtime settings store (`data/settings.json`),
   written by the settings UI and the installer.
4. **`config.example.json`** — project defaults.
5. **Dataclass defaults** — lowest.

After editing `.env`, restart the server: the file is read at start-up.

A few settings are deliberately *not* environment-controlled because they are
tunable at runtime and the settings store is their home: the connection pool
size, the worker count, chunk size and per-file timeout live under
**Settings → Database** and **Settings → Processing**. The environment values
for those exist only as an installer-written fallback (see "Reserved names").

## Application and server

| Variable | Default | Read by | Notes |
| --- | --- | --- | --- |
| `FLASK_SECRET_KEY` | generated | `apps/web/app.py`, `settings/` | Signs sessions and CSRF tokens. Auto-generated into `.flask_secret_key` when empty; set a strong random value (≥ 64 hex chars) for production. |
| `FLASK_ENV` | `production` | `apps/web/app.py` | `development` \| `staging` \| `production`. Controls debug mode, HSTS, cookie security and error verbosity. Production is the default, so an unconfigured install is not silently insecure. |
| `FLASK_DEBUG` | `false` | `run_web.py`, `apps/web/app.py` | `true`/`1`/`yes` enable the reloader and the interactive debugger. The server **refuses to start** when debug is on while `FLASK_ENV=production`. |
| `FLASK_HOST` | `0.0.0.0` | `run_web.py`, `apps/web/app.py` | Bind address. Behind a reverse proxy on the same host, set `127.0.0.1` so only the proxy can reach the app. |
| `FLASK_PORT` | `5000` | `run_web.py`, `apps/web/app.py` | Bind port. |
| `TRUSTED_PROXY_COUNT` | `0` | `apps/web/deployment.py` | Number of reverse proxies in front of the app. `0` means the app is exposed directly and ignores `X-Forwarded-*` headers. A non-numeric value is a start-up error, and the app refuses to guess: it would otherwise trust no proxy and every client would share the proxy's address for rate limits, lockouts and the audit log. Never set it on a directly exposed server — clients could spoof their IP. |
| `WSGI_SERVER` | `flask` | `apps/web/deployment.py`, `run_web.py` | `flask` (built-in server) or `waitress` (production). The setup wizard writes `waitress` here when the package is installed. Serving production traffic with the built-in server is a warning, not a refusal, because `flask` is the default. |
| `WAITRESS_THREADS` | `32` | `apps/web/deployment.py` | Waitress worker threads. Each open Jobs page holds one for its live stream. A non-numeric value warns and falls back to the default. |
| `SOURCE_CODE_URL` | empty (link target `#`) | `apps/web/app.py` | Where users of this server can get its source. SYLTHARAE is AGPL-3.0-or-later, so **a modified copy run for others must point this at the modified source** ([LICENSING.md](LICENSING.md)). Only `http(s)://` values are accepted; anything else is refused and the default is used. Shown on every page with the running version. |

## Database (PostgreSQL)

| Variable | Default | Notes |
| --- | --- | --- |
| `DB_HOST` | `localhost` | Hostname, or a socket directory on POSIX deployments. |
| `DB_PORT` | `5432` | |
| `DB_NAME` | `analysis` | The application database. `database.bootstrap` creates it when missing. |
| `DB_USER` | `postgres` | |
| `DB_PASSWORD` | empty | |
| `DB_POOL_MIN_CONNECTIONS` | `1` (code); `2` in `.env.example` | Read by `DatabaseConfig.from_env`. Taken from **Settings → Database** at runtime when the settings store is available; the environment value applies when it is not. |
| `DB_POOL_MAX_CONNECTIONS` | `20` (code); `25` in `.env.example` | As above. |

`database.database.config.DatabaseConfig.from_env` prefers the documented
`DB_POOL_*` names and still honours the legacy `DB_MIN_CONNECTIONS` /
`DB_MAX_CONNECTIONS`, which win when both are set. `database.get_db_config()`
re-reads the environment, so a value changed after the settings cache was
populated (by the installer, for example) still takes effect —
`tests/unit/test_env_config_names.py` pins both behaviours.

## Administrator (first run)

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ADMIN_USERNAME` | `admin` | Used only while no account exists, to create the initial administrator. |
| `APP_ADMIN_PASSWORD` | empty | When empty, a random password is generated and written to the runtime directory. Remove it from `.env` after the first start if you set it by hand. |
| `PASSWORD_MIN_LENGTH` | `12` | Enforced for every account, admin included. |

## Security

| Variable | Default | Read by |
| --- | --- | --- |
| `SECURITY_MAX_FAILED_LOGINS` | `5` | `core/security/service.py` |
| `SECURITY_LOCKOUT_MINUTES` | `15` | `core/security/service.py` |
| `SECURITY_SESSION_HOURS` | `12` | `core/security/service.py` (absolute session lifetime) |
| `SECURITY_SESSION_IDLE_HOURS` | `6` | `core/security/service.py` (sliding idle window) |
| `RATE_LIMIT_PER_MINUTE` | `60` | `core/security/rate_limit.py` |
| `RATE_LIMIT_PER_HOUR` | `600` | `core/security/rate_limit.py` |

## Ingestion

| Variable | Default | Notes |
| --- | --- | --- |
| `INGESTION_ROOTS` | empty | Semicolon-separated absolute directories the server may read from disk (Windows: `C:\data;D:\inbox`, POSIX: `/data/evidence;/srv/inbox`). Empty disables server-path ingestion; drag-and-drop upload still works. `core/path_safety.py` confines every server-path read to these roots. |

## Data directory and logging

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_DATA_DIR` | platform default | Root for logs, uploads, cache, checkpoints and settings — `~/.local/share/file-analysis` on Linux, `~/AppData/Local/file-analysis` on Windows. See `core/app_paths.py`. |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL`. Read by `apps/web/app.py` at import; an unrecognised value falls back to `INFO` instead of failing the start-up. |

## Reserved names

These names appear in `.env.example` (and are written by the installer), but the
running server does not read them. They are reserved for the installer's record
and for compatibility; changing them here has no effect — use the settings UI:

| Name | Why it is reserved |
| --- | --- |
| `DB_POOL_TIMEOUT` | Pool sizing and timeouts come from **Settings → Database**. |
| `DB_QUERY_TIMEOUT` | As above. |
| `MAX_WORKERS` | Worker count comes from **Settings → Processing**. |
| `FILE_CHUNK_SIZE` | As above. |
| `FILE_PROCESSING_TIMEOUT` | As above. |
| `ACTION_LOGGING_ENABLED` | The security audit trail (`audit_log`) is always on. |
| `PERFORMANCE_MONITORING` | Performance monitoring is always on. |

`tests/unit/test_env_config_names.py` enforces the distinction: every variable
`.env.example` presents as live must appear in the code that reads environment
variables, and this document must name every reserved one — so a name cannot be
documented as live without something honouring it, and a reserved name cannot be
quietly dropped from the documentation.

## Validating a configuration

Configuration problems surface in three places, deliberately in this order:

1. **Start-up checks** (`apps/web/deployment.py`) — run before the server binds.
   An `error` finding refuses the start (debug in production, a
   `TRUSTED_PROXY_COUNT` that is not a whole number, a missing `FLASK_PORT`);
   a `warning` starts with the reason stated (development server in production,
   a non-numeric `WAITRESS_THREADS`). The operator-facing list is in
   [OPERATIONS.md](OPERATIONS.md).
2. **The readiness report** — `python3 verify_readiness.py` reports
   configuration and connectivity checks in named sections, so a deployment can
   be inspected before it is put in front of users.
3. **The tests** — `tests/unit/test_env_config_names.py`,
   `tests/unit/test_deploy_configs.py` and `tests/integration/test_deploy_nginx.py`
   pin the documented names, the deployment files and the proxy assumptions.

## Safe local setup

```
cp .env.example .env          # then edit: DB_* and FLASK_SECRET_KEY at minimum
createdb analysis             # or let database.bootstrap create it
python3 -m database.bootstrap # creates and migrates the schema (or use the wizard)
python3 run_web.py            # serves on FLASK_HOST:FLASK_PORT
```

A fresh install with no `.system_initialized` marker sends every request to the
setup wizard (`/setup`), which walks the system check, the database connection
test and the initial administrator. That redirect is expected first-run
behaviour, not a broken deployment.

For a production-shaped deployment on one host, use the artefacts in `deploy/`
(nginx site + systemd unit) and set `FLASK_HOST=127.0.0.1`,
`TRUSTED_PROXY_COUNT=1`, `WSGI_SERVER=waitress` and `SOURCE_CODE_URL`.
