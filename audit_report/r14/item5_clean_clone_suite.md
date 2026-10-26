# Round 14, item 5 — clean-clone suite: what ran, what it produced, and what is still missing

**Status: PARTIAL — deliberately committed in this state.**

This file records item 5 of round 14 as it actually stands. It is committed so
that the incomplete part is visible in the repository instead of being lost when
the session ended, not so that it can be mistaken for a finished measurement.

## What the item asked for

Run the two-part suite on a **clean clone** of this branch, keep the JUnit
records, and diff the failing-test identifiers against the previous round's
list, so that the round-14 work can be judged against a fixed baseline
(`audit_report/r13/failing_ids_unit.txt` — 67 ids at `512ee0c`;

`audit_report/r13/failing_ids_integration.txt` — 5 ids).

## What was done

| step | state |
| --- | --- |
| clean clone of the branch | done — `/tmp/clean_r14`, checked out at `c2ad57c` |
| unit part (`pytest tests/unit`) | **done, parsed** — counts below |
| integration part (`tests/integration tests/security tests/e2e tests/browser tests/js`) | **started, did not finish** — no JUnit record produced |
| failing-id diff | unit part only, and only against a set recorded in the session |
| JUnit XML files | **LOST** — the sandbox wiped `/tmp` between sessions |

The clone was made at `c2ad57c` ("Round 14 item 3"), not at the branch tip
`ac9d551`. The tip adds one commit and it touches only committed measurement
evidence (`audit_report/evidence_scale/measurements.json`,
`audit_report/r14/performance_r14.{json,md}`), so the unit result below should
be unchanged at the tip — but that is an argument, not a measurement, and it is
recorded as such.

## Unit part — numbers, and their evidence grade

Observed during the run, from the JUnit record while it existed:

| measure | value |
| --- | --- |
| tests | 3 268 |
| passed | 3 218 |
| failed | 28 |
| errors | 11 |
| skipped | 11 |
| failing identifiers (failed + errors) | 39 |

**Evidence grade: OBSERVED-IN-SESSION.** The XML those numbers came from was
deleted with the sandbox and cannot be re-read from this commit. They are
recorded here because throwing them away would leave the round with no
information at all, and they are labelled because a number without its artifact
is not evidence under this project's own rule. Re-running the command below on
a clean clone is what turns them into evidence.

```
pytest tests/unit -q --junit-xml=<path> -p no:randomly
```

## Failing-id diff against round 13 (unit part)

| direction | count | detail |
| --- | --- | --- |
| cleared | 29 | every one of them a text-recognition test that was failing only because no OCR engine was installed; all 29 pass once the headless `opencv` wheel is present (item 3 of this round) |
| introduced | 1 | `tests/unit/test_file_select_toggle.py::TestTheWiring::test_the_function_manager_exposes_the_module_function` |
| unchanged | 38 | the documentation, licensing, reference-doc, inventory and identifier ids carried from earlier rounds |

The introduced failure is a direct consequence of item 1 of this round: the test
pins the literal source line
`window.toggleAllFilesSelection = fileSelection.toggleAllFilesSelection;`, which
the one-owner-per-action-name fix replaced with `exposeSelectionToggle()`.
Either the control must keep publishing under the old name, or the test must
assert the behaviour instead of the text of an assignment.

**Repaired after this file was first committed** (`f6cd359`): the product side
was correct and was left alone, and the test now asserts the ownership rule
instead of the text of one assignment — the suffixed export exists, the shared
module does not claim the name the files page owns, and the control consuming
the shared copy names it explicitly. Red before, green after; see
`test_file_select_toggle_after.txt`. The counts above still describe the
pre-repair state, because the full suite was not re-run for that change — only
the affected file and the two action-ownership files, which need no database.

The two identifier lists are committed beside this file as
`item5_observed_failing_ids_unit.txt` and `item5_cleared_ids_unit.txt`, both
marked with the same evidence grade.

## Integration part — where it stopped

The command was started on the same clone with `REQUIRE_POSTGRES=1`, a fresh
`APP_DATA_DIR` and `SYLTHARAE_TEST_PG_*` pointed at a real PostgreSQL 16.2
instance. It reached roughly 9 % of the run, was still executing when the
session changed, and produced no JUnit record; the sandbox then removed `/tmp`,
taking the clone, the database and the partial output with it.

There is therefore **no integration count, no integration failing-id list, and
no two-part figure** for this branch. Round 12 is the last round with a
two-part clean-clone result (`audit_report/r12/suite_unit_final_head.txt`,
`…suite_integration_final_head.txt`: unit 67 ids, integration 7 ids, both
identical to `19ec4e9`, zero new ids).

## To finish this item

1. Clone the branch fresh (`git clone --branch arena/a5145290-syltharae-pro`),
   confirm `git log --oneline -1` shows `ac9d551` — a clone of this repository
   has silently landed on `origin/main` before and that mistake costs a whole
   run.
2. Build the environment and a PostgreSQL instance (recipe:
   `audit_report/r14/README.md`), then:

   ```
   pytest tests/unit -q --junit-xml=unit.xml -p no:randomly
   pytest tests/integration tests/security tests/e2e tests/browser tests/js \
          -q --junit-xml=rest.xml -p no:randomly
   ```

3. Commit both XML files, then diff the sorted `^(FAILED|ERROR) tests/` lines of
   each against `audit_report/r13/failing_ids_unit.txt` and
   `audit_report/r13/failing_ids_integration.txt`, and replace this file's
   "OBSERVED-IN-SESSION" numbers with the measured ones.
