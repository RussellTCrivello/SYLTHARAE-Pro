# Test environment

What the suite needs in order to run, and the one command that builds it. The
working protocol — bootstrap order, sharding, counting results — is
[AGENTS.md](../AGENTS.md); what each suite covers is
[TESTING.md](TESTING.md); the numbers a clean `origin/main` produces today are
in [STABILITY_BASELINE.md](STABILITY_BASELINE.md).

## Requirements

| Need | Why |
| --- | --- |
| 4 GB RAM or more | Shards of about 50 files keep a pytest process well under that; `tests/unit/test_ocr_matrix.py` was OOM-killed on a 2 GB runner even when run alone, and passes with about 4 GB. |
| 2 GB free on the `TMPDIR` filesystem | pgserver's `initdb` and the pytest temporary directories live there. `tools/dev/bootstrap.sh` refuses to continue below this. |
| Python 3.10–3.12 (3.11 recommended) | The project's supported range; `pgserver` publishes no wheel for 3.13 (verified against PyPI: cp39–cp312 only). |
| Node 20 or newer | The `tests/js/*.mjs` harnesses and the pytest wrappers that drive them. |
| ripgrep (`rg`) — optional | Without it, 5 unit tests in `tests/unit/test_ripgrep_line_scanner.py` skip. |
| `xlwt` — optional | Without it, 2 legacy-reader unit tests skip; it is a test dependency that no manifest declares. |
| nginx and openssl — optional | Without them, 1 integration test (`test_deploy_nginx`) skips. |
| tesseract — optional | OCR falls back to RapidOCR; tesseract-specific code paths are then not exercised. |
| `libnss3` and `libnspr4` — only for browser work | The bundled Chromium needs them. On sandboxes whose apt egress is blocked they cannot be installed, so the `tests/browser/` harnesses skip — and a skip is not a pass. |

## One-command setup

```
bash tools/dev/bootstrap.sh
```

Idempotent: re-running it is safe and fast. In order it:

1. checks that `TMPDIR` (default `$HOME/.cache/tmp`) sits on a filesystem with
   at least 2 GB free, and refuses to continue otherwise;
2. installs `uv` if it is missing (Debian's PEP 668 marker needs
   `--break-system-packages`, a no-op elsewhere);
3. tries `uv python install 3.11`, non-fatally — where the download is
   blocked, `uv venv -p 3.11` falls back to the system interpreter;
4. creates or reuses `.venv` with Python 3.11;
5. installs `requirements.txt` and the **dev extra read from
   `pyproject.toml`** (`pytest`, `pytest-cov`, `ruff`, `bandit`, `pgserver`,
   `pyzipper`) — the package list is never retyped in the script;
6. applies one known repair: a plain install leaves both `opencv-python` (pulled
   in by `rapidocr-onnxruntime`) and the declared `opencv-python-headless` in
   the venv, and on hosts without `libGL.so.1` the GUI build makes
   `import cv2` fail — the script removes the GUI build so the declared
   headless one provides `cv2` (see [DEFECT_REGISTER.md](DEFECT_REGISTER.md),
   item 15);
7. verifies the key imports and prints everything it did.

Measured on the P0-02 baseline sandbox: 3.7 s from a clean directory (warm
package cache), 0.8 s on an immediate re-run.

## Running a suite

```
bash tools/dev/run_tests.sh tests/unit 4
bash tools/dev/run_tests.sh tests/security
bash tools/dev/run_tests.sh tests/integration 4
bash tools/dev/run_tests.sh tests/e2e
```

* The shard count is optional; it defaults to one shard per 50 files.
* Files are sorted and dealt into contiguous shards, so the same directory and
  shard count always produce the same shards.
* `REQUIRE_POSTGRES=1` is the default: a missing PostgreSQL fails the run
  instead of skipping it into green.
* Each shard writes a JUnit XML file and a log under
  `$TMPDIR/run_tests/<suite>-<timestamp>/`; between shards the script deletes
  `$TMPDIR/pgdata_*` (each pytest session leaves one, 70–90 MB).
* The shards are merged and summarized by `tools/ci/junit_annotations.py`,
  which prints the totals, **every skipped test with its reason**, and every
  failure. A skip is never silent.
* Exit status is non-zero if any shard fails, errors or crashes without a
  report, or if the combined report records any failure or error.
* The suites modify the tracked `map_data/registry.db`; the script warns and
  prints the restore command when that happens.

## Reading a result

The combined summary line gives passed / failed / errors / skipped. Treat it
the way [TESTING.md](TESTING.md) teaches: report the command and the counts,
give every skip's reason, separate pre-existing failures from regressions (a
failure that reproduces identically on `origin/main` is not caused by your
change), and never weaken an assertion to obtain green. Classify anything
unusual as one of: environment, test defect, product defect, or deliberate
(the translation-coverage tests fail on purpose until people supply the text).

## Node harnesses

The `tests/js/*.mjs` harnesses run bare with `node tests/js/<name>.mjs`, and
most are also driven by pytest wrappers (for example
`tests/unit/test_action_toolbar.py`) that supply the fixture paths and assert
on their output. One harness — `action_lifecycle_smoke.mjs` — expects its
fixture paths as arguments, so a bare run fails with a `readFileSync`
`TypeError`; that is expected usage, not a defect, and its wrapper passes.

## Restricted sandboxes

On a sandbox whose egress allows only package registries: apt cannot install
anything (no `libnss3`/`libnspr4`, no nginx, no tesseract binary), and uv's
managed-Python download fails (the system interpreter is used instead). The
pytest suites still run in full through pgserver; only the browser harnesses
and the nginx deployment test are out of reach there. The general pitfalls
are [AGENTS.md section 10](../AGENTS.md#10-known-pitfalls).
