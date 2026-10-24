# Round 5 — what was fixed, what the suite says now, what is still yours to decide

Everything below was executed in this checkout against a real PostgreSQL 16.2 and a
real Flask process. Numbers are copied from the runs, not estimated. The raw JUnit
XML of every run is in `audit_report/evidence_r5/`; the failing-test table is
generated from those XMLs by `tools/audit/triage_failures.py` into
`audit_report/findings/failure_triage.csv` (zero `UNCLASSIFIED`).

**Schema freeze held.** `git diff 2670f3b -- database/migrations` is empty (and
`git diff 04bb817 HEAD -- database/migrations` too). No table, column,
constraint, index or seed row was added, renamed or removed in round 5.

---

## 1. Round-5 items and where each one landed

| item | what it was | result | commit |
| --- | --- | --- | --- |
| **M-1** | batch import counted a file *accepted* even when it could not be queued | **fixed**: `deferred` added, per-file status, `accepted + rejected == total` and `queued + deferred == accepted` | `203735f` |
| **M-6** | `/health` hung to the 30 s pool timeout during an outage and named the driver class | **fixed** (2 commits): deadline-bounded probe; then the real cause — the DB-backed translation overlay in `before_request` ran *before* the probe | `9fa21ac`, `987edc4` |
| **M-7** | an outage answered `401 unauthenticated` with no hint | **fixed**: outage 401 carries `code: authentication_unavailable` + `reason` + `retry_after_seconds`; a deleted session still says `unauthenticated` | `8dcdecf` |
| **M-3** | ingestion superlinear above 512 KB | **profiled, two algorithmic fixes, re-measured**; the record and both before/after profiles are committed | `04c8034`, `3f33a7f`, `7eebed6` |
| **M-2** | imports are process-local | **documented**, no schema change | `33aa680` |
| **D-1** | the scenario helper read `alerts.rule_id` | **helper rewritten** onto `scenario_id` / `scenario_evaluation_id`; nothing else in the file changed | `55354a4` |
| **D-2** | tests pinned constraint *names* | **12 failing cases now assert the rule** via `pg_get_constraintdef` (3 `saved_searches`, 9 `content_signals`/`content_signal_runs`), plus the FK and `m0039` cases handled with D-3 | `14a990c` |
| **D-3** | tests assumed `m0009/m0010/m0038/m0039` | **rewritten against `m0001–m0003`** | `fcc029f`, `c621894` |
| **D-4** | `data/gazetteer/SOURCES.md` demanded as a seed input | **packaging file shipped** with the provenance the packer can verify | `86c8d27` |
| **D-8** | 5 duplicate index shapes in the baseline | **registered**, not dropped (dropping is a schema change) | `fcc029f` |
| **D-6** | licensing metadata | **pyproject already declared the SPDX id; the README now states it** — no licence text written | `5703888` |
| **D-5** | `core.reporting` imported by 2 tests, 2 tools | **NOT DONE — blocked, see §7** | — |
| extra | `test_no_machine_paths` failed on the round-4 reports | **fixed**: the reports no longer carry this machine's checkout path | `da88926` |

### Extra finding fixed inside M-3 (`ef2e427`)

`high_and_imminent` bound the *window end* where the reference date belongs, so a
notification about an imminent date could be windowed on the wrong column. Test
`tests/unit/test_scenario_imminent_window.py` fails on `04bb817`, passes at HEAD.

---

## 2. Evidence per fix

### M-1 — every submitted file is accounted for

`POST /api/import-export/batch-import` returned `{queued: 5, error: 25}` for 30
files with no `deferred`, no `rejected`, and 25 files gone from the counters. Live
probe (30 real files, task-slot cap in force) after the fix:

```
total 30, accepted 30, queued 5, deferred 25, rejected 0
```

Mixed case (2 bad paths + 3 valid, one slot free): `total 5, rejected 2,
accepted 3, queued 1, deferred 2`. Empty request: `400 No file paths provided`.
Old contract: `queued: 5, error: 25`, `deferred` absent. Existing fields kept; the
only addition is `deferred` (and a `reason` on deferred entries).

