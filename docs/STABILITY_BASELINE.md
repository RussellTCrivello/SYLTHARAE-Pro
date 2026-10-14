# Stability baseline

Recorded during the verification pass for the current engineering problem.
This file states what was executed and what it showed. It does not claim
production readiness.

## Repository state

| Item | Value |
|---|---|
| Branch | `arena/f107c193-syltharae-pro` |
| Remote tip (verified with `git ls-remote`) | `215b992` before this commit |
| Pull request | #1, OPEN, head matches the remote tip, `mergeStateStatus` UNKNOWN |
| `main` | `948b973`; the branch is 0 behind and 26+ commits ahead |
| Reported commits `22ee34a`, `4f4d7b8`, `215b992` | all present in the branch history |
| Working copy used for tests | detached worktree `<working copy>`, clean at start |
| Main checkout `/home/user/SYLTHARAE-Pro` | on the branch at `948b973`, 120 changed paths, not modified by this work |
| Backup of the main checkout | `/home/user/backups/main-checkout-20261014-073753` (checksums in `SHA256SUMS`) |

## Environment

- Python 3.11 virtual environment at `/tmp/auditenv` (outside the repository).
- Installed for testing, from the declared `dev` extra in `pyproject.toml`:
  `pytest`, `pytest-cov`, `ruff`, `bandit`, `pgserver`, `pyzipper`.
- `opencv-python-headless` installed in place of `opencv-python`. The GUI
  build needs `libGL.so.1`, which this host lacks.
- The `tesseract` binary is not installed. OCR tests pass through the
  RapidOCR path only, so tesseract-specific code paths are not exercised.
- `/tmp/auditenv` is not part of the repository. The setup must be documented
  (see `TEST_ENVIRONMENT.md` when written).

## Executed results

| Suite | Command | Result |
|---|---|---|
| Node smoke tests | `node tests/js/*_smoke.mjs` | 15 of 16 pass. `action_lifecycle_smoke.mjs` exits 1 when run bare; it passes through its pytest wrapper. |
| Search, PostgreSQL | `pytest tests/integration/test_search_*.py` plus search unit tests | 71 passed |
| Screen inspector | `pytest tests/unit/test_screen_inspector.py` | 96 passed, 1 skipped (markup-binding case; the product has no markup bindings) |
| Unit and security suites | `pytest tests/unit tests/security --continue-on-collection-errors` | 1 failure: `tests/security/test_rate_limiting.py::test_the_default_limit_still_applies_to_other_endpoints` (see the defect register) |

The exact pass count for the full unit and security run was not captured,
because the quiet-mode summary was not printed. Only the failure list is
verified.

## Failure classification

- **Environment (resolved in the test venv):** PostgreSQL missing (`pgserver`
  not installed), OCR, PDF rotation, embedded images, and encrypted-ZIP tests
  (`pyzipper` not installed). These are now passing.
- **Test defect (corrected):** the screen-inspector binding test assumed a
  single binding for `files.view_original`.
- **Stale generated document (regenerated):** action-surface,
  screen-inspector, component-library, experience-contract, and reference
  documents.
- **Unverified:** the rate-limit test (see the defect register).

## Outstanding verification gaps

- No browser or end-to-end run. Chromium automation is not available on this
  host.
- Tesseract-specific OCR paths.
- No full-scale ingestion benchmark yet.
- The rate-limit test's cause is not established.
