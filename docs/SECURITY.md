# Security

> **STATUS: NEEDS-REVIEW.** Written during a repair pass to answer questions
> raised by the test suite, not reviewed by the project owner. Treat every
> claim as a proposal: the statements about enforced controls come from
> reading the code, and the test named beside each one is the evidence, but
> the wording, the scope and the omissions have not been agreed. Do not cite
> this document as the project's security policy until it is reviewed.

This document describes the controls the application actually implements. Every
statement below is enforced by code in this repository and covered by the test
suite named next to it; where a control is only partially applied it says so.

## Authentication and sessions

* **Default deny.** A request is rejected unless its endpoint appears in an
  explicit allow-list (`core/security/flask_ext.py`, `PUBLIC_ENDPOINTS`). The
  allow-list is exactly 20 endpoints: `static`, `favicon`, `health.health`,
  `get_csrf_token`, `translations.get_i18n_catalog`, six `auth.*` endpoints
  (`login`, `login_page`, `logout`, `me`, `first_admin_page`,
  `first_admin_create`) and nine `setup.*` endpoints (`setup_page`,
  `system_check`, `test_database`, `run_installation`, `check_setup_status`,
  `set_setup_language`, `dependency_report`, `dependency_install`,
  `dependency_job`). Every other endpoint in those blueprints - and every page
  or API outside them - requires a session; the two "first admin" and the
  setup endpoints are additionally gated server-side on the system state.
* **Roles.** Reads require any authenticated user, writes require `analyst` or
  above, and the admin blueprints require `admin`.
* **Sessions** are rows in the `sessions` table, so they can be revoked
  server-side. Cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` when the
  deployment is served over TLS.
* **Forced password change.** A user created with a temporary password can
  reach only the password-change endpoints
  (`PASSWORD_CHANGE_ALLOWED_ENDPOINTS`) until the password is changed.
* **Changing a password requires the current password** (`POST
  /auth/change-password`, limited to 10 requests per minute). A wrong current
  password counts towards the sign-in lockout, and locking the account ends
  every session. The attempt is audited as `password.change`,
  `password.change_failed` or `password.change_locked`
  (`tests/security/test_change_password.py`).
* **CSRF** protection is applied to state-changing requests
  (`tests/unit/test_session_cookie_config.py`,
  `tests/security/test_change_password.py`).

## Content-Security-Policy

Every response carries this exact policy (asserted by
`tests/unit/test_csp_no_inline_script.py`):

`default-src 'self'; script-src 'self'; worker-src 'self' blob:; child-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'`

`script-src 'self'` means **no inline script and no `eval`**. Interactive
markup therefore wires controls with `data-on-<event>` attributes, which the
declarative dispatcher in `static/js/modules/core/declarative-events.js`
executes without `eval` or `Function`. See `docs/DEVELOPMENT.md` for the
convention.

`style-src` still allows `'unsafe-inline'`, because pages set per-element
styles (table widths, progress bars) at runtime. That is a style-injection
surface, not a script-execution one.

## Request hardening

* `X-Frame-Options: DENY` and `frame-ancestors 'none'` (clickjacking).
* `X-Content-Type-Options: nosniff`.
* HSTS when the deployment is served over TLS.
* Rate limiting on authentication endpoints (`Flask-Limiter`).
* Uploads are validated for extension, size and archive safety
  (zip-slip and path traversal are rejected in `core/archive_safety.py`).

## Start-up safety

The application refuses to start when a production deployment is configured
with debug mode, a default secret key, or an HTTP-only configuration. The
readiness report (`python3 verify_readiness.py`) checks the same conditions.

## Reporting a problem

Report suspected vulnerabilities privately to the maintainer rather than in a
public issue.