Regression test `tests/unit/test_batch_import_accounting.py` (5 tests): 4 fail on
`04bb817` with `KeyError: 'deferred'` / `['error','error',…] != ['deferred',…]`,
all pass at HEAD.

### M-6 — `/health` answers in milliseconds, and says nothing about the driver

The first fix (deadline-bounded probe, 2 workers, 2 s) did not move the number:
the 30 s was spent *before* the route. `Api/routes/common.py`'s `before_request`
called `apply_runtime_translation_overrides(locale)` for every non-`static`
request, which reads the database and waits out the pool timeout. Measured with
PostgreSQL stopped:

| | before | after |
| --- | --- | --- |
| `GET /health` during the outage | **30.02 s**, 503 | **0.0036 / 0.0033 / 0.0033 s**, 503 |
| body | contained `OperationalError` | `{"checks":{"database":"unavailable","settings":"ok"},"status":"degraded"}` |
| healthy | 200 | 200 @ 0.017 s |
| `/api/paths` (authenticated, outage) | 401 | 401 `authentication_unavailable`, 4.6 ms |

The fix names the machine-only endpoints (`_MACHINE_ONLY_ENDPOINTS = ("health.",)`,
`_answers_without_templates()`) instead of exempting them silently.
`tests/unit/test_health_probe_not_blocked.py` (3 tests) mounts the real
`register_common_routes` chain on its own app: on `04bb817` it fails (5.0 s against
a 2.0 s bound, plus `ImportError`), at HEAD it passes.

### M-7 — an outage is not "you are not signed in"

```
store down: {"code":"authentication_unavailable","error":"…session store could not be reached",
             "reason":"session store unavailable; retry this request shortly","retry_after_seconds":5}
session deleted: {"code":"unauthenticated","error":"Authentication required"}
no cookie:       {"code":"unauthenticated","error":"Authentication required"}
```
Both still send `Set-Cookie`. Fail-closed behaviour unchanged.

### M-3 — the profile, the hot spot, the fix

Per-analyser profile at 512 KB / 1 MB / 2 MB (cProfile, top 10 cumulative, in
`audit_report/evidence_scale/ingest_profile_before.json`): the cost was
**quadratic overlap scanning**, not I/O — identifier overlap merging
(`core/detection/identifiers_intel.py`) and temporal span detection
(`core/detection/temporal_intel.py`) both compared every span with every other.

Output equivalence was proved, not assumed: excluding `detected_at`, the
`content_signals` rows are identical before vs after at 200 KB (6 984 rows) and
512 KB (20 952 rows) —
`audit_report/evidence_scale/temporal_output_equivalence.json`.

| document | before | after |
| --- | --- | --- |
| 512 KB | 33.6 s | **6.1 s** |
| 1 MB | 106.3 s | **11.9 s** |
| 2 MB | 414.2 s | **25.0 s** |

The record (hot spot, both fixes, the numbers) is
`audit_report/findings/performance_measurements.md` §1–§10 plus
`audit_report/evidence_scale/ingest_profile_after*.json`.

### D-2 / D-3 — what the edited assertions now say

Not one of these files is on the do-not-edit list. Before → after, per test:

| test | before | after |
| --- | --- | --- |
| `test_saved_searches_pg::test_constraints_reject_invalid_rows` (4 params) | `diag.constraint_name == "ck_saved_searches_name_nonempty"` etc. — 3 fail (`saved_searches_*_check` is the live name) | the violated constraint's **definition** must contain the rule (`btrim`, `criteria_fingerprint ~`, `(legacy_source IS NULL) = (legacy_id IS NULL)`, `FOREIGN KEY (owner_user_id)`) |
| `test_signal_ingestion::test_signal_constraints` (8 params) | name equality against `ck_content_signals_*` — 8 fail | rule membership: `= (date_from IS NOT NULL)`, `(date_from IS NULL) = (date_to IS NULL)`, `date_from <= date_to`, `anchor_date IS NOT NULL`, `char_end > char_start`, `dedup_key ~ '^[0-9a-f]{64}$'`, `'date_reference'::character varying` |
| `test_signal_ingestion::test_failed_run_requires_error_and_deleting_content_cascades` | `constraint_name == "ck_signal_runs_error"` | `content_signal_runs` rejects via a constraint whose definition contains `= (error IS NOT NULL)` |
| `test_structured_content_display::test_migration_m0010_created_contents_raw` | asserted migration `m0010` | asserts `contents_raw` exists in the chain `m0001–m0003` |
| `test_db_integrity_audit::test_an_out_of_vocabulary_value_is_reported_and_fails_the_gate` | imported `database.migrations.m0039_vocabulary_constraints` (never existed here) | reads the live `jobs` CHECK via `pg_get_constraintdef`, drops it, probes, and **restores the same definition** |
| `test_db_integrity_audit::test_no_duplicate_index_shape_remains` | `REGISTERED_REDUNDANT_SHAPES = set()` | the five shapes the frozen baseline creates (registered, not removed) |

Proof that the rule-based form is stronger than the name-based form
(`/tmp/d2_scratch.py`, scratch database `d2_scratch`, migrations `0001–0003`):
all 7 parameters pass; replacing a CHECK with `CHECK (true)` → the assertion
**fails**; restoring the same rule under a different constraint name → it
**passes**. Names cannot tell those two states apart; definitions can.

### D-1 — the only do-not-edit file touched

`git diff 04bb817 HEAD -- tests/integration/test_scenario_engine_pg.py` = 17 added
/ 2 removed lines, all inside the alert helper (`alerts.scenario_id`,
`alerts.scenario_evaluation_id`). The file's tests are unchanged.

`tests/integration/test_scenario_engine_pg.py`: `04bb817` **4 failed**
(`UndefinedColumn: column "rule_id" does not exist`) → `55354a4` 1 failed →
HEAD **22 passed**.

---

## 3. The suite, before and after

Two parts, same command, same machine, PostgreSQL running, `docs/` present as an
uncommitted working tree in both checkouts' baseline (see §5).

| part | tree | tests | failures | errors | skipped | time |
| --- | --- | --- | --- | --- | --- | --- |
| `tests/unit` | `04bb817` | 3170 | 50 | 11 | 11 | 411 s |
| `tests/unit` | HEAD | **3188** | **37** | 11 | 11 | 398 s |
| integration/security/e2e/browser/js | `04bb817` | 1206 | 39 | 0 | 3 | 355 s |
| integration/security/e2e/browser/js | HEAD | **1209** | **18** | 0 | 3 | 355 s |
| **total** | `04bb817` | 4376 | 89 | 11 | 14 | 766 s |
| **total** | HEAD | **4397** | **55** | **11** | **14** | 753 s |

**New failures at HEAD: 0** in both parts (set difference on
`(classname, testname)`, `audit_report/evidence_r5/junit_*_before.xml` vs
`*_after.xml`).

Fixed, and why:

| fixed cases | cause |
| --- | --- |
| 9 `test_signal_ingestion`, 3 `test_saved_searches_pg` | D-2 rules instead of names |
| 4 `test_scenario_engine_pg` | D-1 helper |
| 2 `test_db_integrity_audit`, 1 `test_structured_content_display` | D-3 |
| 4 `test_batch_import_accounting` | M-1 |
| 2 `test_health_probe_not_blocked` | M-6 |
| 1 `test_gazetteer_packaging` | D-4 |
| 1 `test_licensing::test_readme_and_docs_state_the_licence` | D-6 |
| 5 unit + 2 integration cases reading `docs/` | **not a fix** — those documents exist in this working tree but are not committed (D-7); a fresh clone still fails them |

Part A's extra 18 test cases at HEAD are the round-5 regression tests
(`test_batch_import_accounting`, `test_health_probe_not_blocked`,
`test_identifiers_overlap_merge`, `test_temporal_overlap_spans`,
`test_scenario_imminent_window`, `test_outage_auth_reason`).

---

## 4. The failing cases, classified

