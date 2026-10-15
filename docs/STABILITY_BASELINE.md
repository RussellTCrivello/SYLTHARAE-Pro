# Stability baseline

What a clean `origin/main` does when the documented environment is built with
one command and every suite is run through it. This file states what was
executed and what it showed, and nothing here is a claim of production
readiness. How to reproduce: [TEST_ENVIRONMENT.md](TEST_ENVIRONMENT.md).

## Repository state

| Item | Value |
|---|---|
| `main` | `aa2b865` (merge of PR #1), 15 Oct 2026 |
| Measured tree | `origin/main` at `aa2b865`, in a fresh clone, with the `tools/dev/` scripts of this change present as untracked files — they are the measuring instrument, not the measured tree |
| Working copy at test time | clean; `map_data/registry.db` restored after each suite (the suites modify it) |
| This baseline was produced by | task P0-02, branch `arena/P0-02-test-environment-baseline` |

## Environment

Debian sandbox, 2 vCPU, about 3.9 GB RAM, no swap; `/tmp` is disk-backed in
this particular sandbox, but `TMPDIR` was kept on `$HOME/.cache/tmp` per the
protocol anyway ([AGENTS.md](../AGENTS.md) section 2 describes the 2 GB
RAM-tmpfs variant of this sandbox class; the measured one had more headroom).
Python 3.11.2 (system interpreter via the `uv venv -p 3.11` fallback; the
managed-Python download is blocked here), uv 0.13.1, Node 22.22.3, PostgreSQL
16.2 through pgserver 0.1.4, `REQUIRE_POSTGRES=1`. Installed: ripgrep.
Absent: tesseract, nginx, `xlwt`, Chromium's shared libraries (this sandbox's
apt egress is blocked; see [TEST_ENVIRONMENT.md](TEST_ENVIRONMENT.md)).

## Results

All commands run from the repository root on the measured tree above; counts
from the combined JUnit report of each command, durations wall-clock.

| Command | Passed | Failed | Errors | Skipped | Duration |
|---|---|---|---|---|---|
| `bash tools/dev/bootstrap.sh` (clean directory) | — | — | — | — | 3.7 s (0.8 s re-run) |
| `bash tools/dev/run_tests.sh tests/unit 4` | 3,468 | 0 | 0 | 6 | 250 s |
| `bash tools/dev/run_tests.sh tests/security` | 131 | 0 | 0 | 0 | 28 s |
| `bash tools/dev/run_tests.sh tests/integration 4` | 1,193 | 4 | 0 | 27 | 219 s |
| `bash tools/dev/run_tests.sh tests/e2e` | 23 | 0 | 0 | 0 | 6 s |
| `node tests/js/*_smoke.mjs` (22 harnesses, bare) | 21 | 1 (see classification) | — | — | 3 s |
| pytest wrappers of the Node harnesses (12 files) | 254 | 0 | 0 | 1 | 53 s |

`tests/unit` ran as 4 shards of 52/52/52/50 files (206 files, 3,474 tests;
shard durations 71/24/101/54 s). `tests/integration` ran as 4 shards of 28
files (112 files, 1,224 tests). Zero "No reachable PostgreSQL" skips anywhere:
the disposable pgserver was reachable for every shard.

For comparison, an earlier sharded verification pass at the same commit on a
2 GB sandbox recorded `tests/unit` as 3,436 tests in 205 runnable files,
3,424 passed, 1 failed, 11 skipped. The differences reconcile exactly:
+38 tests are `tests/unit/test_ocr_matrix.py`, which was OOM-killed on 2 GB
and passes here; −5 skips are the ripgrep tests, which run here because
ripgrep is installed; the 1 failure (the action-toolbar contract test, see
the gaps below) does not reproduce in this environment. The earlier pass's
`tests/security` (131 passed) and `tests/integration` (1,193 passed, 4
failed, 27 skipped) match this baseline exactly.

## Failure classification

* **Deliberate (4).** `tests/integration/test_translation_coverage.py::
  test_no_catalog_entry_is_empty_or_fuzzy` for `ar`, `he`, `fa`, `hr`:
  311 / 286 / 286 / 361 untranslated or fuzzy entries. These fail on purpose
  until people supply the translations
  ([AGENTS.md](../AGENTS.md) rule 6); they are not regressions.
* **Expected usage, not a defect (1).** `action_lifecycle_smoke.mjs` fails
  when run bare because it expects fixture paths as arguments; its pytest
  wrapper passes them (254/255 wrapper tests pass, see above).
* **Product defects, reproduced at `origin/main`, registered, not fixed here
  (2).** See [DEFECT_REGISTER.md](DEFECT_REGISTER.md):
  * item 15 — a plain `pip install -r requirements.txt` leaves two
    conflicting OpenCV distributions; on hosts without `libGL.so.1`,
    `import cv2` fails and 20 OCR unit tests fail (measured: 14 failed in
    `test_date_and_orientation.py` + `test_embedded_images.py`, 6 failed and
    11 skipped in `test_ocr_matrix.py`). `tools/dev/bootstrap.sh` repairs the
    environment; the manifest is unchanged.
  * item 16 — `GET /api/translations` returns HTTP 500 for every locale
    (verified for `en`, `ar`, `he`, `fa`, `hr` on a live install): Babel
    plural msgids are tuple keys, and `jsonify` sorts keys, so serialization
    raises `TypeError`. No test covers the endpoint.

## Skip reasons

`tests/unit` (6 skips):

| Count | Reason | Class |
|---|---|---|
| 2 | `xlwt` not installed (legacy `.xls` writer; a test dependency no manifest declares) | environment / test-infrastructure |
| 2 | the disposable database has no records to export (`test_search_export_authority`) | fixture state, by design |
| 1 | no markup bindings exist in the product today (`test_screen_inspector`) | by design |
| 1 | the first domain holds a single entry (`test_navigation_prefs`) | data-shape, by design |

`tests/integration` (27 skips):

| Count | Reason | Class |
|---|---|---|
| 26 | `test_resume_real_database.py`: its own module-level probe for a *system* PostgreSQL finds none; the probe ignores `REQUIRE_POSTGRES` (known test defect F-13, scheduled for P0-03) | test defect |
| 1 | nginx or openssl not installed (`test_deploy_nginx`) | environment |

pytest wrappers (1 skip): the markup-binding skip above, again.

## Outstanding verification gaps

* No browser harness run: Chromium's shared libraries cannot be installed on
  this sandbox (apt egress blocked), and a skip is not a pass.
* The crash-recovery suite (26 tests) has never run in this environment
  (F-13); it needs a system PostgreSQL the module's probe can reach.
* `tests/unit/test_ocr_matrix.py` needs more than 2 GB RAM; it passes here
  (about 4 GB) and was OOM-killed on the PM's 2 GB sandbox.
* `tests/unit/test_action_toolbar.py` — the test
  `test_the_runtime_turns_the_served_bar_into_the_contract` was reported
  failing at this commit on a 2 GB sandbox (a regression since `8a72e9e`, a
  commit that is not in this repository's history); it passes in every run
  here. Root cause not established; tracked for P1-01.
* tesseract-specific OCR paths are not exercised (RapidOCR path only).
* No full-scale ingestion benchmark.
* This file makes no claim of production readiness.
