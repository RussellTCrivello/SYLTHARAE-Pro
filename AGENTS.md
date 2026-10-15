# AGENTS.md — how to work in this repository

This file is for AI coding agents and for the people who review their work. It
condenses the rules in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md),
[docs/TESTING.md](docs/TESTING.md) and [docs/SECURITY.md](docs/SECURITY.md),
adds the working protocol for an agent session, and records the environment
pitfalls that cost earlier sessions time. Those three documents remain
authoritative: if this file disagrees with them, they win, and this file is
corrected in the same change.

## 1. The project in one paragraph

SYLTHARAE is a Flask + PostgreSQL information-intelligence platform with
server-rendered Jinja templates and plain JavaScript ES modules (no bundler, no
`package.json`). What exists is declared once, in registries that tests check
against the running application: interfaces in `core/interfaces/registry.py`,
screen contracts in `core/experience/declarations.py`, actions in
`core/experience/action_registry.py`. Counts in the documentation are generated
from those registries and compared by tests, so a number typed by hand fails the
suite. Authorisation is default-deny and decided at the route
(`core/security/flask_ext.py`); the registries decide only what is *shown*.

## 2. Session bootstrap

Every session starts from a fresh `origin/main`. These commands are proven in an
Arena sandbox (Debian, 2 vCPU, about 2 GB RAM, no swap, `/tmp` a RAM-backed tmpfs
of about 1 GB).

```bash
# 2.1  Keep heavy files off /tmp, which is small and backed by RAM.
export WORK="$HOME/.cache/syl-work" TMPDIR="$HOME/.cache/tmp"
mkdir -p "$WORK" "$TMPDIR"

# 2.2  Fresh checkout and a task branch from origin/main.
git clone https://github.com/RussellTCrivello/SYLTHARAE-Pro.git "$WORK/repo" 2>/dev/null \
  || git -C "$WORK/repo" fetch origin
cd "$WORK/repo" && git checkout -B "arena/<TASK-ID>-<slug>" origin/main

# 2.3  Python 3.11. The project supports 3.10-3.12, and pgserver has no wheel for 3.13.
#      Debian's pip refuses a system-wide install (PEP 668) without
#      --break-system-packages, and where the sandbox blocks uv's Python
#      download the venv falls back to the system interpreter.
pip install -q --break-system-packages uv
uv python install 3.11 || true
uv venv -q -p 3.11 .venv
. .venv/bin/activate
uv pip install -q -r requirements.txt pytest pytest-cov ruff bandit pgserver pyzipper

# 2.4  Integration tests get a disposable PostgreSQL from pgserver. Make its
#      absence a failure rather than a skip.
export REQUIRE_POSTGRES=1
```

* **Counting results.** `pyproject.toml` already adds `-q`. A second `-q` hides
  the summary line, so do not add one. Use `-rfE` (failures and errors) and,
  for counts you will report, `--junitxml=$TMPDIR/<name>.xml` followed by
  `python tools/ci/junit_annotations.py $TMPDIR/<name>.xml`.
* **Batch the runs.** A single process running all of `tests/unit` was
  OOM-killed (exit 137) about halfway through on a 2 GB sandbox. Run
  directories in shards of about 50 files. Between shards, delete
  `$TMPDIR/pgdata_*`: each pytest session leaves one pgserver data directory of
  about 70 MB.
* **Node harnesses.** Run `node tests/js/<name>.mjs` (Node 20 is present), or
  the pytest wrapper that drives it.

### 2.5 Browser tooling, when the task needs a real browser

```bash
sudo apt-get update -q && sudo apt-get install -y -q libnss3 libnspr4  # Chromium's shared libraries
npm install --prefix "$HOME/.cache/browser-tools" --no-audit --no-fund playwright-core @sparticuz/chromium
export PLAYWRIGHT_CORE="$HOME/.cache/browser-tools/node_modules/playwright-core/index.mjs"
export CHROMIUM_MODULE="$HOME/.cache/browser-tools/node_modules/@sparticuz/chromium/build/index.js"
```

The bundled Chromium runs in single-process mode, and closing a context takes
the browser down, so use **one context per run**. The binary is extracted to
`/tmp/chromium`, which uses RAM: delete it when browser work is finished. The
harnesses in `tests/browser/` read `BASE_URL`, `APP_USER`, `APP_PASSWORD`,
`PLAYWRIGHT_CORE`, `CHROMIUM_MODULE` and `CHROME_PATH`. Without them they exit 0
and print `SKIP`, and a skip is not a pass.

## 3. Running the application for browser work

