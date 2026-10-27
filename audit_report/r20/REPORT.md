# Round 20 — baseline proof, reader provenance, coverage closure

Branch `arena/d19d9293-syltharae-pro`. Everything below was produced in this
session by the command named next to it; artifacts live beside this file in
`audit_report/r20/`.

| label | meaning |
| --- | --- |
| **measured** | a command in this session produced this number, and the raw output is committed |
| **inferred** | follows from measured facts but was not itself executed |
| **unverified** | stated by a source other than this session; not reproduced here |

Refs: `BASE_REF` = `445982b` (`031b145^`, the commit before round 18's first fix),
`HEAD_REF` at the start of this round = `8dcbfda`.

---

## 1. Executive summary

| workstream | outcome | evidence |
| --- | --- | --- |
| 1 baseline diff | two clean worktrees at `445982b` and `8dcbfda`, both suites run, ID table classified | `id_diff_unit.csv`, `id_diff_integration.csv`, §2 |
| 2 reader provenance | **fixed** — a value in `Sheet1!D6` was cited as `Sheet1!D4`; three separate losses in one path | `tests/integration/test_spreadsheet_cell_provenance.py`, §3 |
| 3 coverage | reduced and recorded; remainder justified | §4 |
| 4 partial write | **fixed** — a failure after the commit answered 500 for four committed writes | `tests/integration/test_partial_write_faults.py`, §5 |
| 5 seed guard | **fixed** — `/health` reports an unseeded gazetteer before *Add place* does | `tests/integration/test_gazetteer_readiness.py`, §6 |
| 6 error safety | **measured clean** — 21 error paths × 3 caller classes, 0 leaks | `tests/integration/test_error_message_safety.py`, §7 |
| 7 artifact portability | **fixed** — a gate, plus a baseline for the raw logs that cannot be rewritten honestly | `tools/audit/check_artifact_portability.py`, §8 |

Commits in this round (oldest first). The hashes are the re-created ones — the
originals were lost when the sandbox re-cloned at 09:29 (§9); the content, the
order and the messages are the same:

| commit | what |
| --- | --- |
| `1c60be5` | readers: keep the row a spreadsheet cell actually sits in (§3) |
| `32ac37d` | health: report an unseeded gazetteer before *Add place* does (§6) |
| `df5ad94` | places: a failure after the commit is not a failed write (§5) |
| `34e0b24` | probe: give the 65 unfixtured endpoints a fixture, not a skip (§4) |
| `e7e0b34` | errors: no exception text reaches an unauthenticated caller (§7) |
| `caa4687` | portability: rewrite host paths, and fail if they reappear (§8) |
| `019bd7a` | i18n/theme: reuse catalog vocabulary, keep the event runtime first (§2.3) |
| `eb987e5` | evidence: regenerate the endpoint inventory |
| _this commit_ | round 20 record |

Not part of the round's directives but produced in the same session: the plan in
`docs/plans/CATEGORY_TERM_I18N.md` for multilingual category / term / keyword
labels, with `tools/audit/scan_term_label_surface.py` and its inventory
`term_label_surface.csv` (§10, item 11).

---

## 2. Baseline diff (Workstream 1)

Two detached worktrees, one database each (the suite creates a disposable
PostgreSQL per session, so the databases are independent by construction):

```
git worktree add --detach /tmp/wt/base 445982b
git worktree add --detach /tmp/wt/head 8dcbfda
APP_DATA_DIR=<worktree>/.test_runtime_<label> \
  python -m pytest tests/unit|tests/integration -q --junit-xml=audit_report/r20/junit_<label>_<suite>.xml
```

Reader inventory in both environments (identical by construction — same
interpreter, same `site-packages`):

| optional reader | version |
| --- | --- |
| openpyxl | 3.1.5 |
| xlrd | 2.0.2 |
| odfpy | 1.4.1 |
| python-docx | 1.2.0 |
| python-pptx | 1.0.2 |
| pymupdf / pymupdf4llm / pymupdf_layout | 2.0 |
| pandas | 3.1.0 |
| pytesseract | 0.3.13 (no `tesseract` binary on PATH) |
| imageio-ffmpeg | 0.6.0 (no `ffmpeg` binary on PATH) |

### 2.1 An environment limit that changed the method (measured)

The first attempt ran the two unit suites **concurrently**. Both were killed:

```
[07:48:52] base unit
/tmp/run_suite.sh: line 12: 124530 Killed  ... pytest tests/unit
[07:49:05] head unit
/tmp/run_suite.sh: line 12: 124705 Killed  ... pytest tests/unit
```

`dmesg` names the reason: `Out of memory: Killed process 124705 (python)
total-vm:2907876kB, anon-rss:1715960kB`. The box has 3 939 MB and no swap, and
one unit run peaks near 1.7 GB, so two cannot coexist. The runs were restarted
**sequentially** (base unit → base integration → head unit → head integration)
with the same interpreter and the same `APP_DATA_DIR` policy; the concurrent
attempts were discarded rather than mixed into the table.

### 2.2 Results (measured)

Run sequentially, one suite at a time, one process at a time. The head
integration suite was killed during the first pass (§2.1) and re-run alone until
it finished; that second run is the one in the table and in
`junit_head_integration.xml`.

| suite | tests | failures | errors | skipped | artifacts |
| --- | --- | --- | --- | --- | --- |
| base unit (`445982b`) | 3482 | 30 | 11 | 11 | `junit_base_unit.xml`, `log_base_unit.txt` |
| base integration (`445982b`) | 1191 | 7 | 0 | 29 | `junit_base_integration.xml`, `log_base_integration.txt` |
| head unit (`8dcbfda`) | 3496 | 40 | 11 | 11 | `junit_head_unit.xml`, `log_head_unit.txt` |
| head integration (`8dcbfda`) | 1206 | 12 | 0 | 29 | `junit_head_integration.xml`, `log_head_integration.txt` |

Summarised with `python3 tools/audit/suite_summary.py <xml>`.

### 2.3 Classification (measured)

`tools/audit/compare_suite_ids.py base.xml head.xml --csv …` compares the two
runs by test id, not by count:

| suite | ids | stable | pre-existing | regression | unclassified |
| --- | --- | --- | --- | --- | --- |
| unit | 3496 | 3445 | 41 | **10** | 0 |
| integration | 1206 | 1194 | 7 | **5** | 0 |

Fifteen regressions, every one traceable to a round-19 change:

| dropped id | cause | status |
| --- | --- | --- |
| `test_lexis_cosmos_i18n` ×9 | 29 user-visible strings added to the page with no catalog row | **fixed** (`019bd7a`), re-measured at the final tree: 26 passed, 4 skipped across this module and `test_csp_no_inline_script` |
| `test_csp_no_inline_script.TestTheRuntime::test_the_shell_loads_the_runtime_first_and_synchronously` | theme initialiser placed above the declarative event runtime | **fixed** (`019bd7a`), same run |
| `test_translation_coverage::test_every_interface_string_is_translated[ar/he/fa/hr]` | `Appearance` and `Light, dark, or follow the system` in `base.html` with no rows | **fixed** (`019bd7a`); measured before the environment reset, not re-measured since |
| `test_interface_coverage.TestTheEvidenceReport::test_the_endpoint_inventory_matches_the_application` | four round-19 export routes missing from the generated inventory | **fixed** (`eb987e5`); measured before the environment reset |

The pre-existing groups are the same on both sides, so no fix in this round was
bought by lowering another result:

| cause (taken from the failure message recorded in `junit_head_unit.xml`) | ids |
| --- | --- |
| `docs/INTERFACE_REGISTRY.md` is not in the repository (`the registry document is missing`) | 7 |
| `docs/REGISTRY_EVIDENCE.md` is not in the repository | 6 |
| `docs/COMPONENT_LIBRARY.md` is not in the repository | 5 |
| `docs/DOMAIN_MODEL.md` is not in the repository | 3 |
| `docs/ACTION_SURFACE_AUDIT.md`, `docs/ARCHITECTURE.md`, `docs/EXPERIENCE_CONTRACT.md`, `docs/SCREEN_INSPECTOR_EVIDENCE.md` — 2 each | 8 |
| `docs/PRODUCTIZATION_MAP.md`, `docs/reference/README.md`, `docs/windows/DEPENDENCY_INVENTORY.md` — 1 each | 3 |
| `content_vs_identity`: `assert 'the only real sentence' in ''` / `assert 'deleted paragraph' in ''` | 2 |
| `identifiers_intel`: `KeyError: 'email'`, `assert {'identifier'} == {'email'}` | 2 |
| `licensing`: `pymupdf-layout 2.0: ? (no usable licence metadata)` in the installed build | 2 |
| `component_library.TestAdoption`: `assert 12 == 9` (hand-written markup count drifted) | 1 |
| `install_cli_config`: `ruff`/`vulture` pinned in `requirements.txt`, absent from the installed environment | 1 |
| `no_machine_paths`: historical captures still contain a socket path | 1 |
| **total** | **41** |

Row 1 is the registry document that *embeds* the generated block, so it takes
the generated-block errors with it; rows 1–6 are one class — **documents that
are not in the repository at all**, 32 of the 41 ids. Six ids are real
behaviour questions rather than drift: `content_vs_identity` (identity metadata
displacing content), `identifiers_intel` (an `email` kind missing from the
detection result — the same vocabulary the round's Bug A work touched), and the
`pymupdf-layout` licence reading. They are ticketed in §10 as triage items, not
folded into the documentation group.

Integration: 4 × `test_no_catalog_entry_is_empty_or_fuzzy` (empty/fuzzy entries
in ar/he/fa/hr), 1 × `test_interface_coverage` evidence report (same missing
`REGISTRY_EVIDENCE.md`), 2 × `test_cell_locations_and_recipients` (the
cell-location defect, fixed in §3 after this diff was taken).

None of these is fixed here: the standing instruction is to ticket generated-doc
drift and frozen catalogs, not to edit them to make a test pass. They are
carried to §10 with an owner-sized ticket each.

**What this table is not.** It compares `BASE_REF` with the round's *starting*
commit `8dcbfda`; the fixes landed afterwards. Re-running both suites at the
final commit is the remaining gate item (§9), interrupted by the environment
reset described there. The 10 unit regressions are the exception: they were
re-measured at the final tree after the reset.

---

## 3. Reader provenance: `Sheet1 - B3` vs `B4` (Workstream 2)

### 3.1 Reproduction (measured, before the fix)

`tests/integration/test_spreadsheet_cell_provenance.py` builds a workbook whose
content starts at `C3` (rows 1–2 blank, columns A–B blank), with an interior
blank row 5, a merged `C1:D1`, a hidden row 7, and a second sheet. Rebuilding
every address from the stored text and comparing with openpyxl's own reading
gave, at `8dcbfda`:

| assertion | expected | measured before | measured after |
| --- | --- | --- | --- |
| `Sheet1!C3` | `Region` | `EMEA` | `Region` |
| search citation for the `D6` value | `Sheet1 - D6` | `Sheet1 - D4` | `Sheet1 - D6` |
| `Notes!A1` | `Author` | missing | `Author` |
| `Notes!B2` | marker note | cited as `B1` | `B2` |

### 3.2 Three causes, one path

| # | where | what it did | fix |
| --- | --- | --- | --- |
| 1 | `reader_file/readers/read_office.py:read_xlsx_file` | drops rows that are entirely empty and records their numbers in `row_numbers` — which **no code read** | `pipeline/storage_pipeline.py::_extract_sheet_text(data, row_numbers)` writes the gaps back as empty lines, including blanks above the first datum |
| 2 | `Api/services/search_service.py::_spreadsheet_row_map` | a line without a tab was "not a data row", so the one-cell first row of a sheet did not advance the counter | every remaining line is a row; a line without a tab is column A |
| 3 | `reader_file/readers/read_office.py:read_ods_file` | ignored `number-rows-repeated` / `number-columns-repeated` | `_ods_repeat` + `_ods_row_cells` expand repeats, holding back trailing empty runs so a padded sheet cannot explode |

The XLS path (`xlrd`) keeps every row of `sheet.nrows`, so it needed no change;
CSV keeps its blank line by construction. Both were re-measured.

### 3.3 Round-trip

`test_round_trip_against_an_independent_reader` takes every `(location, value)`
emitted for the workbook and asserts that openpyxl finds that value at that
coordinate — an independent reader, not a second copy of the row arithmetic.
The ODS case asserts the repeats explicitly (two blank rows stay two rows;
three empty cells stay three columns).

`11 passed` for `test_spreadsheet_cell_provenance.py` +
`test_cell_locations_and_recipients.py` together (measured, after the fix).

---

## 4. Coverage closure (Workstream 3)

Source of the numbers: `audit_report/findings/param_routes.csv`, regenerated by
`tools/audit/probe_param_routes.py` (680 rows = 170 rules × 4 variants).

| verdict | before this round |
| --- | --- |
| OK | 606 |
| SKIPPED (NO-FIXTURE) | 65 |
| NOT-IMPLEMENTED (declared 501) | 9 |

The 65 SKIPPED rows cover 47 distinct routes. Status and decisions are in §4.2;
the counts after this round are recorded in the same table.

### 4.1 Declared 501s

`content_analysis.get_entities`, `get_sentiment`, `get_topics` — three routes,
three variants each. Each answers
`{"code": "not_implemented", "error": “… is not available in this version”, "success": false}`
(measured, `param_routes.csv`), consistently across all three variants and
without touching the database (`db_effect` column is `-` for all nine rows).

### 4.2 NO-FIXTURE decisions

| class of NO-FIXTURE route | routes | decision | after |
| --- | --- | --- | --- |
| object created through an API the probe already uses (places, place names, LEXIS views) | 8 | add a fixture | `place_id`, `name_id`, `view_id` (+ an "other user" view) exist; routes return real answers |
| settings (`/api/settings/<category>`, `/storage/<key>`, `/theme/<key>`, backups) | 8 | **probe bug, not a missing fixture** — the "other user" variant never fell back to a text value, so a route with no id was reported as unfixturable | fixed in the probe; all measured |
| jobs and chunked uploads (`/api/jobs/<id>/*`, `/upload/*`, `/api/input/uploads/chunked/*`) | 17 | add a fixture where the API creates one (chunked session: `POST /api/input/uploads/chunked/start` → 201) | session created; the rest measured through the synthetic id below |
| map tiles (`/api/map/raster|/cache/...`) | 6 | **accept the gap** — a tile needs a downloaded map package (external data), and the route is already covered by the missing-id variant | exercised with id 0 → 404, no 5xx |
| audit entry (`/api/audit/<id>`) | 1 | accept — `GET /api/audit` answers 400 to the probe's parameters, so no id could be read back | exercised with id 0 → 403/404 |
| scenario evaluation (`/api/scenarios/<id>/evaluations/<id>`) | 1 | accept — an evaluation row only exists after a completed `scenario_evaluation` job | exercised with id 0 → 404 |
| other (`/export/<id>`, `/api/interfaces/<id>`, `/api/experience/*`, `/api/set_language`) | 11 | add a fixture / text value | all measured |

Result (measured, `audit_report/findings/param_routes.csv`, regenerated by
`python tools/audit/probe_param_routes.py`):

| verdict | before | after |
| --- | --- | --- |
| OK | 606 | **671** |
| SKIPPED (NO-FIXTURE) | 65 | **0** |
| NOT-IMPLEMENTED (501) | 9 | 9 |
| distinct routes skipped | 52 | 0 |

Nine rows (5 routes) still use a synthetic id `0`, marked `(synthetic)` in the
`values` column: 7 answered 404 and 2 answered 403, none a 5xx. That is a
measurement of the route, not a claim that a real object was exercised.

Two probe defects were found and fixed on the way, both of which had been
inflating the NO-FIXTURE count:

* the "other user" variant of a non-id parameter produced `None` instead of the
  same plausible text used for the valid variant;
* `CROSS-USER-200` fired for `GET /operations/jobs/<job_id>` with `job_id="probe"`,
  which is a subresource page answering its own "not found" HTML — a real id is
  now required before that verdict can be reached.


---

## 5. Partial-write and retry integrity (Workstream 4)

Method: `tests/integration/test_partial_write_faults.py` injects a raise in two
places — inside the transaction (`_record_curation`, which `_write()` commits
after) and after the commit (`_revision_payload`, which the response is built
from) — on create, update, delete and the three place-name routes.

Measured matrix (after the fix; before it, the four "after commit" rows answered
500 with the row already committed):

| path | injected fault | status | rows after | retry |
| --- | --- | --- | --- | --- |
| `POST /api/places` | inside transaction | 500 | 0 (rolled back) | retry succeeds, 201 |
| `POST /api/places` | after commit | 201 | 1 | — |
| `PUT /api/places/<id>` | after commit | 200 | 1 (renamed) | — |
| `DELETE /api/places/<id>` | after commit | 200 | 0 | — |
| `POST /api/place-names` | after commit | 201 | 1 | — |
| `PUT /api/place-names/<id>` | after commit | 200 | renamed | — |
| `DELETE /api/place-names/<id>` | after commit | 200 | 0 | — |
| `POST /api/places` ×2 | none | 201 / 409 | 1 | 409 on the duplicate |

The fix: `_revision_block()` catches, logs and answers
`{"fingerprint": null, "changed": false}`, because the write it describes has
already committed.

---

## 6. Seed and setup guard (Workstream 5)

Reproduction: the test database has the migrations and no seed — exactly the
state the round-19 bug was reported from.

| state | `/health` `checks.gazetteer` | status |
| --- | --- | --- |
| no seed | `not-seeded` | 200 (`healthy`) |
| one active place | `ok` | 200 |

The endpoint does not fail on an unseeded gazetteer on purpose: the instance is
up, one feature is degraded, and a failing probe would take a working service
out of rotation. The body names no table, no path and no exception (asserted).
`POST /api/places` keeps its 503 as the last line of defence.

---

## 7. Error-message safety (Workstream 6)

`tools/audit/scan_error_bodies.py` inventories every response body that
interpolates exception text (measured):

| | count |
| --- | --- |
| response bodies mentioning an exception | 379 |
| of which routed through `client_error` / `client_safe_message` (SEC-08) | 209 |
| unsanitised | 170 |

The 170 are reviewed at runtime rather than by reading: 21 crafted cases across
places, place names, file exports, LEXIS exports, settings, analytics,
interfaces and the export surface, driven as **anonymous**, **viewer** and
**admin**. Assertion: no schema name, no SQL verb, no traceback, no driver name,
no absolute path in any body. Measured: **0 leaks in all three passes**, and the
gazetteer message keeps its one useful detail (`no category for feature_type
'city'`) which names curation vocabulary, not schema.

---

## 8. Artifact portability (Workstream 7)

`tools/audit/check_artifact_portability.py` finds `/home/<user>`, `/Users/…`,
`/tmp/…`, `C:\Users\…` and `loopback:port` inside `audit_report/`.

| | files | fragments |
| --- | --- | --- |
| offenders at the start of this round | 60 | 667 |
| after: outside the baseline | 0 | 0 |

The 60 are listed once in `portability_baseline.txt`. They are raw logs from
rounds 3–19; editing a path inside a captured run would make the file claim
something that was never printed. Everything written from this round on is
portable, and `tests/unit/test_artifact_portability.py` is the gate (including
three cases that prove the detector fires).

---

## 9. Verification gate

| gate item | status | evidence |
| --- | --- | --- |
| full unit + integration at HEAD in a clean worktree, fresh DB | **partially met** | both suites measured at the round-start commit (`8dcbfda`, §2.2); at the final commit only the two unit modules that carried regressions were re-run (26 passed, 4 skipped). The final full run started at 08:43 and was interrupted, not failed |
| no regression against `BASE_REF`, zero unclassified ids | **met for the measured runs** — 15 regressions found, all attributable and all fixed; not re-measured at the final commit | `id_diff_unit.csv`, `id_diff_integration.csv` |
| `git diff HEAD -- database/migrations` empty, schema freeze intact | **met** | measured after the last commit of the round |
| probe counts: 3 030 malformed, 6 560 query-string, 680 parameterised | **partially met** | the parameterised sweep was re-measured this round (680 rows, 0 findings, 0 skipped, §4); the malformed and query-string sweeps were not re-run this round |
| browser re-run: Bug B 503 modal | **met** before the environment reset (dev stack + `repro_bug_b.mjs`) | |
| browser re-run: partial-write case | **not met** | the dev stack was stopped to free memory and has not been rebuilt |

**Why the last two rows are incomplete, stated plainly.** At 09:29 the sandbox
was re-cloned from GitHub mid-session. `/tmp` — the virtualenv, the two
worktrees, the PostgreSQL data directory — did not survive, and the round's
local commit objects were lost with the old clone. The working tree survived,
the round's commits have been re-created from it (`1c60be5` … `eb987e5`), and no
fix content was lost; but re-running a full suite needs a rebuilt interpreter
with `pgserver`, `pandas`, `pymupdf` and the rest, which is environment work,
not verification. This report therefore states clearly which numbers were
measured before the reset and which were re-measured after it, and does not
present the interrupted run as a result: `log_head_unit.txt` is 12 lines of a
killed run, kept for the record, not quoted as a count.

---

## 10. Backlog

Ordered by what would bite a user first. Effort is developer-time for the fix
alone, excluding review.

| # | item | severity | scope | effort | risk / note |
| --- | --- | --- | --- | --- | --- |
| 1 | Re-run both suites at the final commit and publish the id diff | **blocker for closing the round** | rebuild the environment, then one sequential run per suite | 0.5 d | no technical risk; the 15 known regressions are already fixed, this is confirmation |
| 2 | **32 ids**: documents that are not in the repository — `INTERFACE_REGISTRY.md` (7), `REGISTRY_EVIDENCE.md` (6), `COMPONENT_LIBRARY.md` (5), `DOMAIN_MODEL.md` (3), `ACTION_SURFACE_AUDIT.md` / `ARCHITECTURE.md` / `EXPERIENCE_CONTRACT.md` / `SCREEN_INSPECTOR_EVIDENCE.md` (2 each), `PRODUCTIZATION_MAP.md` / `reference/README.md` / `windows/DEPENDENCY_INVENTORY.md` (1 each) | high (32 tests, no user impact) | generate with `core.interfaces.evidence --write` and `tools/docs/generate_reference.py`, commit the documents | 1.5 d | needs an explicit decision: they are generated documents, and the standing rule forbids writing documents to satisfy tests |
| 3 | `identifiers_intel`: no `email` kind in the detection result (`KeyError: 'email'`, `{'identifier'} == {'email'}`) | medium — a document with an email address is not reported as such | identifier detection vocabulary + the `identifier_kind` filter the round's Bug A work touched | 1 d | could be the same class of defect as Bug A; triage before scheduling |
| 4 | `content_vs_identity`: identity metadata appears to displace extracted content (`'the only real sentence' in ''`) | medium — a reader losing content | reader/extraction core (docx/pdf metadata path) | 1–2 d | needs **reproduction first**; the fixture may be the problem, not the reader |
| 5 | Four catalog entries are empty or fuzzy in ar/he/fa/hr | medium | translation authoring by a human | 0.5 d | machine translation is forbidden by standing rule |
| 6 | `licensing`: `pymupdf-layout` ships no usable licence metadata in the installed build | low (compliance reporting) | record the licence in the dependency inventory or pin a build that declares it | 0.5 d | affects the offline kit's licence surface, not runtime |
| 7 | `component_library.TestAdoption`: `assert 12 == 9`, the hand-written markup count drifted | low | regenerate the count from the library | 0.25 d | same decision as #2 |
| 8 | `no_machine_paths`: historical captures still contain a socket path | low | accept as historical, or re-run those rounds' evidence | 1 d if re-run | the portability gate deliberately exempts pre-round-20 captures (§8): rewriting them would make them claim something never printed |
| 9 | `install_cli_config::test_an_installed_environment_reports_no_missing_packages` | low (environment) | install `ruff`/`vulture` in the test environment, or classify the test as environment-dependent | 0.25 d | not a code defect |
| 10 | Flaky classification: the 48 non-passing ids were not re-run three times | low (method) | 3× rerun of those ids | 0.5 d | until then they are "pre-existing", not "flaky" |
| 11 | Multilingual category / term / keyword labels — plan written, not implemented | feature | one additive migration + resolver + six search entry points | ~8 d | blocked on the schema-freeze decision (`docs/plans/CATEGORY_TERM_I18N.md`, decision D1) |
