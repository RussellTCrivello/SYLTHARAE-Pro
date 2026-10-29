# Configuration

> **STATUS: NEEDS-REVIEW.** Written during a repair pass to answer questions
> raised by the test suite, not reviewed by the project owner. The variable
> names and defaults were read out of the code, but whether every documented
> option should be supported, renamed or removed is a decision nobody has
> taken yet.

Settings are layered: environment variables override `data/settings.json`, which
overrides built-in defaults. `.env.example` lists the names a deployment may set;
this page explains what each one does and which ones are reserved.

## Web server

| Variable | Default | Effect |
| --- | --- | --- |
| `FLASK_SECRET_KEY` | generated at first start | Session and CSRF signing key. Must be set in production; a generated key is written to the runtime directory for development. |
| `FLASK_ENV` | `production` | `development` relaxes the start-up checks. |
| `FLASK_DEBUG` | `false` | Debug mode. Refused in production by the start-up validation. |
| `FLASK_HOST` / `FLASK_PORT` | `0.0.0.0` / `5000` | Bind address. |
| `WSGI_SERVER` | `flask` | `waitress` runs the production WSGI server. |
| `WAITRESS_THREADS` | `32` | Worker threads when `WSGI_SERVER=waitress`. |
| `TRUSTED_PROXY_COUNT` | `0` | Number of reverse proxies whose `X-Forwarded-*` headers are trusted. Leave at `0` without a proxy. |
| `SOURCE_CODE_URL` | — | Link shown in the interface for the AGPL source offer. |
| `LOG_LEVEL` | `INFO` | Root logging level. |

## Database

| Variable | Default | Effect |
| --- | --- | --- |
| `DB_HOST` / `DB_PORT` | `localhost` / `5432` | PostgreSQL address. A Unix socket directory is accepted as host. |
| `DB_NAME` | `analysis` | Database name. |
| `DB_USER` / `DB_PASSWORD` | `postgres` / empty | Credentials. |
| `DB_POOL_MIN_CONNECTIONS` / `DB_POOL_MAX_CONNECTIONS` | **not read** on the normal path | Pool bounds come from `DatabaseSettings` (`pool_min_conn = 2`, `pool_max_conn = 25`, `settings/settings_models.py:283-284`), then the resource coordinator lowers the maximum (`core/resource_coordinator.py:269-279`). `DB_POOL_*` — and the legacy `DB_MIN_CONNECTIONS` / `DB_MAX_CONNECTIONS`, which win over them when both are set — are consulted **only** if importing the settings system raises; that fallback (`database/database/config.py:88-92`) defaults to `1` / `20`. Setting either name in a working installation therefore does nothing. |

## Security and rate limits

| Variable | Default | Effect |
| --- | --- | --- |
| `APP_ADMIN_USERNAME` / `APP_ADMIN_PASSWORD` | `admin` / generated | First administrator created on an empty database. The generated password is written to `initial_admin_password.txt` in the runtime directory and must be changed at first sign-in. |
| `PASSWORD_MIN_LENGTH` | `12` | Minimum password length. |
| `SECURITY_MAX_FAILED_LOGINS` | `5` | Failed attempts before lockout. |
| `SECURITY_LOCKOUT_MINUTES` | `15` | Lockout duration. |
| `SECURITY_SESSION_HOURS` | `12` | Absolute session lifetime. |
| `SECURITY_SESSION_IDLE_HOURS` | `6` | Idle timeout. |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_PER_HOUR` | `60` / `600` | Per-client limits. |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | Limit on the password-change endpoint. |
| `RATELIMIT_STORAGE_URI` | in-process | Storage backend for the limiter; point at Redis for multi-process deployments. |

## Ingestion and storage

| Variable | Default | Effect |
| --- | --- | --- |
| `APP_DATA_DIR` | repository `data/` | Runtime data root (settings, backups, gazetteer seed). |
| `INGESTION_ROOTS` | unset | Allowed source roots; an ingestion path outside them is refused. |
| `OPERATIONS_MAX_UPLOAD_MB` | shipped default | Largest accepted upload. |
| `OPERATIONS_MAX_CHUNKED_UPLOAD_MB` | shipped default | Largest accepted chunked upload. |
| `OPERATIONS_UPLOAD_CHUNK_MB` | shipped default | Chunk size. |
| `OPERATIONS_MAX_STAGED_PATH_CHARS` | shipped default | Longest staged path. |
| `TESSERACT_CMD` | auto-detected | Path to the Tesseract binary when it is not on `PATH`. |
| `MAP_DATA_DIR` | repository `map_data/` | Where the map viewer reads and writes its registry. The shipped tree contains `catalog.json` (read-only reference data) and `registry.db` (written by the application). Pointing this at a scratch directory keeps a run from writing the tracked file: the test suite sets it to a temporary tree and copies the shipped `catalog.json` there, so a full run leaves `git status` clean. |

## Compute

| Variable | Effect |
| --- | --- |
| `COMPUTE_MODE` | Device policy for heavy work (`auto`, `cpu`, …). |
| `COMPUTE_GATEWAY` | Enables the compute gateway. |
| `COMPUTE_ISOLATION` | Isolation level for worker execution. |
| `COMPUTE_GPU_FALLBACK` | Whether an accelerator may fall back to CPU. |

## Reserved names

These are accepted by `.env.example` and the installer but no code reads them
yet. Setting them has no effect; they are kept so an existing deployment's file
does not break:

`MAX_WORKERS`, `FILE_CHUNK_SIZE`, `FILE_PROCESSING_TIMEOUT`, `DB_POOL_TIMEOUT`,
`DB_QUERY_TIMEOUT`, `ACTION_LOGGING_ENABLED`, `PERFORMANCE_MONITORING`.

`tests/unit/test_env_config_names.py` fails if a name presented as live in
`.env.example` is not read by the code, or if a reserved name is dropped from
this page.