Use a database the tests do not own. Either use a system PostgreSQL
(`sudo apt-get install -y postgresql && sudo service postgresql start`, then
create a role with a password), or keep a pgserver instance alive in its own
process. Start the app on `127.0.0.1:5055`, with `APP_DATA_DIR` outside the
repository and `DB_*` set (see `.env.example`). Then complete the first-run
wizard non-interactively with `python tools/smoke/live_smoke.py install`
(`SMOKE_BASE_URL`, `SMOKE_ADMIN_PASSWORD`, `SMOKE_DB_*`). For browser cookies,
use a `localhost` or `127.0.0.1` host. If `tools/dev/` provides a launcher or
a seeding tool (prompts P0-05 and P0-06 create them), use it rather than
improvising.

## 4. Non-negotiable rules

1. **Evidence over assertion.** Back every claim in a report with a command you
   ran and its counts. A skip is not a pass. "Should work" is not evidence.
2. **Never weaken a test to get green.** Do not weaken an assertion, delete a
   test, broaden a skip, add `xfail`, or loosen a CHECK. Classify each failure
   as a code defect, a fixture defect or a wrong expectation, and fix that one.
3. **Registries are the source of truth.** Add or alter interfaces, screens and
   actions in the registries, never in prose. Never hand-edit a generated block:
   run its generator (section 5), then that document's test.
4. **Content-Security-Policy is `script-src 'self'`.** No inline `<script>`, no
   `on*=` attributes, no `javascript:` URLs, no `eval`. Use `data-on-<event>`
   (the handler must be reachable on `window`), and pass page data in
   `<script type="application/json">` blocks.
   `tests/unit/test_csp_no_inline_script.py` enforces this.
5. **Text is product.** Every visible string goes through `_()` or the JS packs.
   Layouts must work right-to-left (Arabic, Hebrew, Persian) and use logical CSS
   properties.
6. **Translations are never invented.** Do not copy English into a msgstr. A
   fuzzy entry is not a translation. A missing translation stays missing and is
   reported for a human; `scripts/catalog_maintenance.py` reports what is
   missing. `tests/integration/test_translation_coverage.py` is deliberately
   left failing until people supply the text.
7. **Security is default-deny.** Never loosen a route's authorisation without
   a written PM decision. Every write carries CSRF. Every query is
   parameterised (`core/sql_safety.py`, `core/path_safety.py`). Raise typed
   errors (`core/errors.py`) and never return exception text to a client.
8. **Long work belongs to the job system** (`services/jobs/`). Emit events
   through the manager, and add new event types to `job_state.EVENT_TYPES` in
   the same change.
9. **Schema changes are new numbered migrations**
   (`database/migrations/m00NN_name.py`). Make them idempotent and
   transactional, and have them refuse loudly when a precondition fails. Never
   edit an applied migration.
10. **Front-end change hygiene.** Bump `<meta name="asset-version">` in
    `templates/base.html` when shipped JavaScript or CSS changes. Reference
    static files with `url_for('static', filename=...)`. When a page that was a
    classic script becomes a module, verify it in a real browser.
11. **Scope discipline.** One task, one branch, one pull request. Do not
    refactor in passing. Never mix a repair with a refactor in one commit.
12. **Pre-existing failures are proven, not assumed.** A failure counts as
    pre-existing only if it reproduces identically on `origin/main`. Record it.
    Do not hide it and do not fix it silently.
13. **The repository wins.** Prompts and documents can be stale. Verify every
    stated fact at `HEAD`. When the repository disagrees with your
    instructions, follow the repository and report the discrepancy.

## 5. Sources of truth and their generators

| What | Declared in | Generated document | Command |
| --- | --- | --- | --- |
| Interfaces | `core/interfaces/registry.py` | `docs/INTERFACE_REGISTRY.md` | `python3 -m core.interfaces.docgen docs/INTERFACE_REGISTRY.md` |
| Registry against the live app | registry + URL map | `docs/REGISTRY_EVIDENCE.md` | `python3 -m core.interfaces.evidence --write docs/REGISTRY_EVIDENCE.md` |
| Screen contracts | `core/experience/declarations.py` | `docs/EXPERIENCE_CONTRACT.md` | `python3 -m core.experience.docgen docs/EXPERIENCE_CONTRACT.md` |
| Actions | `core/experience/action_registry.py` | `docs/ACTION_SURFACE_AUDIT.md` | `python3 -m core.experience.action_audit docs/ACTION_SURFACE_AUDIT.md` |
| Screen Inspector | registries + bindings | `docs/SCREEN_INSPECTOR_EVIDENCE.md` | `python3 -m core.experience.audit docs/SCREEN_INSPECTOR_EVIDENCE.md` |
| Components | templates | `docs/COMPONENT_LIBRARY.md` | `python3 -m core.frontend.component_audit` |
| Schema | migrations | `docs/reference/DATABASE_SCHEMA.md` | `python3 tools/docs/generate_schema.py` (`--check`) |
| Routes and Python reference | URL map and code | `docs/endpoint_inventory.json`, `docs/reference/*` | `python3 tools/docs/generate_reference.py` |

