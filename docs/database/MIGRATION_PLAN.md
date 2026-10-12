# Migration plan and record (deliverable F)

**Status: executed and verified on disposable databases. Not yet applied to any
operator database.** m0038 and m0039 exist in `database/migrations/`, apply
cleanly in sequence on a fresh bootstrap (39 migrations total), and are covered
by integration tests. Applying them to a real deployment is the operator's
call; this document is the runbook for that.

The ordering below follows the execution: the duplication removal (DB-1/DB-2)
was the first task, so it took the next free version, 0038; the vocabulary
constraints (DB-7/DB-8) became 0039. Both are independent - each can be applied
alone.

Migrations follow the repository's own conventions: one module per change under
`database/migrations/`, `version` / `name` / `upgrade` / `downgrade`, idempotent
statements (`IF EXISTS` / `IF NOT EXISTS`), applied by
`database/migration_runner.py` (each migration in its own transaction, recorded
in `schema_migrations`).

---

## Step 0 - preconditions (before touching a real database)

1. **Back up** the target (`pg_dump -Fc`). The removals change schema objects;
   the downgrade restores them, but the backup is what makes that statement
   safe.
2. **Record the integrity state first**, so the change can be compared:
   `python3 tools/db/integrity_audit.py --json > integrity_before.json`
   (read-only; exits 1 when it finds anything, which is expected on a live
   database with anything to reconcile).
3. **Prove the target schema is the one the migrations define**: apply the
   migration chain to a copy or a scratch database and compare
   `information_schema` counts with `INVENTORY.md` (51 tables / 1 view / 490
   columns / 254 constraints / 179 indexes after m0038+m0039). A schema that
   does not match means a hand-edited database, and the shape guards below will
   refuse - which is the intended behaviour.
4. **Decide DB-4 and DB-6** (the `alerts` snapshot columns and the stale dump).
   Neither blocks m0038/m0039.

## Step 1 - m0038 `redundant_enforcement_removal` (DB-1, DB-2) - applied

Removes nine exact duplicates: one redundant UNIQUE constraint on
`hash_contexts` (DB-1) and eight redundant indexes that duplicate a surviving
index or a UNIQUE constraint's index (DB-2). The full pair table with the origin
of each duplicate is in `DUPLICATION_REGISTER.md` (DB-1, DB-2).

**Guard, in the migration itself.** Before dropping anything it reads
`pg_constraint` + `pg_indexes` and requires every survivor to be present with
the exact expected shape (`_EXPECTED_SHAPES`), raising with the object named
otherwise. A drifted database therefore refuses the migration rather than
dropping the last enforcement of an invariant. Verified by
`test_the_migration_refuses_to_drop_when_the_survivor_is_gone`, which drops a
survivor inside the test transaction and asserts the refusal.

**No data is touched.** Only `DROP INDEX` / `ALTER TABLE ... DROP CONSTRAINT`.

**`DROP INDEX CONCURRENTLY` is not usable inside the migration**: the runner
wraps each migration in a transaction and `CONCURRENTLY` cannot run in a
transaction block. For a zero-lock deploy, run the nine statements by hand with
`CONCURRENTLY` first, then apply the migration: `IF EXISTS` makes it a recorded
no-op and the guards still pass because the survivors are untouched. On a
database small enough for a brief `ACCESS EXCLUSIVE` lock, applying the
migration as-is is fine.

**`downgrade()` recreates all nine** from the verbatim original DDL captured in
`_RESTORE`, so the schema can be returned to the measured pre-m0038 state. It is
a schema revert, not a data revert (nothing deleted data).

**Verification performed** (all on freshly bootstrapped databases):

| Check | Result |
| --- | --- |
| All 39 migrations apply on an empty database | pass |
| The nine dropped objects are gone, the nine survivors remain | pass |
| `pg_indexes` shape grouping finds 0 duplicate shapes | pass (was 9) |
| Uniqueness still rejects duplicates on `hashs(hash)`, `hash_contexts(hash_id, source_id, side_id)`, `words(word)`, `punctuation(punctuation_text)`, `analyst_categories(name)` | pass |
| `downgrade()` restores all nine; `upgrade()` removes them again | pass |
| Schema reference regenerated; `tools/docs/generate_schema.py --check` clean | pass |

## Step 2 - m0039 `vocabulary_constraints` (DB-7, DB-8) - applied

Adds four CHECK constraints, each **generated at migration time** from the
module that defines the values - never copied into SQL:

| Column | Constraint | Source | Values |
| --- | --- | --- | --- |
| `alerts.type` | `ck_alerts_type` | `NotificationType` | 12 |
| `alerts.priority` | `ck_alerts_priority` | `NotificationPriority` | 4 |
| `jobs.status` | `ck_jobs_status` | `job_state.ALL_STATES` | 8 |
| `job_events.event_type` | `ck_job_events_event_type` | `job_state.EVENT_TYPES` | 21 |

