# Security

How SYLTHARAE protects the data it holds and the accounts that reach it: what is
enforced, where it is implemented, and which test holds it in place. Everything
below describes this repository; the policy quoted here is read from the running
application by `tests/unit/test_csp_no_inline_script.py::test_the_documented_policy_is_the_served_policy`.

## Content Security Policy and browser protections

Every response carries the following policy verbatim
(`apps/web/app.py::add_security_headers`):

`default-src 'self'; script-src 'self'; worker-src 'self' blob:; child-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'`

Reading it as the browser does:

* `script-src 'self'` — no inline script, no `eval`. There is no `'unsafe-inline'`
  for script and no string evaluation anywhere in the application's JavaScript.
  Interactive behaviour is declared with `data-on-<event>` attributes (for
  example `data-on-click`) that
  `static/js/modules/core/declarative-events.js` interprets by looking the
  handler name up on `window` — a restricted interpreter, with no `eval` and no
  `new Function`. Page data reaches the script in
  `<script type="application/json">` blocks, which are not executed.
* `default-src 'self'` — anything not named below may only load from this
  origin. `object-src 'none'` forbids plugins and `base-uri 'self'` stops an
  injected `<base>` from repointing relative URLs.
* `frame-ancestors 'none'` — the application cannot be framed, which is what
  makes clickjacking impractical. `X-Frame-Options: DENY` carries the same
  decision for older clients.
* `worker-src 'self' blob:` and `child-src 'self' blob:` — workers built from
  blobs are allowed (the export and preview code uses them); nothing is loaded
  from a third-party origin.
* `style-src 'self' 'unsafe-inline'` — inline **style** is allowed. This is a
  deliberate, narrow allowance: stylesheets cannot execute script, and the
  templates set computed values (bar widths, colours) inline. Script keeps its
  strict policy.
* `img-src 'self' data: blob:` — logos and generated previews may be data or
  blob URLs.
* `connect-src 'self'` — a page can only call this origin, so an injected
  script cannot exfiltrate data to another host.

Alongside the policy, every response sets:

| Header | Value | Purpose |
| --- | --- | --- |
| `X-Content-Type-Options` | `nosniff` | Stops a browser from re-interpreting a response's type. |
| `X-Frame-Options` | `DENY` | Framing refused for clients that ignore `frame-ancestors`. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Full URLs are not leaked to other origins. |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Browser features the application never needs are denied outright. |
| `Cross-Origin-Opener-Policy` | `same-origin` | Cross-origin documents cannot keep a handle on this window. |
| `Content-Security-Policy` | as quoted above | |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Sent **only** in production and only over TLS (`request.is_secure`), so it cannot pin a plain-HTTP development host into HTTPS. |

Each header is applied with `setdefault`, so a view can deliberately relax one
where it must — the original-file viewer frames content this application serves,
and it does so by overriding `frame-ancestors` for that response only.

The policy is verified three ways: the served header has no inline or eval
allowance for script; no template, script or served page contains an inline
handler attribute or an executable inline `<script>`; and every handler a page
binds resolves to a function reachable on `window`. See
[DEVELOPMENT.md](DEVELOPMENT.md) for the authoring rules that keep this true.

## Authentication, sessions and authorization

* **Passwords** are hashed with Werkzeug's `scrypt` (`core/security/passwords.py`),
  a memory-hard KDF; the method is embedded in the stored hash, and
  `needs_rehash` upgrades a hash when the parameters change. A password's
  minimum length is `PASSWORD_MIN_LENGTH` (default 12).
* **Changing a password** requires the current password. A wrong current
  password counts towards the sign-in lockout, and if that locks the account
  **every session, including the one making the request, is ended**. On success
  the account's other sessions are revoked and the current one continues. Every
  outcome is written to the audit trail: `password.change`,
  `password.change_failed`, `password.change_locked`.
* **Sessions** are stored server-side (`sessions`) with the token kept hashed
  (`_hash_token`), so a stolen database does not hand over live sessions.
  The cookie is `HttpOnly`, `SameSite=Lax`, and `Secure` in production; the
  absolute lifetime and the sliding idle timeout are
  `SECURITY_SESSION_HOURS` (12) and `SECURITY_SESSION_IDLE_HOURS` (6).
