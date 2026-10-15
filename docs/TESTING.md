# Testing

What the test suite covers, how to run it, and what the live smoke tests add
that a test process cannot. Development conventions are in
[DEVELOPMENT.md](DEVELOPMENT.md); the deployment shape the smoke tests target is
in [OPERATIONS.md](OPERATIONS.md). The environment the suite expects — RAM,
disk, tool versions and the one-command setup — is in
[TEST_ENVIRONMENT.md](TEST_ENVIRONMENT.md), and the currently measured baseline
counts are in [STABILITY_BASELINE.md](STABILITY_BASELINE.md).

## The layered suite

| Directory | Needs a database? | What it covers |
| --- | --- | --- |
| `tests/unit` | no (a few use the disposable server) | Core logic, registries, services, security helpers, generated documents and the interface/action contracts. Fast; a failure here is a defect in logic or a document that drifted. |
| `tests/integration` | yes — a disposable PostgreSQL | Real schema from the real migrations: routes end to end, ingestion, search, detection, reporting, notifications, browser-less page rendering. |
| `tests/security` | partly | Authorization, disclosure, session handling, CSRF, proxy deployment assumptions. |
| `tests/js` | node | The declarative-event runtime and the action-toolbar smoke test (`node tests/js/…mjs`). Skips when node is absent. |

```
.venv/bin/python -m pytest tests/unit -q
.venv/bin/python -m pytest tests/integration -q
.venv/bin/python -m pytest tests/security -q
```

Integration tests create a **test-named** database on a disposable server and
run `database.bootstrap` into it; they never touch the configured application
database. When no server is reachable they skip, once, with the reason and the
candidate hosts they tried — set `REQUIRE_POSTGRES=1` to turn that skip into a
failure in CI.

Batch the runs: the full suite in one process holds many database fixtures open
at once and can exhaust a small machine's disk or memory. Run a directory, or a
focused list of files.

## Why these tests exist in these shapes

The suite encodes failures that actually happened, and the docstring of each
file usually names the one it pins. A few examples worth knowing before you
"simplify" one:

* **The catalogs are the product's text, and gaps are defects.**
  `tests/integration/test_translation_coverage.py` fails on any empty or fuzzy
  entry in the offered catalogs, on an interface string the catalog does not
  carry, and on a `.mo` that lags its `.po`;
  `tests/unit/test_catalog_extraction.py` pins that a translation call cannot
  offer its own lookup key as a message (NARR-02), and
  `tests/unit/test_catalog_maintenance.py` pins that the maintenance tool never
  fills a missing translation with English. The workflow is in
  [DEVELOPMENT.md](DEVELOPMENT.md).
* **Documents are generated and compared.** `docs/reference/DATABASE_SCHEMA.md`,
  `docs/INTERFACE_REGISTRY.md`, `docs/EXPERIENCE_CONTRACT.md`,
  `docs/ACTION_SURFACE_AUDIT.md`, `docs/SCREEN_INSPECTOR_EVIDENCE.md` and
  `docs/COMPONENT_LIBRARY.md` are produced by generators and compared with the
  committed file, so a count in prose cannot drift from the product. Regenerate
  with the documented command; never hand-edit the generated block.
* **The CSP is asserted, not assumed.** `tests/unit/test_csp_no_inline_script.py`
  reads the served header, scans templates and scripts for inline handlers, and
  renders every page to prove none contains inline script — and that every
  handler name a page binds is reachable on `window`.
* **Cross-document consistency.** `tests/unit/test_doc_links.py` resolves every
  relative link and anchor in the documentation; `tests/unit/test_no_machine_paths.py`
  fails if a shipped file leaks a local path. Both read `git ls-files`, so a new
  artifact must be staged to be covered.
* **Schema/migration agreement.** `tests/integration/test_bootstrap_migrations.py`
  asserts the objects a migrated database must have;
  `tests/integration/test_redundant_enforcement_removal.py` proves the duplicate
  enforcement removed by m0038 is gone while the canonical constraint still
  rejects duplicates; `tests/integration/test_vocabulary_constraints.py` proves
  the vocabulary CHECKs match the code's vocabulary exactly.
* **Test isolation is part of the contract.** A module that simulates an older
  schema must restore the current one before it finishes
  (`restore_canonical_hash_contexts` in
  `tests/unit/test_relationship_deduplication.py`), because the session shares
  one database and a later test would otherwise see a schema no migration
  produces.

## Live smoke test

The unit and integration suites drive the application in-process. The smoke
tools drive a **running, installed** server over HTTP, which is the only way to
prove the proxy, TLS and cookie configuration together.

```
# full functional pass against a real server (setup wizard, ingestion, search,
# reports, exports, restart survival)
python tools/smoke/live_smoke.py install     # first run: setup wizard
python tools/smoke/live_smoke.py run1        # full pass
# restart the server, then
python tools/smoke/live_smoke.py run2        # repeat after restart

# export-surface check
python tools/smoke/export_surfaces_smoke.py

# browser smoke: proves the page's own scripts ran (a button that does nothing
# is invisible to an HTTP-only test)
npm install --prefix /tmp/smoke-tools puppeteer-core
NODE_PATH=/tmp/smoke-tools/node_modules CHROME_PATH=/usr/bin/chromium \
    SMOKE_ADMIN_PASSWORD=... node tools/smoke/browser_smoke.mjs

# navigation smoke: sidebar order/hiding round trip through the settings API
NODE_PATH=/tmp/smoke-tools/node_modules CHROME_PATH=/usr/bin/chromium \
    SMOKE_ADMIN_PASSWORD=... node tools/smoke/navigation_smoke.mjs
```

Environment for `live_smoke.py`: `SMOKE_BASE_URL`, `SMOKE_HTTP_URL`,
`SMOKE_PUBLIC_HOST`, `SMOKE_EVIDENCE` (must be inside the workspace),
`SMOKE_OCR_FONT`, `SMOKE_ADMIN_USER`, `SMOKE_ADMIN_PASSWORD`, and
`SMOKE_DB_HOST` / `SMOKE_DB_PORT` / `SMOKE_DB_USER` / `SMOKE_DB_PASSWORD` /
`SMOKE_DB` for the server it points at. For the browser tests:
`SMOKE_BASE_URL` (use a `localhost` host so the browser accepts the cookie),
`SMOKE_ADMIN_USER`, `SMOKE_ADMIN_PASSWORD`, `CHROME_PATH`,
`SMOKE_MAX_PAGES`.

The smoke tests write their evidence (screenshots, generated documents, logs)
into `SMOKE_EVIDENCE`; nothing else in the repository consumes it, so keep it
out of git.

## Reading a result honestly

* Report the command and the counts, and separate **pre-existing** failures from
  regressions. A test that fails identically on the base revision is not caused
  by your change.
* A skip is not a pass. If a test skips because a service is unavailable
  (PostgreSQL, node, nginx, `pyzipper`), say so with the reason rather than
  counting it green.
* Never weaken an assertion, delete a test or broaden a skip to obtain a green
  run. If the expectation is wrong, fix the expectation *and* the reason it was
  wrong; if the code is wrong, fix the code.
* Check `-rf` output for `FAILED` lines rather than reading progress
  characters — a truncated progress line has misled reviewers before.