66 cases (55 failures + 11 errors). Zero `PROJECT-DEFECT`. Generated table:
`audit_report/findings/failure_triage.csv`; per-case messages are in it verbatim.

| file | cases | category | decision | cause |
| --- | --- | --- | --- | --- |
| `tests/unit/test_interface_docs.py` | 17 | DOCS-NOT-COMMITTED | D-7 | `docs/INTERFACE_REGISTRY.md`, `REGISTRY_EVIDENCE.md`, `endpoint_inventory.json` are generated and uncommitted |
| `tests/unit/test_component_library.py` | 3 | DOCS-NOT-COMMITTED | D-7 | `docs/COMPONENT_LIBRARY.md` uncommitted |
| `tests/unit/test_action_lifecycle_components.py` | 2 | DOCS-NOT-COMMITTED | D-7 | `docs/COMPONENT_LIBRARY.md` |
| `tests/unit/test_action_surface_audit.py` | 2 | DOCS-NOT-COMMITTED | D-7 | `docs/ACTION_SURFACE_AUDIT.md` |
| `tests/unit/test_architecture_diagrams.py` | 2 | DOCS-NOT-COMMITTED | D-7 | `docs/ARCHITECTURE.md` |
| `tests/unit/test_experience_contract.py` | 2 | DOCS-NOT-COMMITTED | D-7 | `docs/EXPERIENCE_CONTRACT.md` |
| `tests/unit/test_interface_lifecycle.py` | 2 | DOCS-NOT-COMMITTED | D-7 | `docs/INTERFACE_REGISTRY.md` |
| `tests/unit/test_ocr_provenance_docs.py` | 2 | DOCS-NOT-COMMITTED | D-7 | `docs/DOMAIN_MODEL.md` |
| `tests/unit/test_screen_inspector.py` | 2 | DOCS-NOT-COMMITTED | D-7 | `docs/SCREEN_INSPECTOR_EVIDENCE.md` |
| `tests/integration/test_interface_coverage.py` | 2 | DOCS-NOT-COMMITTED | D-7 | same generated set, integration side |
| `tests/unit/test_reference_docs.py` | 1 | DOCS-NOT-COMMITTED | D-7 | generated reference pages are stale |
| `tests/unit/test_windows_offline_kit.py` | 1 | DOCS-NOT-COMMITTED | D-7 | `docs/windows/DEPENDENCY_INVENTORY.md` |
| `tests/unit/test_licensing.py` | 4 | NEEDS-DECISION | D-6 | `THIRD_PARTY_NOTICES.md` absent (2); `pymupdf-layout` / `pymupdf4llm` declare no usable licence metadata (2) |
| `tests/integration/test_title_parent_linkage.py` | 4 | NEEDS-DECISION | D-4 | do-not-edit; the test inserts 5 positional args into a repository that takes 4 |
| `tests/integration/test_translation_coverage.py` | 4 | NEEDS-DECISION | — | 284–359 untranslated/fuzzy entries per locale (ar/he/fa/hr); needs a translator |
| `tests/integration/test_places_crud_pg.py` | 3 | NEEDS-DECISION | D-4 | do-not-edit; `place_key` naming and a 500 in the admin curation path |
| `tests/unit/test_bandit_triage_fixes.py` | 2 | NEEDS-DECISION | D-5 | imports `core.reporting.model` |
| `tests/integration/test_signal_explorer_pg.py` | 2 | NEEDS-DECISION | D-4 | do-not-edit; the explorer returns no rows for the seeded fixture |
| `tests/unit/test_identifiers_intel.py` | 2 | NEEDS-DECISION | D-4 | do-not-edit; email identifiers reported under a different key |
| `tests/unit/test_analytics_measures.py` | 1 | NEEDS-DECISION | D-5 | imports `core.reporting.datasets` |
| `tests/unit/test_component_library.py` | 1 | NEEDS-DECISION | — | hand-written table count is 11, the document says 9 |
| `tests/unit/test_notification_volume_guards.py` | 1 | NEEDS-DECISION | D-10 | demands an `m0014` alerts-index migration the frozen chain does not have; reverted to `2670f3b` |
| `tests/integration/test_notification_accuracy.py` | 1 | NEEDS-DECISION | D-10 | `test_alert_indexes_exist` expects `idx_alerts_*` names from a migration this chain does not have |
| `tests/integration/test_places_pg.py` | 2 | COLLATERAL | D-4 | passes 14/14 **in isolation** on both `04bb817` and HEAD; fails only inside the full run |
| `tests/unit/test_archive_formats.py` | 1 | ENV | — | `pyzipper` (declared test-only dependency) is not installed in this rebuilt venv |

