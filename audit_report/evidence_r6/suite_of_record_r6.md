# Round 6 suite of record — environment, runs, and what changed

Tree: `5f4db9f` (nothing committed between the two runs; the only edits were to
`tools/audit/*` and `docs/`, which the suite of record did not exercise).
Interpreter `/tmp/sylth-venv/bin/python` 3.11.2, pytest 9.1.1, `-p no:randomly`.

## Environment

Set for both parts of both runs (`/tmp/sylth_pg_env.sh`, plus the test-only
variables the crash-recovery module reads):

| variable | value |
| --- | --- |
| `DB_HOST` | `/tmp/pgdata_main` (unix socket directory; no TCP listener) |
| `DB_PORT` | `5432` |
| `DB_USER` / `DB_PASSWORD` | `postgres` / empty |
| `DB_NAME` | `postgres` |
| `APP_DATA_DIR` | `/tmp/sylth_appdata` |
| `HOME` | `/tmp/sylth_home` |
| `SYLTHARAE_TEST_PG_HOST` | `/tmp/pgdata_main` |
| `SYLTHARAE_TEST_PG_PORT` | `5432` |
| `SYLTHARAE_TEST_PG_USER` | `postgres` |

`tests/integration/test_resume_real_database.py` reads `SYLTHARAE_TEST_PG_*`
and defaults to `localhost:5432`. The server listens on a socket directory
only, so with the variable unset the module skips 26 tests. Run 1 of the
repaired pair (see below) predates our setting it and skipped them; run 2 sets
it and they execute: 25 passed, 1 xfailed, and the module's own skip no longer
fires.

## Commands

```bash
pytest tests/unit -q --junitxml=<unit>.xml
pytest tests/integration tests/security tests/e2e tests/browser tests/js -q --junitxml=<rest>.xml
```

## Results

| run | part | tests | failures | errors | skipped |
| --- | --- | --- | --- | --- | --- |
| run 1 (cv2 repaired, no `SYLTHARAE_TEST_PG_HOST`) | unit | 3190 | 34 | 11 | 11 |
| | rest | 1209 | 17 | 0 | 28 |
| run 2 (suite of record) | unit | 3190 | 34 | 11 | 11 |
| | rest | 1209 | 17 | 0 | 3 |
| **total** | | **4399** | **51** | **11** | **14** |

Failing/erroring test cases: **62** in both runs. The failing-ID sets are
identical — 45 in part A, 17 in part B, with an empty symmetric difference
(`junit_r6_unit.xml` vs `junit_r6_unit_run1.xml`,
`junit_r6_rest.xml` vs `junit_r6_rest_run1.xml`).

Triage (`tools/audit/triage_failures.py`, `findings/failure_triage.csv`):

| category | cases |
| --- | --- |
| `DOCS-NOT-COMMITTED` (D-7) | 38 |
| `NEEDS-DECISION` (D-4, D-5, D-6, D-10) | 24 |
| `PROJECT-DEFECT` | 0 |
| `COLLATERAL` | 0 |
| `ENV` | 0 |

## OCR: 95 formerly skipped tests

`rapidocr-onnxruntime` imports `cv2`; the rebuilt venv listed
`opencv-python-headless 5.0.0.93` in `pip list` while `import cv2` raised
`ModuleNotFoundError`. Reinstalling the same version
(`pip install --force-reinstall --no-deps "opencv-python-headless>=4.9"`) made
the module importable. Effect, measured by re-running part B with
`rapidocr_onnxruntime` made unimportable (`PYTHONPATH` shim) and comparing:

* 95 tests skip when the engine is unavailable (11 in `tests/unit/test_ocr_matrix.py`,
  84 across `test_archive_lineage`, `test_archive_nesting`, `test_email_lineage`,
  `test_file_details_api`, `test_ocr_searchable`, `test_provenance_persisted`,
  `test_universal_recursion`);
* **all 95 pass** in the suite of record; none fail, none skip.

## Schema

`git diff 2670f3b -- database/migrations` — empty.
