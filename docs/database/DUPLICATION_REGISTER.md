# Duplication register (deliverable D)

Every duplication finding, with the evidence that establishes it, the impact,
what was done, and what still needs a decision. Nothing was removed or merged
without a decision recorded here.

Status legend: **Resolved** = a migration in `database/migrations/` implements
the decision and a test proves the outcome; **Open** = needs a decision or the
operator's database; **Repaired** = a code/artifact defect fixed in place.

Executed migrations: **m0038** `redundant_enforcement_removal` (DB-1, DB-2) and
**m0039** `vocabulary_constraints` (DB-7, DB-8), both verified on freshly
bootstrapped databases - 39 migrations apply cleanly, no `NOT VALID` constraint
remains, and no duplicate index shape exists afterwards.

Cross-references: `INVENTORY.md` (A) for the counts, `RELATIONSHIP_INTEGRITY.md`
(C) for the constraints, `RESPONSIBILITY_MATRIX.md` (B) for what looked like
duplication and is not.

| ID | Kind | Object | Status |
| --- | --- | --- | --- |
| DB-1 | Constraint duplication | `hash_contexts`: two identical unique constraints | **Resolved by m0038** |
| DB-2 | Index duplication | 9 index shapes duplicated (8 plain-vs-unique, 1 covered by DB-1) | **Resolved by m0038** |
| DB-3 | Access-path duplication | place mentions read twice (view + legacy table) | **Repaired** |
| DB-4 | Column duplication | `alerts.file_name` / `alerts.file_path` copy `paths` | Open - needs owner decision |
| DB-5 | Unenforced relation | 5 `job_id` provenance columns have no FK | Open - needs decision |
| DB-6 | Artifact duplication | `database/SYLTHARAE.sql` duplicates the migration DDL | Open - needs decision |
| DB-7 | Missing vocabulary | `alerts.type`, `alerts.priority` | **Enforced by m0039** |
| DB-8 | Missing vocabulary | `jobs.status`, `job_events.event_type` | **Enforced by m0039** |
| DB-9 | Dead SQL | `ingestion_batch._query_categories` read `words_paths` | **Repaired** |
| DB-10 | Dead implementation | second alert-creation path (`ContentDBService.create_alert` → `AlertsRepository.insert_alert`) has no caller | **Recorded** (not removed) |

---

## DB-1 - `hash_contexts` carries two identical unique constraints

**Evidence.** `pg_constraint` on the migrated database:

    uq_hash_contexts_identity           UNIQUE (hash_id, source_id, side_id)
    uq_hash_contexts_hash_source_side   UNIQUE (hash_id, source_id, side_id)

Same columns, same order. m0011 (`content_identity`) created
`uq_hash_contexts_identity` as part of the three-level model; m0013
(`relationship_deduplication`) then merged duplicate rows (its real value) and
created the second constraint under an explicit name - it did not check whether
the invariant was already enforced. Both are backed by separate physical
indexes, so every write to `hash_contexts` maintains both.

**Impact.** Write amplification on every insert/update of the context table, an
extra index that only duplicates work, and an ambiguity for readers: a future
`ON CONFLICT ON CONSTRAINT` has two equally valid targets. No data can violate
the intended invariant - that is precisely why the second copy is redundant.

**Verification that the duplication is real, not apparent.** The duplicate
shape is one of the 9 shapes in `pg_indexes` flagged by
`tools/db/integrity_audit.py`-style shape grouping (see `DB-2`), and no code
names either constraint in an `ON CONFLICT ON CONSTRAINT` clause (searched all
`*.py`). `tests/integration/test_bootstrap_migrations.py` asserts the *survival*
of `uq_hash_contexts_identity`; `verify_readiness.py` asserts the survival of
`uq_hash_contexts_hash_source_side`; `tests/unit/test_relationship_deduplication.py`
drops both to test m0013's consolidation logic. So **both names are currently
pinned by a test or a readiness check** - the constraint cannot be dropped
without also updating those, which is exactly the kind of coupled change that
must be a deliberate decision (see `MIGRATION_PLAN.md`, step 1).

**Action taken (m0038).** `uq_hash_contexts_identity` was kept and
`uq_hash_contexts_hash_source_side` dropped. The decision rests on: the name the
content-identity migration itself uses, the name
`tests/integration/test_bootstrap_migrations.py` asserts, and the absence of any
`ON CONFLICT ON CONSTRAINT` in the codebase (searched) - so no reader depends on
the dropped name. `paths.context_id` references `hash_contexts(id)` (the primary
key), so no dependent object was affected.

**Coupled changes made in the same work set**, because both names were pinned:

* `verify_readiness.py::REQUIRED_INDEXES` now pins `hashs_hash_key` and
  `uq_hash_contexts_identity` (it had pinned the two dropped names);