Hand-maintained registers that must stay truthful: `docs/DEFECT_REGISTER.md`
(exactly one status per item), `docs/INTERFACE_COVERAGE.md`,
`docs/STABILITY_BASELINE.md` and `CHANGELOG.md` (under "unreleased").

## 6. Verification ladder

Climb it in order and report each rung you reached:

1. The focused test you wrote first. Where it reproduces a defect, show it
   failing before the fix.
2. The neighbouring tests of the files you touched.
3. The suite batches the change can affect: `tests/unit`, `tests/security`, and
   `tests/integration` with `REQUIRE_POSTGRES=1`, all in shards.
4. The Node harnesses, if JavaScript changed. The browser harnesses, if
   behaviour in a page changed.
5. Regenerate the affected documents, then run their tests.
6. `ruff check <changed files>`. Run `python tools/security/bandit_count_gate.py`
   if Python changed, and `python tools/licenses/check_licenses.py --quiet` if a
   dependency changed.
7. Read the diff: nothing unrelated, no machine paths
   (`tests/unit/test_no_machine_paths.py`), and no secrets.

## 7. Git, commits and pull requests

* Branch from `origin/main` as `arena/<TASK-ID>-<slug>`. Never push to `main`,
  and never force-push a branch someone else uses.
* **Commit messages follow the house style.** The subject is an imperative
  sentence that names the behaviour (72 characters at most). The body follows
  this pattern:
  - what was wrong, the root cause, and how it was proven;
  - a bulleted list of the changes;
  - `Tests:` with each test path and its count;
  - `Translations:` stating what changed and what still needs a human.
  Earlier commits co-authored by the agent carry a `Co-authored-by:` trailer;
  keep doing that.
* Open a pull request titled `[<TASK-ID>] <subject>`, with the completion
  report (section 9) as its body. If you cannot push, write
  `git format-patch origin/main` output to `$HOME/deliverables/<TASK-ID>/` and
  say so in the report.
* Never commit any of these: `.test_runtime/`, `data/settings.json` (tests
  write it), smoke or browser evidence, screenshots (unless the task asks for
  them), `.venv`, `node_modules`.
* Pushing files under `.github/workflows/` needs a token with the `workflow`
  scope. If the push is refused for that reason, deliver the workflow file in
  the PR description and in the deliverables folder for the owner to commit.

## 8. Stop and ask

Stop, write down what you found, and ask the PM rather than guessing when
the work needs any of these:

* a product decision: wording, a visible default, which of two behaviours is
  intended, or whether to retire something;
* loosening authorisation, deleting or rewriting user data, or a migration that
  cannot be reversed;
* credentials or secrets you do not have, such as `SMOKE_ADMIN_PASSWORD` for CI;
* translation text in any language;
* growing the scope beyond the task, or a diff that passes about 600 changed
  lines outside generated files. In that case, propose a split.

## 9. Completion report

Use this structure, as the PR body and as your final message:

```
## Completion report — <TASK-ID> <title>
1. Outcome: DONE | PARTIAL | BLOCKED — one sentence.
2. Base → head: origin/main <sha> → <branch> @ <sha>; PR <url> (or patch path).
3. Changes, by commit: what and why (root cause where a defect was fixed).
4. Evidence: command → passed / failed / skipped (each skip with its reason), before and after.
5. Acceptance criteria: each one → met / not met, with the proof.
6. Pre-existing failures: proven on origin/main; untouched.
7. Discrepancies: where the prompt or docs disagreed with the repository.
8. Decisions needed: options, consequences, and your recommendation.
9. Follow-ups found but not done: why, and the suggested owner or prompt.
10. Registers and documents updated: defect register, coverage matrix, generated docs.
```

## 10. Known pitfalls

* `/tmp` is a RAM-backed tmpfs of about 1 GB. A checkout plus virtualenv there
  fills it, and pgserver's `initdb` then fails with "No space left on device".
  Use `$HOME/.cache/...` and set `TMPDIR` (section 2).
* `REQUIRE_POSTGRES=1` turns "no database" into a failure. Without it, the
  integration suite can skip into green.
* Integration tests share one session database. A module that changes the
  schema or seeds rows must restore what it changed (see
  `tests/integration/_seed.py`).
* `tests/unit/test_doc_links.py` resolves every relative link and anchor in
  the root `*.md` files and in `docs/`. `tests/unit/test_no_machine_paths.py`
  rejects home-directory virtualenv paths, sandbox preview hosts, link-local
  addresses and pgserver socket paths in tracked files.
* `categories-list-page.js` is loaded as a classic script, so an `import` line
  in it is a syntax error. Switching it to a module needs a browser check.
* Running the suites modifies the **tracked** SQLite file
  `map_data/registry.db`. Before committing, restore it with
  `git checkout -- map_data/registry.db` unless your task changes it on
  purpose. Check `git status` after every test run.
* The browser crawl runner that produced the "71/71" result lived outside the
  repository. Use the committed harness under `tests/browser/` once P0-05 has
  landed.
