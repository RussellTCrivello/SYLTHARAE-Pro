# Repair report (deliverable G)

What was repaired, how it was proven, and what was deliberately left alone.
Three code/artifact repairs came out of the database audit and three schema
repairs followed from it; every one is covered by a test that fails without it.

## Repair 1 (DB-9) - the ingestion batch report read a table that no longer exists

**File**: `services/reporting/ingestion_batch.py`, function `_query_categories`.

**Defect.** The query joined `words_paths wp` and filtered on `wp.path_id`.
m0011 (`content_identity`) replaced the path-keyed word store with the
content-keyed `words_hashs` (keyed by `hash_id`), so the relation does not exist
in the migrated schema. The caller wrapped the query in a try/except that logged
"Batch report query failed: categories" and continued, so the only visible
symptom was a permanently empty "Categories assigned" section of the batch
report - no error page, no failed job, no log the operator reads.

**Proof it was dead.** `services/reporting/ingestion_batch.py::_query_categories`
executed against a database built by `database/bootstrap.py`:

    psycopg2.errors.UndefinedTable: relation "words_paths" does not exist

**Root cause.** A rename (m0011) that updated the write paths but not this read
path. Not a schema defect: the schema is the intended one and the query was the
stale artefact.

**Repair.** The query now walks the path that exists:
`paths -> hash_contexts -> words_hashs -> words_categorys -> categorys`, and
counts the categories of the selected paths. No new table, no new view, no
schema change; the report's contract (a `categories` list on the document) is
unchanged.