* `tests/unit/test_relationship_deduplication.py` now restores the canonical
  state after it replays m0013 (`restore_canonical_hash_contexts`) - replaying
  m0013 alone resurrects the retired name and leaves the canonical constraint
  missing, which broke three later tests in the same session (recorded as
  Repair 4 in `REPAIR_REPORT.md`);
* `tests/integration/test_db_integrity_audit.py` registers no accepted duplicate
  shape any longer, and its test is named for that condition.

**Verified.** `tests/integration/test_redundant_enforcement_removal.py` (5 tests)
proves the dropped objects are gone, the survivors are present, every uniqueness
still rejects duplicates (`hashs(hash)`,
`hash_contexts(hash_id, source_id, side_id)`, `words(word)`,
`punctuation(punctuation_text)`, `analyst_categories(name)`), that `downgrade()`
recreates all nine and `upgrade()` removes them again, and that the migration
refuses to drop a survivor that has gone missing.

## DB-2 - nine index shapes are duplicated

Identical shapes per `pg_indexes`; in every pair at least one member is a unique
constraint, so the plain index adds no lookup capability, only write cost.

| Table | Shape | Keep | Drop (redundant) | Origin of the redundant member |
| --- | --- | --- | --- | --- |
| `analyst_categories` | `(name)` | `analyst_categories_name_key` (UNIQUE, inline `UNIQUE NOT NULL`) | `idx_analyst_categories_name` | m0009 explicit `CREATE INDEX` next to the inline constraint |
| `categorys` | `(word_id)` | `categorys_word_id_key` (UNIQUE) | `idx_categorys_word_id` | m0001 |
| `hash_contexts` | `(hash_id, source_id, side_id)` | `uq_hash_contexts_identity` | `uq_hash_contexts_hash_source_side` | DB-1 |
| `hashs` | `(hash)` | `hashs_hash_key` (UNIQUE) | `idx_hashs_hash` | m0001 |
| `keywords_hashs` | `(keyword_id)` | `idx_keywords_hashs_keyword_id` | `idx_keywords_paths_keyword_id` | m0001 (legacy name from before m0011) |
| `punctuation` | `(punctuation_text)` | `punctuation_punctuation_text_key` (UNIQUE) | `idx_punctuation_text` | m0001 |
| `words` | `(word)` | `words_word_key` (UNIQUE) | `idx_words_word` | m0001/m0004 |
| `words_hashs` | `(hash_id, word_id)` | `uq_words_hashs_hash_word` (UNIQUE) | `idx_words_hashs_hash_word` | m0035 (m0036 releases it) |
| `words_hashs` | `(word_id)` | `idx_words_hashs_word_id` | `idx_words_paths_word_id` | m0002 (legacy name) |

**Impact.** Nine index maintenance paths that no query needs. On the largest
tables (`words_hashs`, `hashs`) this is write cost and disk in the hot path of
ingestion.

**Caveat that must be respected.** Two of these are *not* mere accidents:
`idx_words_hashs_hash_word` is the deliverable of m0035/m0036 (the search
inverted-index cover) and the legacy-named `idx_words_paths_word_id` /
`idx_keywords_paths_keyword_id` predate the m0011 rename. Dropping an index that
a migration explicitly created reverses that migration's statement; the
corrective migration must say why the invariant it served is already met by the
unique constraint. Also note that the committed dump lacks the two m0036
indexes, so the dump cannot be used to verify the intended index set (DB-6).

**Action taken (m0038).** One migration drops the nine redundant members (all
shape-identical: no partial predicate, no expression, default operator class),
keeps the enforcing or consistently-named survivor, and recreates all nine in
`downgrade()` from verbatim original DDL. Before dropping anything it checks
that every survivor is present with the exact expected shape and raises with the
object named otherwise - on a drifted schema the drop would remove the only
enforcement of an invariant.

`idx_words_hashs_word_hash` (m0036, `(word_id, hash_id)`) is deliberately
untouched: its column order is the reverse of `uq_words_hashs_hash_word`, so it
answers word-first lookups that the constraint's index cannot.

**Production note.** The migration runs inside the migration runner's
transaction, so `DROP INDEX CONCURRENTLY` (which cannot run in a transaction
block) is not used. For a very large deployment, the operator can instead apply
the same nine statements manually with `CONCURRENTLY` before deploying, and the
migration then finds nothing to drop - its guards are satisfied because the
survivors are untouched.

## DB-3 - the place entity had two access paths (repaired)

**Evidence.** `services/reporting/ingestion_batch.py::_query_places` read
`path_geo_mentions_m0015` **directly**, while m0019 made `path_geo_mentions` a
view whose stated purpose is to union the signal-derived places with the
preserved m0015 rows *for content with no non-failed places run*. Reading the table
skipped that rule and re-surfaced rows the view hides.

