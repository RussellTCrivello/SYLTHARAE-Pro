# Development notes

> **STATUS: NEEDS-REVIEW.** Written during a repair pass to answer questions
> raised by the test suite, not reviewed by the project owner. The commands
> were run, but the workflow described here has not been agreed as the
> project's development process.

## Running the tests

```bash
python3 -m pytest tests/unit
DB_HOST=... python3 -m pytest tests/integration
```

The integration suite needs PostgreSQL. When no server is reachable the
fixtures skip rather than fail; `pgserver` (installed with the test extras)
provides a disposable one. The three ways it can look "reachable" and still
skip are worth knowing:

* the crash-recovery tests connect with their own variables, not `DB_*`
  (`SYLTHARAE_TEST_PG_HOST` / `_PORT` / `_USER` / `_PASSWORD`, default
  `localhost:5432`), so a server started on a unix socket directory
  (`DB_HOST=/tmp/pgdata`, no TCP listener) is reachable for the application and
  invisible to them - they skip with "PostgreSQL not reachable for the
  crash-recovery tests". Set `SYLTHARAE_TEST_PG_HOST` to the same value as
  `DB_HOST`;
* `pytest.importorskip("psycopg2")` turns a missing driver into a skip, not an
  error;
* a test module that cannot create its fixture database skips rather than
  failing.

## When the OCR tests all fail or skip at once

The OCR layer runs on `rapidocr-onnxruntime`, which imports `cv2` when it is
imported. A wheel that `pip list` reports as installed but whose `cv2` module
is not actually importable makes `core.ocr.engines.ocr_available()` return
`False`; the OCR tests then skip with "no OCR engine installed", or fail with
`assert False is True`, and the self-check prints
`status: unavailable`. This is an install fault, not a product defect - do not
"fix" it in the engine or in the tests.

Diagnose:

```bash
python3 -c "import cv2; print(cv2.__version__)"                 # first import that fails
python3 -c "from core.ocr.engines import ocr_available; print(ocr_available())"
python3 tools/ci/ocr_selfcheck.py                                # what the engine reads on this host
```

Repair the wheel, then re-run the OCR tests:

```bash
python3 -m pip install --force-reinstall --no-deps "opencv-python-headless>=4.9"
python3 -c "import cv2, rapidocr_onnxruntime; print(cv2.__version__)"
python3 -m pytest tests/unit/test_ocr_matrix.py \
                 tests/unit/test_date_and_orientation.py
```

Reinstalling the same version can be the fix: the broken environment listed
`opencv-python-headless 5.0.0.93` in `pip list` while `import cv2` raised
`ModuleNotFoundError`, and `pip install --force-reinstall --no-deps` of that
same version made the module importable and turned 95 skipped OCR tests and 29
failing ones green.

## Interactive controls without inline script

The Content-Security-Policy sets `script-src 'self'`, so inline `onclick=` and
`<script>` blocks are rejected by the browser. Controls are wired like this:

```html
<button data-on-click="deleteCategory(3, 'Reports')">Delete</button>
```

`static/js/modules/core/declarative-events.js` installs one delegated listener
per event type and evaluates the expression with `this` bound to the element
and `event` bound to the event. The expression is interpreted, never passed to
`eval`/`Function`, and it accepts only a small subset of JavaScript: calls,
member access, literals, `this`, `event`, the usual comparison and boolean
operators, and `return false` to prevent the default action.

Because names are resolved in the global scope, a page module that references a
handler from markup must publish it:

```javascript
window.deleteCategory = deleteCategory;
```

Guards: `tests/unit/test_csp_no_inline_script.py` fails on a new inline handler
attribute, a generated `on<event>=` attribute, or a template `<script>` block;
`tests/unit/test_shared_js_helpers.py` fails on a new local `escapeHtml` copy.

## Adding a migration

Migrations live in `database/migrations/` and are applied in version order by
`database.migration_runner`. Each is a module with `version`, `name` and an
`upgrade(conn)` function, and must be idempotent where the operation allows it.
`tests/integration/test_bootstrap_migrations.py` builds a fresh database from
scratch and `tests/integration/test_startup_upgrade_path.py` covers upgrading an
existing one.

## Regenerating reference documentation

```bash
python3 tools/docs/generate_schema.py       # docs/reference/DATABASE_SCHEMA.md
python3 tools/docs/generate_reference.py    # docs/reference/**
```

`tests/integration/test_schema_reference.py` and
`tests/unit/test_reference_docs.py` fail when the committed files are stale.
