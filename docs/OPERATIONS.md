# Operations

Running SYLTHARAE: the start-up checks, the supported deployment shape, and what
to do when something goes wrong. Configuration names and defaults are in
[CONFIGURATION.md](CONFIGURATION.md); the security policy is in
[SECURITY.md](SECURITY.md); backups and schema handling are in
[DATABASE.md](DATABASE.md).

## Start-up checks

Before the server binds, `apps/web/deployment.py::evaluate` inspects the
environment and reports findings. An **error** refuses the start (`run_web.py`
exits with a non-zero status, which the systemd unit is configured to detect); a
**warning** starts, with the reason stated.

| Finding | Level | Trigger | What to do |
| --- | --- | --- | --- |
| `debug_in_production` | error | `FLASK_DEBUG` is on while `FLASK_ENV=production`. | Set `FLASK_DEBUG=false`, or `FLASK_ENV=development` on a development machine. Debug mode executes code sent by the browser. |
| `invalid_trusted_proxy_count` | error | `TRUSTED_PROXY_COUNT` is not a whole number ≥ 0. | `0` when clients connect directly, `1` behind one reverse proxy. A guess here silently breaks client-address accounting. |
| `invalid_port` | error | `FLASK_PORT` is not 1–65535. | Set a real port number. |
| `invalid_waitress_threads` | warning | `WAITRESS_THREADS` is not a number. | Set a whole number, 4 or more; the default (32) is used meanwhile. |
| `development_server` | warning | Production served by Flask's built-in server. | `pip install waitress` and set `WSGI_SERVER=waitress`. |
| `waitress_missing` | warning | `WSGI_SERVER=waitress` but the package is absent. | Install it, or the built-in server is used instead. |
| `proxy_bypassable` | warning | `TRUSTED_PROXY_COUNT` > 0 but the app listens on a non-loopback address. | Set `FLASK_HOST=127.0.0.1`, or firewall the app port — otherwise a client that reaches the app directly can forge `X-Forwarded-For` and evade rate limits, lockouts and audit attribution. |
| `no_tls_proxy` | warning | Production, `TRUSTED_PROXY_COUNT=0`, non-loopback bind. | Prefer TLS termination (`deploy/nginx/syltharae.conf`). With Secure cookies HTTP sign-in is rejected; turning Secure off allows it but sends passwords and session cookies unencrypted. |
| `short_secret_key` | warning | `FLASK_SECRET_KEY` shorter than the minimum. | `python -c "import secrets; print(secrets.token_hex(32))"`, then restart. |

Run the same evaluation without starting the server with
`python3 verify_readiness.py`, which reports the configuration checks together
with database, schema and endpoint checks in named sections.

## Supported deployment shape

`deploy/` carries the deployment artefacts that the tests pin
(`tests/unit/test_deploy_configs.py`, `tests/integration/test_deploy_nginx.py`,
`tests/security/test_proxy_deployment.py`):

* `deploy/nginx/syltharae.conf` — TLS termination (TLS 1.2/1.3), HTTP → HTTPS
  redirect, `/static/` served directly, request limits, server tokens off, and
  proxy headers set to the values the application expects. **`Host` and
  `X-Forwarded-Host` must be forwarded**: without them the app sees
  `127.0.0.1:5000`, the browser's `Referer` no longer matches the public name,
  and the HTTPS CSRF check rejects every sign-in with 400.
* `deploy/systemd/syltharae.service` — runs `run_web.py` with a restart policy
  and the environment file; a start-up refusal is visible as a failed unit.

Matching settings:

```
FLASK_ENV=production
FLASK_HOST=127.0.0.1        # only the proxy can reach the app
FLASK_PORT=5000
TRUSTED_PROXY_COUNT=1       # exactly one proxy in front
WSGI_SERVER=waitress
SOURCE_CODE_URL=https://…   # where users can get this deployment's source
```

The setup wizard writes the production-shaped values when you let it, including
`WSGI_SERVER=waitress` when the package is installed.

## Direct HTTP on a trusted private network

The app can serve direct HTTP for a trusted LAN or isolated test network. This keeps CSRF protection enabled and uses a non-Secure, SameSite=Lax session cookie, which browsers send for same-origin HTTP navigation and fetches. Set:

```
FLASK_ENV=development
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
TRUSTED_PROXY_COUNT=0
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
```