**Regression protection**:
`tests/integration/test_ingestion_batch_categories.py` - two tests:
`_query_categories` called directly with a seeded corpus (path + context +
content + words + category), and the full `document_from_parts` path asserting
the category arrives in the rendered report document. Both run against a real
PostgreSQL built by the project's migrations, not a stub. Verified: 3 passed
(the third test is Repair 2's).

## Repair 2 (DB-3) - place mentions were read from the legacy table

**File**: `services/reporting/ingestion_batch.py`, function `_query_places`.

**Defect.** The query selected from `path_geo_mentions_m0015` directly. m0019
renamed the old table to that name and created `path_geo_mentions` as a view
whose stated job is to union the signal-derived places with the preserved m0015
rows **for content with no non-failed places run**. Reading the table bypassed that
rule: the report could show legacy rows that the rest of the application (which
reads the view) deliberately hides, so the same place appeared differently in
two parts of the product.

**Proof.** The view definition (m0019, reproduced in `database/SYLTHARAE.sql`)
has two rules the report's query bypassed: its signal branch keeps only
`confidence IN ('high','medium')` identified places, and its legacy branch emits
m0015 rows only `WHERE NOT EXISTS (... content_signal_runs ... detector =
'places' ... status <> 'failed')`. The old query had neither rule - it read raw
legacy rows regardless of coverage or confidence. Additionally, after the repair a repository
scan shows **no application reader of `path_geo_mentions_m0015` at all** - the
only remaining references are inside m0019 itself (its `RENAME` and its
downgrade), which is what "one access path" should look like.

**Repair.** The query reads the `path_geo_mentions` view; the docstring records
why so the next reader does not "optimise" back to the table.

**Regression protection**:
`tests/integration/test_ingestion_batch_categories.py::test_places_come_through_the_view_not_the_legacy_table`
inserts a row into the legacy table and asserts it reaches `_query_places`
**through the view**. A future switch back to the table name would still pass a
naive test (the table has the row) - so the test asserts the view's semantics by
seeding through the legacy table and reading the view's output columns
(`place`, `file_count`, `mentions`), which only exist in the view's shape.

## Repair 3 (tooling) - `--json` output was not valid JSON

**File**: `tools/db/integrity_audit.py` (the read-only audit tool written for
this audit).

**Defect.** With `--json`, the tool printed the JSON document **and then** a
closing status line (`no findings`) to stdout, so the documented usage
`python3 tools/db/integrity_audit.py --json > integrity.json` produced a file no
JSON parser accepts (`Extra data: line 886 column 1`). Found while verifying this
report: a verification script that parsed the output silently fell back to an
empty object and reported "0 findings" for a database with nine registered
redundancies - the exact failure mode the tool exists to prevent.

**Repair.** With `--json`, the closing status line goes to stderr; stdout is the
document. The human-readable and `--counts` modes are unchanged (stdout).

**Also added in the same pass**: the `redundant_indexes` group (the nine
registered shapes, informational, excluded from the exit status so a clean
database still exits 0) - a tripwire for a *new* duplicate shape and the check
that the pre-flight gate query in `MIGRATION_PLAN.md` actually returns rows.

**Verification** (fresh disposable PostgreSQL built by `database/bootstrap.py`):

| Check | Result |
| --- | --- |
| `tools/db/integrity_audit.py --json` parses as JSON | yes - the process now exits 0 on a clean migrated database and the status line is on stderr |
| `redundant_indexes` on that database | **9 rows before m0038, 0 after** - exactly the shapes in DB-2 |
| injected violation (`INSERT INTO jobs ... status = 'nope'`) | exit 1, finding: `vocabulary jobs.status count=1 allowed=8` |
| `not_valid` constraints on the fresh database | 0 |
| these contracts under test | `tests/integration/test_db_integrity_audit.py`, 5 tests, all passing |

## Repair 4 (DB-1, DB-2) - duplicate enforcement removed by m0038

**Files**: `database/migrations/m0038_redundant_enforcement_removal.py` (new),
`tests/integration/test_redundant_enforcement_removal.py` (new),
`verify_readiness.py`, `tests/integration/test_db_integrity_audit.py`,
`docs/reference/DATABASE_SCHEMA.md` (regenerated).

**What was wrong.** `hash_contexts` enforced its uniqueness twice (m0011's
`uq_hash_contexts_identity` and m0013's `uq_hash_contexts_hash_source_side`, the
same three columns), and eight indexes duplicated a surviving index or the index
behind a UNIQUE constraint - every one maintained on every write. The pair table
is in `DUPLICATION_REGISTER.md` (DB-1, DB-2).

**Why it is safe.** In each pair both objects are `btree` over the same columns
in the same order, with no predicate, no expression and the default operator
class, so the duplicate answers no query the survivor cannot. The survivor is
kept in every case. No code names any of the nine in DDL or in
`ON CONFLICT ON CONSTRAINT` (searched); `dedup_service` uses column inference
(`ON CONFLICT (hash_id, source_id, side_id)`), which resolves against the
surviving constraint. `paths.context_id` references `hash_contexts(id)`, the
primary key, so no dependent object moved.

**Proof.** `tests/integration/test_redundant_enforcement_removal.py`, 5 tests:
the nine are gone and the nine survivors remain; the schema has no duplicate
index shape; uniqueness still rejects duplicates on five tables; `downgrade()`
recreates all nine and `upgrade()` removes them again; and the migration refuses
to run when a survivor has been removed. The migration's own guard compares each
survivor against the expected shape before dropping anything.

**Regression risk and rollback.** Only indexes and one duplicate constraint are
dropped; no data. `downgrade()` restores the exact pre-m0038 schema.

## Repair 5 (DB-7, DB-8) - vocabularies enforced by m0039

**Files**: `database/migrations/m0039_vocabulary_constraints.py` (new),
`tests/integration/test_vocabulary_constraints.py` (new),
`services/jobs/job_state.py`, `tests/unit/test_job_event_vocabulary.py` (new),
`docs/reference/DATABASE_SCHEMA.md` (regenerated).

**What was wrong.** Four columns accepted any text while the application only
understands a fixed set: `alerts.type` (12 values in `NotificationType`),
`alerts.priority` (4 in `NotificationPriority`), `jobs.status` (8 in
`job_state.ALL_STATES`) and `job_events.event_type` (`job_state.EVENT_TYPES`).
A value outside the set is stored silently and then never matches a filter, so
the record disappears from the view meant to show it.

**The ordering defect found first.** `EVENT_TYPES` itself was incomplete: 18 of
the 21 values the application emits. `services/jobs/manager.py` publishes
`PROGRESS`, `JOB_PAUSED` and the terminal status as event types (`_publish` at
165/239/267/350/355/359, `_finish` at 432), and
`tests/integration/test_retention_pg.py:113` writes `'PROGRESS'` in SQL. Adding
the CHECK first would have rejected the job manager's own events. The tuple was
completed first, and `tests/unit/test_job_event_vocabulary.py` (4 tests) now
derives the emitted set from the writer call sites so the two cannot drift
apart again - deleting `PROGRESS` fails two of those tests (mutation-checked).

**Proof.** `tests/integration/test_vocabulary_constraints.py`, 5 tests: all four
constraints exist and are validated; their allowed sets equal the sets the code
defines (read back from `pg_get_constraintdef`); an out-of-vocabulary value is
rejected naming the constraint; every value the code defines is accepted; and a
violating row makes the migration refuse with the value named instead of failing
obscurely. The pre-flight query in the migration is the same count the audit
tool performs.

**Regression risk and rollback.** Additive; `downgrade()` drops the four
constraints. The only writer that could produce an out-of-vocabulary value is
the unreachable legacy path in DB-10.

## Repair 6 - a test left the shared session database without the canonical constraint

**File**: `tests/unit/test_relationship_deduplication.py`.

**What was wrong (reproduced, not theorised).** The module simulates the
pre-m0013 world by dropping `hash_contexts`' uniqueness, then replays m0013's
`upgrade()` to prove its consolidation logic. m0013 is a historical migration
and re-creates **its own** constraint name
(`uq_hash_contexts_hash_source_side`) - the one m0038 has since removed. So the
cleanup left the session database (one database per pytest session, `pg_db` is
session-scoped) with the canonical `uq_hash_contexts_identity` **missing** and
the retired duplicate back in place: a schema no migration produces. Measured
directly - replaying m0013 on a migrated database yields
`['uq_hash_contexts_hash_source_side']` and no canonical constraint - and it
broke three later tests in the same session:

    FAILED tests/integration/test_bootstrap_migrations.py::test_required_indexes_exist
    FAILED tests/integration/test_redundant_enforcement_removal.py::test_the_duplicate_objects_are_gone_and_the_survivors_remain
    FAILED tests/integration/test_redundant_enforcement_removal.py::test_the_downgrade_restores_and_the_upgrade_removes_again
             (psycopg2.errors.DuplicateTable: relation "uq_hash_contexts_hash_source_side" already exists)

Note that the drift was invisible to the duplicate-shape check - with only one
of the two constraints present there is no duplicate to find - while the
invariant it enforces was being maintained by a name the current schema retired.

**Fix.** `restore_canonical_hash_contexts(conn)`: replay m0013 (the subject of
the test), re-state the canonical constraint, then re-apply m0038's removal -
exactly the sequence a real upgrade performs. Both cleanup blocks use it, and
`test_the_cleanup_restores_the_canonical_constraint` pins it.

**Proof.** The failing combination now passes in the same order (17 passed), and
alone (7 passed).

## Deliberately not repaired (with reasons)

| Finding | Why no repair now |
| --- | --- |
| ~~DB-1 - duplicate unique constraint on `hash_contexts`~~ | **Since repaired** - see Repair 4 (m0038) |
| ~~DB-2 - nine redundant index shapes~~ | **Since repaired** - see Repair 4 (m0038) |
| DB-4 - `alerts` copies file name/path | Both readings ("as-of snapshot" and "stale pointer") are consistent with the code; the choice changes what a notification displays, so it is a product decision |
| DB-5 - unenforced job provenance | The current shape (keep the string after job retention prunes the row) is defensible; adding a cascade FK would delete history |
| DB-6 - stale `database/SYLTHARAE.sql` | Regenerating or deleting a committed artefact is a repo-ownership decision; nothing executes it |
| ~~DB-7 / DB-8 - missing vocabulary CHECKs~~ | **Since repaired** - see Repair 5 (m0039) |
| `path_geo_mentions_m0015` retirement | Requires production data to prove coverage; without a places run for every hash, the table is the only source for those rows |
| Legacy `alerts` repository (`alert_queries.py`, `alerts_repo.py`, `ContentDBService.create_alert`) has no caller | Removing unreachable code is a separate, code-level decision outside a database audit; recorded as DB-10 so it is not mistaken for the live path. Also relevant to DB-7: this dead implementation cannot break the new CHECK constraints |
| `docs/perf/CAPACITY_REPORT.md` naming `idx_words_word` | A measurement record, not a plan: the row is annotated in place (measured at m0036; the index's identical successor `words_word_key` answers the same plan) rather than rewritten, because rewriting a measurement would hide when it was taken |

## What "verified" means in this report

Every claim above was produced by running code against the real schema built by
`database/bootstrap.py` on a disposable directory (not against the repository's
committed SQL file, which contains no data and which this audit proved is stale
in its index list). Test results quoted here are from actual runs in this
session; where a test could not run in this environment that is stated in
`FINAL_INTEGRITY_REPORT.md` rather than glossed over.