**Ordering defect fixed first, in code.** `job_state.EVENT_TYPES` listed 18
values and was missing `PROGRESS`, `JOB_PAUSED` and `FAILED`, all of which
`services/jobs/manager.py` publishes (`_publish` at 165/239/267/350/355/359,
`_finish` at 432). A CHECK built on the old tuple would have rejected the job
manager's own events. The tuple was corrected to 21 and
`tests/unit/test_job_event_vocabulary.py` now derives the emitted set from the
writer call sites, so the two cannot drift again (4 tests; deleting `PROGRESS`
fails two of them).

**Added safely.** Each constraint is `ADD CONSTRAINT ... NOT VALID` followed by
`VALIDATE CONSTRAINT` in the same transaction: adding does not scan the table,
validating does not block writes, and the final state enforces the rule for
every row (all four report `convalidated = true`). This mirrors the pattern the
repository already uses for constraints with a migration cost.

**Pre-flight, in the migration.** Before adding each constraint it counts
existing rows outside the vocabulary and, if any exist, raises naming the
offending values - a drifted deployment stops with a readable message and no
change instead of a bare `CheckViolation` mid-DDL. `tests/integration/
test_vocabulary_constraints.py` proves the refusal path by dropping a
constraint, inserting a violating row and asserting the `RuntimeError`.

**No data is touched.** Only `ALTER TABLE ... ADD/DROP CONSTRAINT`.

**Downgrade** drops the four constraints, restoring the previous behaviour.

**Verification performed:**

| Check | Result |
| --- | --- |
| Fresh bootstrap applies m0039 after m0038 | pass (39 migrations) |
| All four constraints exist and are validated | pass |
| An out-of-vocabulary value is rejected, naming the constraint | pass (status, alert type, alert priority, event type) |
| Every value the code defines is accepted (all 12 alert types, all 8 states, all 21 event types) | pass |
| The constraints' allowed sets equal the code's sets | pass (compared against `pg_get_constraintdef`) |
| The audit tool reports no vocabulary findings on a clean database | pass |
| The audit still *detects* an out-of-vocabulary value (constraint dropped, row inserted) | pass |

## Step 3 - decisions that are NOT migrations yet

* **DB-4** (`alerts.file_name`/`file_path` copying `paths`): needs an owner
  decision on semantics. If the answer is "read through `paths`", that is a code
  change plus a migration dropping the columns; if it is "as-of snapshot", the
  change is documentation only. Written once and never updated, and
  `alerts.file_id` is `ON DELETE CASCADE`, so the copy cannot outlive its
  source.
* **DB-5** (five `job_id` provenance columns without a FK): first measure
  values that match no `jobs` row (`tools/db/integrity_audit.py` reports it).
  Then "add `ON DELETE SET NULL` FKs" needs those rows reconciled or the
  constraint added `NOT VALID`; "provenance strings are fine" needs a
  `CHECK (job_id IS NULL OR job_id <> '')` and documentation. Retention prunes
  jobs, so a cascading FK would delete evaluation history - this must stay a
  deliberate decision.
* **DB-6** (`database/SYLTHARAE.sql`): no migration. Either regenerate it from a
  migrated database as a release step and document in `docs/DATABASE.md` that
  migrations are the authority, or delete it. Deleting needs approval;
  regenerating is additive. Note its index set is already two migrations stale
  (it lacks the m0035/m0036 `words_hashs` indexes), so it cannot be used to
  verify the intended index set.
* **Retiring `path_geo_mentions_m0015`**: only after the operator confirms every
  hash has a places run. Measured how:
  `SELECT count(*) FROM hashs h WHERE NOT EXISTS (SELECT 1 FROM content_signal_runs r WHERE r.hash_id = h.id AND r.detector = 'places')`.
  While that count is non-zero the table is the only source for those rows and
  must stay. Not deleted on static-scan evidence.

## Order of execution (one release window)

| # | Action | Reversible | Needs approval |
| --- | --- | --- | --- |
| 1 | backup + `integrity_before.json` + precondition counts | n/a | no |
| 2 | pre-flight vocabulary queries (step 2) | n/a | no |
| 3 | apply **m0039** (additive vocabulary constraints) | yes (drop constraints) | **yes** |
| 4 | pre-flight shape query + optional manual `DROP INDEX CONCURRENTLY` | yes | **yes** |
| 5 | apply **m0038** (removals) | yes (`downgrade()` recreates all nine) | **yes** |
| 6 | coupled code updates are already in the tree (`verify_readiness.py`, audit tool, tests) | yes | **yes** |
| 7 | regenerate `docs/reference/DATABASE_SCHEMA.md`, update register/report docs | yes | no |
| 8 | DB-4 / DB-5 / DB-6 decisions | depends | **yes** |

Applying the additive migration first is the safer order on a live system even
though the removals were implemented first.

Not in this plan on purpose: no table merges, no table drops, no column type
changes, no data deletion, no new tables, no ORM. The audit found no duplication
that requires any of those.