The 29 do-not-edit cases are visible, not hidden, and none of those files was
edited. `test_places_pg` is the one ordering artefact: it is the same on both
trees, so it is pre-existing, and it is recorded as `COLLATERAL` rather than
papered over by touching the schema.

---

## 5. Untracked `docs/`, and what that does to the numbers

`docs/` is untracked by design (D-7, waiting for your review). It exists
partially in this working tree, which lets five unit tests and two integration
tests pass here that a fresh clone would fail. Those seven cases are marked
"not a fix" in §3. Generated `docs/`, translations and licence text were **not**
committed in round 5.

---

## 6. Inventories

Eleven generated inventories plus the runtime probe, 11 244 rows, every row with a
verdict, **zero `UNTOUCHED`** (`audit_report/inventory/`, `verdict_summary.json`):

| verdict | rows |
| --- | --- |
| VERIFIED-OK | 6 924 |
| NEEDS-DECISION | 3 708 |
| DEFECT-OPEN | 589 |
| ENV-BLOCKED | 14 |
| FIXED+TEST | 5 |
| DEAD-CODE | 4 |
| UNTOUCHED | **0** |

| inventory | rows | non-OK verdicts |
| --- | --- | --- |
| `i18n_msgids.csv` | 7 141 | 3 708 NEEDS-DECISION (catalog entry with no static use), 564 DEFECT-OPEN (missing in ≥1 catalog) |
| `sql.csv` | 2 377 | — |
| `routes.csv` | 485 | 3 FIXED+TEST, 14 ENV-BLOCKED |
| `modules.csv` | 425 | 2 DEAD-CODE |
| `routes_runtime.csv` | 342 | — |
| `js_modules.csv` | 178 | — |
| `templates.csv` | 79 | 1 DEAD-CODE |
| `env_vars.csv` | 68 | 25 DEFECT-OPEN (read by code, absent from the documentation) |
| `css.csv` | 45 | 1 DEAD-CODE |
| `schema.csv` | 40 | — |
| `interfaces.csv` | 35 | 2 FIXED+TEST |
| `jobs.csv` | 29 | — |

The 589 DEFECT-OPEN rows are the i18n gaps (564) and the undocumented environment
variables (25) — both are content decisions carried by D-6/translation, not code
defects. No row is left unreached; the per-row text is in the CSVs.

---

## 7. D-5 is blocked, and this is why

The decision said "build the thin facade over `services/reporting`". There is
nothing to wrap:

* `services/reporting/` holds `processing.py` and `ingestion_batch.py`; there is no
  registry, no `runs` module, no dataset definitions.
* The callers need more than ids. `tools/perf/keyness_perf.py` needs
  `REGISTRY.report("term_keyness")` with `normalize_parameters()`, per-dataset
  `.bind(values, scope)` returning SQL + bound parameters, `REGISTRY.dataset(key)`,
  `REGISTRY.translation_keys()` / `.translation_plurals()`, **and**
  `services.reporting.runs.submit_run/execute_run/get_run`.
* `tests/unit/test_analytics_measures.py` asserts
  `float(KEYNESS_SIGNIFICANT_G2) == thresholds.LL_P0001.value` **and** that
  `">= 15.13" in TERM_KEYNESS_TOTALS_V1.sql`, i.e. it requires the keyness dataset
  statement itself.
* That statement does not exist anywhere in this repository and never has:
  `git log --all --oneline -- core/reporting` and `-- services/reporting/runs.py`
  are both empty.