Then connect from another device using the server's LAN address, for example `http://192.168.1.20:5000` (replace with the actual address). Use that exact host consistently; do not open the app on one hostname and submit requests to a different IP/hostname. Keep the firewall limited to the intended private network. **Plain HTTP is not confidential:** usernames, passwords, session cookies and application data can be observed or modified by anyone able to intercept that network traffic. Do not use this mode on public Wi-Fi, an untrusted network or the public internet. For deployment beyond a trusted LAN, terminate TLS and use the production proxy configuration above.

If viewing through a third-party embedded preview, browsers may block its cookies even with a valid CSRF token. Open the preview as a top-level page instead; this is a browser third-party-cookie restriction, not a reason to disable CSRF. Direct same-origin HTTP use on a LAN does not have that iframe restriction.

## First run

With no `.system_initialized` marker, every request is redirected to `/setup`
and the wizard walks the system check, the database connection test and the
initial administrator. That redirect is expected; a 302 to `/setup` is therefore
not a readiness failure (`tests/integration/test_readiness_login_check.py`).
Completing the wizard runs the migrations, creates the administrator and writes
the marker.

If the marker exists but the critical tables do not, the application still sends
you to `/setup`: the marker is the fast path, the table check is authoritative.

## Routine operations

| Task | How |
| --- | --- |
| Check readiness | `python3 verify_readiness.py` |
| Schema state | `python3 -c "from database.bootstrap import schema_status; print(schema_status())"` |
| Apply pending migrations | `python3 -m database.bootstrap` (or let start-up do it) |
| Database audit (read-only) | `python3 tools/db/integrity_audit.py` — every check is a `SELECT` |
| Dependency licences | `python3 tools/licenses/check_licenses.py --quiet` |
| Logs | The configured `LOG_LEVEL`, plus the runtime data directory (`APP_DATA_DIR`). Every error response carries a correlation id that matches the server-side log entry. |

## Recovering an administrator password

`scripts/reset_admin_password.py` is the supported recovery path, and it refuses
rather than guesses:

```
python3 scripts/reset_admin_password.py --list                    # who exists
python3 scripts/reset_admin_password.py --username admin          # prompts twice
python3 scripts/reset_admin_password.py --username admin --promote
python3 scripts/reset_admin_password.py --username admin --activate
```

* The target must be an **administrator** (`--promote` recovers a demoted
  account) and **active** (`--activate` recovers a deactivated one); otherwise
  the script exits `3` and changes nothing.
* With **no accounts at all** it exits `2`: start the server once and the
  first-run bootstrap creates the initial administrator (see *First run*).
* The change is written to the audit log as `user.password_recovery`, and the
  account is asked for a new password at the next sign-in.
* Exit codes: `0` success, `2` account not found, `3` refused, `4` database not
  reachable, `1` unexpected error.

## Backups and restore

`pg_dump` of the application database is the backup; the runtime data directory
(uploads, logs, settings) is the second half. `contents_raw` holds the ingested
bytes, so a database-only backup restores metadata without content — back up
both. Restoring a database backup is an operator action, not an application
one; the import/export surface is for moving *records* between deployments and
is administrator-only.

## Diagnosing common failures

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Every sign-in answers 400 | The reverse proxy is not forwarding `Host` / `X-Forwarded-Host`, so the CSRF origin check fails. | `test_deploy_configs.py` asserts the required headers; compare your site config with `deploy/nginx/syltharae.conf`. |
| Everyone shares one rate-limit bucket, or a client's address is wrong in the audit log | `TRUSTED_PROXY_COUNT` does not match the topology. | The `proxy_bypassable` / `no_tls_proxy` findings above. |
| The server refuses to start after a change | A start-up **error** finding. | The message names the variable and the fix; `journalctl -u syltharae`. |
| A page loads but buttons do nothing | A script failed to load, or a handler is not reachable on `window`. | Browser console; `tests/unit/test_csp_no_inline_script.py` covers the handler contract. |
| A job sits in `CANCELLING` | The worker has not acknowledged cancellation yet; cancellation is cooperative. | Job detail → events; a worker that never finishes leaves this state visible rather than reporting a false `CANCELLED`. |
| Integration tests skip | No PostgreSQL reachable. | `DB_HOST`/`DB_PORT`, or run `pytest tests/integration -q` where a server exists. `REQUIRE_POSTGRES=1` makes the skip a failure. |

## Upgrades

Upgrading is: deploy the new code, restart, and let the migration runner apply
any new migrations on start-up. Migrations are additive by convention and
refuse loudly when a precondition is unmet, so a failed upgrade leaves the schema
as it was and the ledger honest. Take a backup before an upgrade that carries a
migration — the repository's own rule is that a destructive change is never part
of an already-shipped migration; a correction is a new one.
