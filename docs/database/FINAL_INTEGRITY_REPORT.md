# Final database integrity report (deliverable H)

Scope: the PostgreSQL schema of SYLTHARAE-Pro as built by
`database/bootstrap.py` (migrations m0001-m0039), its relationship integrity,
its duplication, and the application code paths that read it. The companion
documents are `INVENTORY.md` (A), `RESPONSIBILITY_MATRIX.md` (B),
`RELATIONSHIP_INTEGRITY.md` (C), `DUPLICATION_REGISTER.md` (D),
`CANONICAL_ENTITY_MAP.md` (E), `MIGRATION_PLAN.md` (F), `REPAIR_REPORT.md` (G).

**Nothing destructive was executed against an operator database.** No table or
column was dropped, no data was deleted, no schema object was renamed. The
corrective migrations m0038 and m0039 *were* written and executed - against
disposable databases created for the purpose, and they are covered by
integration tests. Applying them to a deployment database is the operator's
call; `MIGRATION_PLAN.md` is the runbook, revised after execution to match what
the migrations actually do.

## 1. Method and evidence base

| Question | How it was answered |
| --- | --- |
| What does the schema contain? | A disposable PostgreSQL built by `bootstrap_database()`, catalogued through `information_schema`, `pg_constraint`, `pg_indexes`, `pg_trigger`, `pg_proc`; every count is `COUNT(*)`, never a parsed `psql` transcript |
| Does the committed dump match the migrations? | Loaded `database/SYLTHARAE.sql` into a second disposable database (PostgreSQL 18 dump on the project's PostgreSQL 16, with `\restrict`/`\unrestrict` and `SET transaction_timeout` stripped) and compared object *sets*, then every constraint and index *definition* by name (the set comparison alone cannot see a changed value set; the definition comparison reports 33 cosmetic array-rendering differences and 1 real one) |
| Which code uses which table? | Static scan over `*.py`, `*.js`, `*.html`, `*.sql` (excluding the `test-doc/` Tika corpus) |
| Is there duplication? | Index shape grouping, constraint-by-constraint comparison, column-set comparison, and reading the write paths |
| Are there data-level violations? | `tools/db/integrity_audit.py` - every foreign key walked for orphans, `NOT VALID` constraints flagged, duplicate business keys for 18 tables, vocabulary checks for `alerts.type`, `alerts.priority`, `jobs.status`, `job_events.event_type`, required-in-practice checks |

## 2. Verified schema facts (measured, not inherited)

Fresh database, 39 migrations applied, exit 0 (m0038 removes the duplicated
enforcement, m0039 adds the vocabulary constraints):

| Measure | Value |
| --- | --- |
| Base tables / views | 51 / 1 (`path_geo_mentions`) |
| Columns | 490 |
| Constraints | 254 - 48 primary keys, 66 foreign keys, 24 unique, 116 check |
| Indexes | 179 |
| Triggers / functions / sequences | 5 / 5 / 3 |
| Constraints not validated (`NOT VALID`) | 0 |
| Redundant index shapes | **0** (was 9; removed by m0038) |
| Tables without a primary key | 3 (`words_hashs`, `keywords_hashs`, `words_categorys`) - each carries a UNIQUE constraint instead |
| Tables with no code reference | 0 (the lowest, `path_geo_mentions_m0015`, has no *application* reader since DB-3 was repaired - only m0019 itself names it) |

`database/SYLTHARAE.sql` and the migrations produce identical object *sets*
(tables, views, columns, constraint names, triggers, functions, sequences). A
definition-level comparison - added because a constraint can keep its name and
change its value set, which a set comparison cannot see - found exactly three
divergences:

* the dump lacks `idx_words_hashs_hash_word` (m0035) and
  `idx_words_hashs_word_hash` (m0036): 186 indexes against 188, **pre-existing at
  HEAD**;
* 33 of the 34 textually different constraints differ only in PostgreSQL 18's
  array rendering versus PostgreSQL 16's (`ARRAY[('x'::character varying)::text,
  ...]` vs `(ARRAY['x'::character varying, ...])::text[]`) - cosmetic, and a
  trap for anyone diffing the dump as text;
* one is real: `content_signals.ck_content_signals_resolution` allows six values
  in the dump and seven in the current migrations (m0037 adds the identifiers
  detector's `literal`).

The dump contains no data (`--schema-only`, no COPY/INSERT) and nothing in the
repository reads it. That is DB-6: **the migrations are the authority; the dump
is a stale snapshot** - and after m0037 it is stale by one migration more than it
already was.

## 3. Defects found and their disposition

| ID | Defect | Severity | Disposition |
| --- | --- | --- | --- |
| DB-9 | `ingestion_batch._query_categories` read `words_paths` / `wp.path_id`, a table and column that m0011 removed. Every batch report's "Categories assigned" section was silently empty | High - a whole report section was permanently blank and the failure was swallowed by the caller | **Repaired**, 3 tests, `UndefinedTable` reproduced before the fix |
| DB-3 | `ingestion_batch._query_places` read the legacy table `path_geo_mentions_m0015` instead of the `path_geo_mentions` view, bypassing the view's coverage and confidence rules - a second access path to one entity | Medium - the same place could be reported differently in two parts of the product | **Repaired**, covered by a test that seeds through the legacy table and reads the view |
| Tooling | `tools/db/integrity_audit.py --json` appended a status line to stdout, so the documented `--json > file` produced invalid JSON | Medium - the tool that detects problems reported "no findings" to any parser that gave up quietly | **Repaired**; verified parseable, and the tool still detects an injected violation |
| DB-1 | `hash_contexts` had two identical unique constraints (`uq_hash_contexts_identity`, `uq_hash_contexts_hash_source_side`) | Low-medium - write cost, ambiguous conflict target; no data can violate the intent | **Resolved by m0038**, survivor guarded and uniqueness re-tested |
| DB-2 | 9 index shapes duplicated (8 plain-vs-unique, 1 = DB-1) | Low-medium - write amplification on the hot ingestion path | **Resolved by m0038**, `downgrade()` recreates all nine |
| DB-7 | `alerts.type` / `alerts.priority` had no vocabulary CHECK (12 / 4 values defined in code) | Medium - an out-of-vocabulary value becomes an invisible notification | **Enforced by m0039**; constraints generated from the enums |
| DB-8 | `jobs.status` / `job_events.event_type` had no vocabulary CHECK (8 / 21 values defined in code) | Medium - an unknown status escapes the terminal-state sweep | **Enforced by m0039**, after `EVENT_TYPES` was completed from 18 to the 21 the manager actually emits |
| Test isolation | `tests/unit/test_relationship_deduplication.py` left the shared session database without `uq_hash_contexts_identity` and with the retired constraint, silently weakening the invariant for every later test in the session | Medium - three tests failed when the suite was ordered that way; the drift is invisible to a duplicate-shape check | **Repaired** (`restore_canonical_hash_contexts`), pinned by a new test |
| DB-10 | A second alert-creation path (`ContentDBService.create_alert` → `AlertsRepository.insert_alert`) exists with no caller | Low - maintenance risk, not integrity; recorded so it is not mistaken for the live path | **Recorded**, not removed (product decision) |
| DB-4 | `alerts.file_name` / `file_path` copy `paths`, and `alerts.file_id` cascades - the copy cannot outlive its source | Low - either an as-of snapshot (fine) or a stale pointer (a bug); the code does not say | **Needs a product decision**; documented, not changed |
| DB-5 | 5 `job_id` columns hold a value with no FK to `jobs` | Low - provenance is unenforced; adding a cascade FK would delete history | **Needs a decision**; the audit tool reports the real scale on request |
| DB-6 | `database/SYLTHARAE.sql` is a stale, unreferenced schema snapshot | Low-medium - a second definition that answers "what are the indexes" wrongly | **Needs a repo-ownership decision** (regenerate or delete) |

Every "legitimately distinct" pair that looked like duplication (contents vs
contents_raw, sources vs sides, the two taxonomies, the version/evaluation
tables) is recorded with its evidence in `RESPONSIBILITY_MATRIX.md` so the next
audit does not reopen it.

## 4. Verification actually performed (this session)

| Command | Result |
| --- | --- |
| fresh disposable PostgreSQL + `bootstrap_database()` | **39** migrations applied, database created, exit 0 |
| catalog counts on that database | the table in section 2 |
| `python3 tools/db/integrity_audit.py --json` (clean database, after m0038) | exit **0**, valid JSON, **`redundant_indexes: 0`**, zero orphans, zero duplicate keys, zero vocabulary findings, zero unattributable audit rows |
| `python3 tools/db/integrity_audit.py` after injecting `jobs.status = 'nope'` | exit **1**, finding `vocabulary jobs.status count=1 allowed=8` - still, with the CHECK dropped for the probe |
| `pytest tests/integration/test_redundant_enforcement_removal.py` | **5 passed** |
| `pytest tests/integration/test_vocabulary_constraints.py` | **5 passed** |
| `pytest tests/unit/test_job_event_vocabulary.py` | **4 passed** (deleting `PROGRESS` from `EVENT_TYPES` fails 2 of them) |
| `pytest tests/integration/test_db_integrity_audit.py` | **6 passed** |
| `pytest tests/unit/test_relationship_deduplication.py tests/integration/test_bootstrap_migrations.py tests/integration/test_redundant_enforcement_removal.py -q` | **17 passed** - the same order that failed 3 tests before the isolation fix |
| `pytest tests/integration/test_db_integrity_audit.py tests/integration/test_ingestion_batch_categories.py tests/unit/test_relationship_deduplication.py -q` | 14 passed, 0 failed (no FAILED lines, exit 0) |
| `pytest tests/integration/test_bootstrap_migrations.py tests/integration/test_schema_reference.py -q` | 7 passed, 0 failed (no FAILED lines, exit 0) |
| `python3 tools/docs/generate_schema.py` + `--check` on a migrated database | regenerated reference; `--check` exit 0 (clean) after both migrations |
| definition-level dump comparison (every constraint and index of both databases, matched by name) | 0 objects only in the dump; 2 indexes only in the migrations; 34 textually different constraints of which 33 are PostgreSQL 18 vs 16 array rendering and 1 (`ck_content_signals_resolution`) is a real value-set difference |
| pre-flight shape query (`MIGRATION_PLAN.md` 2a) | 9 rows, exactly the registered shapes (shape value `USING btree (...)`) |
| `tests/integration/test_db_integrity_audit.py` (new, 5 tests) | passes - pins the `--json` contract, the clean-database exit code, the absence of unvalidated constraints, the registered redundant shapes (non-fatal) and detection of an injected out-of-vocabulary value |
| `python3 tools/docs/generate_schema.py --check` | **could not run standalone**: needs a database connection and this sandbox has no system PostgreSQL (`Connection refused` on 127.0.0.1:5432). The same generator *is* exercised by `test_schema_reference.py`, which passes against its own disposable server |

## 5. What is NOT verified (explicit limitations)

1. **No live archive was available.** Every data-level check in
   `tools/db/integrity_audit.py` (orphans, duplicate business keys, vocabulary
   drift, unattributable audit rows, the real row counts) ran against a freshly
   migrated, **empty** database. "Zero orphans" there is a statement about the
   schema, not about production data. The checks are implemented and proven to
   fire on injected violations; they must be run against the deployment database
   before the integrity of stored data can be claimed. This is the single
   largest gap in this report.
2. **Performance claims are structural, not measured.** "Redundant index"
   means "identical shape", established from `pg_indexes`. No query plans were
   captured, so the *cost* of the redundancy is inferred (write maintenance)
   rather than measured. Nothing in the plan depends on a measurement of
   benefit that was not taken.
3. **The vocabulary pre-flight result is unknown** for the same reason: whether
   any stored `alerts`/`jobs` row is outside its vocabulary cannot be answered
   without the deployment database. m0039 refuses with the offending values
   listed if there are any, so the check is the migration itself - but the
   answer for the deployment database is not in this report.
4. **DB-4 semantics cannot be settled from code.** Both readings are consistent
   with the implementation; a product decision is required.
5. **No schema change was applied to a deployment database.** m0038 and m0039
   are written and verified - they apply cleanly in sequence on an empty
   database, their guards and refusals are tested, and their effects are
   measured - but "verified on a disposable empty database" is not the same
   claim as "verified on production data", and only the first one is made here.
   The audit's structural checks (shape identity, key lists, guards) transfer
   directly; the data-level checks do not.

## 6. Compliance with the standing constraints

* No table was merged, split or dropped; no data was deleted; no environment was
  reset. The audit was read-only against any real state and used disposable
  databases only.
* No new table, column, ORM, layer or dependency was introduced. The code
  repairs change a query, a vocabulary tuple and a test's cleanup in three
  files.
* Nothing was repaired on the basis of name or column similarity; each finding
  cites the code or catalog evidence that establishes it.
* The two repairs are covered by tests that fail on the old code, and those
  tests exercise a real migrated PostgreSQL, not a stub.
* Pre-existing failures elsewhere in the suite are not claimed as fixed here;
  this report covers the database scope and states exactly what was run.

## 7. Recommended next actions, in order

1. Run `python3 tools/db/integrity_audit.py --json > integrity_before.json`
   against the deployment database and attach it to this report; that converts
   every item in section 5.1 from "unknown" to a measured fact.
2. Decide DB-4, DB-5, DB-6 (three owner decisions, no code needed yet).
3. Approve and execute `MIGRATION_PLAN.md` steps in the documented order
   (m0039 vocabulary constraints first - additive - then m0038's removals) with
   the pre-flight gates; the coupled code changes are already in the tree.
4. Re-run the audit after each step; `redundant_indexes` must read 0 after the
   removal step, which is the tripwire that it was complete.
5. Only after the operator confirms places-run coverage, retire
   `path_geo_mentions_m0015` in a later, separate migration.