So "the facade" is not a rename: it means writing the keyness dataset SQL, the
report registry and the run engine — new product code with no source to copy and
no consumer other than two tests and two audit tools. Under the rule that nothing
is written just to make a test green, I stopped and am asking, rather than
inventing SQL and then certifying it with my own assertion.

Options, cheapest first:

1. **Leave D-5 open** (what I did). 3 cases stay red, honestly attributed.
2. **Declaration-only facade**: `core.reporting` with the registry constants,
   dataset ids and the anchored `_ID` / `_HELP_TOPIC` validators, no SQL. Clears
   the 2 `test_bandit_triage_fixes` cases; `test_analytics_measures` still fails
   (no statement to point at) — and it adds a module no product code uses.
3. **Build the reporting layer for real**: keyness SQL over `words_hashs`,
   verified against a measured corpus with `EXPLAIN ANALYZE`, plus the run engine.
   That is a project, not a round-5 item, and it belongs in a schema-free
   follow-up.

---

## 8. Still yours to decide (nothing below is done silently)

| # | what | what it costs |
| --- | --- | --- |
| D-7 | commit generated `docs/` — 38 red cases depend on it | publishing documents you have not read; `SECURITY.md`, `CONFIGURATION.md`, `DEVELOPMENT.md` need your review first, `DATABASE_SCHEMA.md` regenerates from the frozen chain (`--check` exit 0) |
| D-6 | `THIRD_PARTY_NOTICES.md` + the two PDF packages' licence metadata — 4 red cases | writing notices is a legal review of every vendored asset; both remain listed OPEN |
| D-5 | see §7 | option 1 now; 2 or 3 on your word |
| translations | 4 red cases, 564 inventory rows | needs a translator; machine translation would turn the test green and degrade the product |
| alert indexes | 2 red cases (`test_alert_indexes_exist`, `test_notification_volume_guards`) | either the index set is a requirement (a schema change you would have to approve) or the expectation goes |
| D-4 do-not-edit cluster | 11 red cases (`title_parent_linkage` 4, `places_crud_pg` 3, `signal_explorer_pg` 2, `identifiers_intel` 2) | these are product/test disagreements I am not allowed to edit my way out of |
| `test_places_pg` ordering | 2 red cases in the full run only | fix by test isolation (per-module database or fixture reset), never by the schema |

## 9. Unverifiable here, and why

| thing | why it cannot be verified in this environment |
| --- | --- |
| OCR of the 29 `ENV-LIMIT` cases | no Tesseract/OCR runtime, no sample corpus in the checkout |
| `pyzipper` AES-ZIP path | the package is not installed in the rebuilt venv (declared test-only dependency) |
| Windows offline kit | no Windows host; `docs/windows/DEPENDENCY_INVENTORY.md` is generated and uncommitted |
| translations (564 rows) | no translator; I do not machine-translate legal/intel text |
| `pymupdf-layout` licence | the installed metadata declares no licence field — nothing to read, so nothing recorded beyond "unrecognised" |
| ingestion of an 8 MB document | round 4 measured no row in 300 s; the post-fix 2 MB figure (25 s) was not extrapolated to 8 MB and the 8 MB case was not re-run |

---

## 10. Where this stands

* 0 new failures; 89 → 55 failures (11 errors unchanged, all `ENV`/`DOCS`).
* 0 `PROJECT-DEFECT` rows in the triage table.
* `database/migrations` untouched; no do-not-edit test edited except the D-1
  helper you granted.
* Commits: `203735f` M-1 · `9fa21ac` M-6 · `8dcdecf` M-7 · `55354a4` D-1 ·
  `ef2e427` imminent window · `04c8034` `3f33a7f` `7eebed6` M-3 · `33aa680` M-2 ·
  `5703888` D-6 · `14a990c` D-2 · `86c8d27` D-4 · `fcc029f` `c621894` D-8/D-3 ·
  `987edc4` M-6 (2/2) · `da88926` machine paths.

I am stopping here for your word on D-5, D-7 and D-6.