* **Lockouts**: `SECURITY_MAX_FAILED_LOGINS` (5) failures lock the account for
  `SECURITY_LOCKOUT_MINUTES` (15) — `core/security/service.py`.
* **Authorization** is decided where the operation runs, per route, through the
  decorators in `core/security/flask_ext.py`. Blueprints listed in
  `AUTH_ADMIN_BLUEPRINTS` are administrator-only for **every** mutating method,
  which is how the import/export surface (backup restore, export) is gated:
  both are administrator capabilities, and the blueprint-level rule means a new
  route added there cannot be forgotten.
* **Rate limiting** (`core/security/rate_limit.py`, flask-limiter) applies per
  client against `RATE_LIMIT_PER_MINUTE` (60) and `RATE_LIMIT_PER_HOUR` (600),
  with tighter per-route limits on the login and password surfaces. Because
  limits are per client address, `TRUSTED_PROXY_COUNT` must match the real
  proxy topology — otherwise every client shares one bucket, or a client can
  forge its own ([CONFIGURATION.md](CONFIGURATION.md)).

## CSRF and request safety

Session-changing requests carry a CSRF token (`flask-wtf`), the token is
rendered as a meta tag and sent by the front-end, and the setup endpoints are
**not** exempt from the check — a first-run wizard is still a state-changing
surface. Input is validated at the route boundary, and every database query is
parameterised: a query that interpolates a value into SQL is treated as a
defect rather than a style question (`core/sql_safety.py`). File paths that
arrive from a client or a server-side ingestion root are confined to the
configured roots by `core/path_safety.py`, and archive extraction is bounded by
`core/archive_safety.py` (entry count, expanded size, path traversal).

## Error disclosure

Raw exception text never reaches a client. `core/errors.py` classifies an
exception, logs the full detail server-side with a correlation id and returns a
client-safe message plus that id; `client_safe_message` and `sanitize_message`
scrub connection strings and credentials even from operator-visible messages.
The global handlers in `apps/web/app.py` cover the framework-level cases, and
`tests/unit/test_experience_contract.py` reads every route module and asserts
that no handler returns exception text in a response body. The one place that
had drifted — a settings handler returning `str(e)` — is held fixed by
`tests/security/test_settings_error_hygiene.py`.

## Data protection in the database

* **Audit trail.** `audit_log` records authentication, authorization and
  administrative events with the acting user, the resource, the client address
  and a detail payload. The username is stored as a snapshot and the row is
  intentionally not foreign-keyed to `users`: the trail must survive the
  deletion of the account it describes.
* **Immutable history.** Reporting records are immutable by construction:
  `report_runs` is write-once once terminal, datasets and analyses in a run are
  write-once, and `report_artifacts` carries a checksum and byte size that a
  trigger verifies against the stored bytes. A correction is a new run, never an
  edit. The analyst categorization log is likewise append-only. These are
  database triggers, not conventions — see
  [database/RELATIONSHIP_INTEGRITY.md](database/RELATIONSHIP_INTEGRITY.md).
* **Least data.** Only what a feature needs is stored: `contents_raw` for
  display and export, `contents.content_data` for search, and derived signals
  keyed by content hash. Backups are the operator's `pg_dump` of the application
  database ([DATABASE.md](DATABASE.md)).

## Bandit triage of the intelligence layer

Static analysis (`bandit`) findings in the parsing and intelligence layers were
triaged rather than silenced: each one is either fixed with the fix pinned by a
test, or recorded here with the reason it is not exploitable. The fixes —
validators anchored with `$` that accepted a trailing newline, a SQL column
guarded by `assert` (removed by `python -O`) replaced with an explicit check,
and `eval`-free handlers — are pinned by
`tests/unit/test_bandit_triage_fixes.py`, so a regression fails the suite
instead of reappearing silently.

## Reporting a vulnerability

This is a self-hosted application: report a security issue to whoever operates
your deployment first, and include the version shown in the application footer
(`version.py`) plus the reproduction. Operators should review
[OPERATIONS.md](OPERATIONS.md) for the deployment checklist and
[CONFIGURATION.md](CONFIGURATION.md) for the security-relevant settings before
exposing an installation to a network.