**Repair.** The query now reads the `path_geo_mentions` view (docstring explains
why). After the repair, a repository-wide scan shows the only remaining
references to `path_geo_mentions_m0015` are inside m0019 itself (its own
`RENAME`/`downgrade`): the legacy table now has **no application reader**.

**Coverage.** `tests/integration/test_ingestion_batch_categories.py::test_places_come_through_the_view_not_the_legacy_table`
seeds a legacy row and asserts it reaches the report *through the view*.

**Left open.** Whether the legacy table should eventually be retired (after a
places run has covered all content) is a data question for the operator, not a
code repair; recorded in `MIGRATION_PLAN.md` as a non-step.

## DB-4 - `alerts` copies `paths.file_name` / `paths.file_path`

**Evidence.** `core/monitoring/notification_service.py` writes the two columns
when it creates the alert, and the notification list reads them back instead of
joining `paths`. `alerts.file_id` is `ON DELETE CASCADE`, so the copy cannot
outlive its source - the classic justification for a snapshot (survive the
parent) does not apply here.

**Impact.** Two copies of one fact; a path rename (`path_revisions` records
those) leaves alerts showing the old name. That may be desired ("what the file
was called when the alert fired") or a bug ("the notification points at the old
name"). The code does not say which.

**Recommendation.** A decision, not a repair: either (a) declare the copy an
as-of snapshot, document it on the table and keep it, or (b) read the name
through `paths` and drop the two columns. Do not do either without the owner's
answer, because both change what a notification displays.

## DB-5 - job provenance columns are not enforced

**Evidence.** `jobs.job_id` is the primary key (a `uuid4().hex[:12].upper()`
generated in `services/jobs/manager.py`), so it is unique and stable. Five
columns hold that value without a foreign key:

    content_signal_runs.job_id, rule_evaluations.job_id,
    scenario_evaluations.job_id, report_artifacts.job_id,
    job_schedules.last_job_id

`job_events.job_id` *does* have `FOREIGN KEY ... ON DELETE CASCADE`.

**Impact.** A typo or a race produces a provenance value that points at nothing,
and nothing in the database says so. Conversely, adding a plain FK with cascade
would delete analyses/evaluations when job retention prunes the job row -
changing history. The current shape (keep the string) is defensible, but it
should be a decision.

**Recommendation.** Either leave it and add a CHECK that the value is non-empty
(cheap, preserves provenance), or add the FK with `ON DELETE SET NULL` for the
evaluation/artifact columns (provenance survives, but becomes anonymous). Flag
as a decision for the owner; `tools/db/integrity_audit.py` already reports
values that match no `jobs` row so the real scale can be measured before
choosing.

## DB-6 - `database/SYLTHARAE.sql` duplicates the schema without an authority role

**Evidence.** The dump and the migrations produce identical table/view/column/
constraint-name/trigger/function/sequence sets. Definition-level comparison adds
three facts: the dump is missing `idx_words_hashs_hash_word` (m0035) and
`idx_words_hashs_word_hash` (m0036) - 186 indexes against 188; 33 of the 34
textually different constraints differ only in how PostgreSQL 18 versus 16
renders an array membership test (cosmetic); and one differs for real -
`content_signals.ck_content_signals_resolution`, where the dump allows six
values and the current migrations seven (m0037 adds the identifiers detector's
`literal`). The dump contains **no data** (`pg_dump --schema-only`, no
COPY/INSERT) and is referenced by no script, test or document in the
repository. It is PostgreSQL 18 output, so loading it into this project's
PostgreSQL 16 target additionally requires stripping `\restrict`/`\unrestrict`
and `SET transaction_timeout`.

**Impact.** A second, silently stale definition of the schema. Someone will
load it, or read it to answer "what are the indexes", and get a wrong answer -
exactly what happened while preparing this audit (the dump's index set is not
the migrated one).

**Recommendation.** Choose one: (a) regenerate it from a migrated database and
add the regeneration to the documented release step, or (b) delete it and let
the migrations be the only DDL. Either way, do not leave it as-is with no
statement of which is authoritative; `docs/DATABASE.md` currently documents the
bootstrap/upgrade path (migrations), which is the authority the audit verified.

## DB-7 - `alerts.type` and `alerts.priority` have no vocabulary CHECK

**Evidence.** `core/monitoring/notification_service.py` defines
`NotificationType` (12 members) and `NotificationPriority` (4 members); the
`alerts` table has no CHECK on either column, and `Api/routes/notifications.py`
filters and displays by the raw string.

**Impact.** A value outside the vocabulary is stored silently and then never
matches a filter - an invisible notification. `tools/db/integrity_audit.py`
implements the check now (read-only), so the real scale can be measured.

**Action taken (m0039).** `ck_alerts_type` (12 values) and `ck_alerts_priority`
(4 values) were added, both **generated from the enums at migration time**
(`NotificationType`, `NotificationPriority`) rather than copied, each as
`ADD CONSTRAINT ... NOT VALID` followed by `VALIDATE CONSTRAINT` in the same
transaction. Before adding a constraint the migration counts the rows that would
violate it and refuses with the offending values listed, so a drifted deployment
stops with a readable message and no change instead of a bare `CheckViolation`.

The two existing CHECKs on `alerts` (`ck_alerts_rule_addressed`,
`ck_alerts_scenario_addressed`) tie the polymorphic references to a recipient;
this is the missing third piece. The one code path that could write a value
outside the enums is DB-10, which is unreachable.

## DB-8 - `jobs.status` and `job_events.event_type` have no vocabulary CHECK

**Evidence.** `services/jobs/job_state.py` defined `ALL_STATES` (8) and
`EVENT_TYPES` (**18**, incomplete - see below) and enforces transitions in code
(`can_transition`); the columns accept any text. `jobs` is also written by
`content_signal_runs`' `last_job_id`-style provenance and by the schedules
table.

**Impact.** A status outside `ALL_STATES` makes a job invisible to the
terminal-state sweep in the job manager; the client switches on `event_type`
without a default branch for unknown values.

**Ordering defect found while preparing the constraint.** `EVENT_TYPES` was not
the complete set of what the application emits: `services/jobs/manager.py`
publishes `PROGRESS`, `JOB_PAUSED` and the terminal status itself as an event
type (`_publish` at lines 165/239/267/350/355/359 and `_finish` at 432), and
`tests/integration/test_retention_pg.py:113` writes `'PROGRESS'`. A CHECK built
on the old tuple would have **rejected the manager's own events**. The tuple was
therefore corrected to 21 values first, with a new test
(`tests/unit/test_job_event_vocabulary.py`, 4 tests) that derives the emitted
set from the writer call sites - so a new event type added to `manager.py`
without adding it to `EVENT_TYPES` fails, and vice versa. Deleting `PROGRESS`
from the tuple makes two of those tests fail (mutation-checked).

**Action taken (m0039).** `ck_jobs_status` (8 values, from `ALL_STATES`) and
`ck_job_events_event_type` (21 values, from `EVENT_TYPES`) added with the same
`NOT VALID` + `VALIDATE` pattern and the same pre-flight refusal, in the same
migration as DB-7. Both are generated from the constants, so they cannot drift
from the code that writes the columns.

`test_retention_pg.py:113` writes `'PROGRESS'` directly in SQL, so the corrected
vocabulary is what makes that test's data legal as well.

## DB-9 - dead SQL in the ingestion batch report (repaired)

**Evidence.** `_query_categories` joined `words_paths wp` and used `wp.path_id`.
m0011 renamed that table to `words_hashs` and keyed it by `hash_id`. Proven
against a migrated database: `UndefinedTable: relation "words_paths" does not
exist`. The batch report caught the exception and logged it, so the failure was
invisible except as an always-empty "Categories assigned" section.

**Repair.** The query now resolves `path -> hash_context -> words_hashs` and
counts categories through `words_categorys`, which is the only join path that
exists in the migrated schema.

**Coverage.** `tests/integration/test_ingestion_batch_categories.py`, which
seeds a categorised path and asserts the category reaches the rendered report
document (`document_from_parts`), not just the query.

**Note.** This is also why the audit checks dead SQL at all: the failure mode
of a stale join is silence, not an error page.

## DB-10 - a second alert-creation path exists and cannot be reached

**Evidence.** `alerts` has exactly one live writer,
`core/monitoring/notification_service.py`. The `database/` tree also carries a
repository path: `AlertsRepository.insert_alert`
(`database/database/repository/alerts_repo.py`) and
`alert_queries.py::insert_alert`, reached through
`ContentDBService.create_alert` (`database/services/contents_db_service.py`).
Searching every `*.py` for `create_alert(`, `insert_alert(` and
`AlertsRepository(` finds **no caller**: the path is unreachable. Its sibling
read methods (`get_all_alerts`, `get_alert_stats`, `get_recent_alerts`,
`get_alert_by_id`, `mark_alert_read`, ...) are in the same position.

**Impact.** Not data integrity - an unreachable writer cannot write. The risk is
maintenance: the table has two implementations of its access contract, and a
change made in the wrong one looks like it works while nothing calls it. It also
means the alert vocabulary CHECK cannot be broken by this path.

**Classification: dead code, not a schema defect.** Nothing was deleted: the
repository belongs to the legacy `database/` service layer, and removing it is a
product decision about how much legacy surface to keep. Recorded here so the
next reader does not mistake it for the live path - and so that m0039's
`ck_alerts_type` / `ck_alerts_priority` are not blamed for a future caller that
does not exist today.
