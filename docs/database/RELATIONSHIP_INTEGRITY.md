# Relationship integrity report (deliverable C)

What the migrated schema enforces, what it does not, and what was measured
versus what remains unknown. Everything below was read from a database built by
`database/bootstrap.py` (m0001…m0039) through `information_schema`,
`pg_constraint`, `pg_indexes` and `pg_trigger`, plus a static pass over the code
that reads and writes it.

## Enforced relationships

| Property | Count | Evidence |
| --- | --- | --- |
| Foreign keys | 66 | all `VALID` (`convalidated = true`): no `NOT VALID` constraint anywhere, so stored rows satisfy every FK |
| Primary keys | 48 | 3 tables have none: `words_hashs`, `keywords_hashs`, `words_categorys` — each carries a `UNIQUE` constraint on its real key instead (see "tables without a primary key") |
| Unique constraints | 24 | after m0038 removed the duplicate `hash_contexts` constraint |
| Check constraints | 116 | after m0039 added the four vocabulary checks |
| Triggers | 5 | `trg_scenario_outcomes_append_only`, `trg_report_runs_terminal_immutable`, `trg_report_run_datasets_write_once`, `trg_report_run_analyses_write_once`, `trg_report_artifacts_immutable` |
| Views | 1 | `path_geo_mentions` |

**Deletion behaviour is declared per relationship**, not implied: `CASCADE` where
children cannot outlive the parent (`jobs → job_events`, `paths →
path_revisions`, `report_runs → datasets/analyses/artifacts`, `alerts.file_id →
paths`), `SET NULL` where provenance must survive (`alerts.rule_id`,
`alerts.rule_evaluation_id`, `alerts.scenario_id`,
`alerts.scenario_evaluation_id`, `sources.category_id`,
`path_revisions.changed_by`, `paths.parent_path_id`, `report_artifacts.created_by`),
and `RESTRICT` where a reference must be resolved first
(`content_signal_places.place_id`).

**Cardinality** is expressed with keys rather than convention: one row per
content for derived data (`contents_raw (hash_id, chunk_seq)`,
`words_hashs (hash_id, word_id)`, `keywords_hashs (hash_id, keyword_id)`,
`content_signals (dedup_key)`), one row per (hash, detector) for scans
(`content_signal_runs` PK), and per-run ordered datasets/analyses
(`report_run_datasets`/`report_run_analyses`: PK `(run_id, position)` plus
`UNIQUE (run_id, dataset_key|analysis_key)`).

**Immutability is enforced by triggers, not by discipline.** `report_artifacts`
additionally checks `sha256 = encode(sha256(content),'hex')` and
`byte_size = octet_length(content)`; `report_runs` is immutable once terminal;
datasets/analyses are write-once.

## Exact duplication found and what happened to it

| # | Object | Evidence | Action |
| --- | --- | --- | --- |
| DB-1 | `hash_contexts`: `uq_hash_contexts_identity` **and** `uq_hash_contexts_hash_source_side`, both `UNIQUE (hash_id, source_id, side_id)` | two UNIQUE constraints on the same key list; m0011 created the first, m0013 re-declared it | **resolved by m0038**: dropped `uq_hash_contexts_hash_source_side`; the invariant and the matching name (`uq_hash_contexts_identity`, asserted by `tests/integration/test_bootstrap_migrations.py`) remain |
| DB-2 | 9 index pairs with identical shape (8 plain-vs-unique, 1 plain-vs-plain) | shape extracted from `pg_indexes` with the index name and `UNIQUE` token removed; no predicate, no expression, default operator class in every member | **resolved by m0038**: dropped the redundant member of each pair, kept the enforcing/consistently-named one; `downgrade()` recreates all nine |
| DB-3 | `database/SYLTHARAE.sql` reproduces the schema but is stale | object-by-object comparison: identical table/view/column/constraint-name sets; 2 indexes in the migrations are absent from the dump (`idx_words_hashs_hash_word`, `idx_words_hashs_word_hash` — m0035/m0036) | **open, needs an owner decision** (regenerate from the migrations, or delete). The migrations are the authority either way. |
| DB-4 | `sessions`, `users`, `words`… no duplicate rows found | duplicate scan over every key the schema declares plus the business keys of the association tables | nothing to fix; the probes are in the audit tool |

`tools/db/integrity_audit.py` reports the duplicate-shape condition as
`redundant_indexes`; on a correctly migrated database it is now **empty**, and
`tests/integration/test_db_integrity_audit.py` fails if a new duplicate appears.

## Tables without a primary key

`words_hashs`, `keywords_hashs`, `words_categorys` have no PK. Each has a
`UNIQUE` constraint over its actual key (`(hash_id, word_id)`,
`(hash_id, keyword_id)`, `(word_id, category_id)`), so the invariant is declared;
the difference is only that nothing can point a foreign key at them. Nothing in
the schema does. **Classification: acceptable, intentional**; not changed,
because adding surrogate PKs would alter row identity for no integrity gain.

## Missing integrity rules

| Column(s) | Missing rule | Why it matters | Status |
| --- | --- | --- | --- |
| `alerts.type`, `alerts.priority` | vocabulary CHECK | a value outside `NotificationType`/`NotificationPriority` is stored and then never matches a filter — the notification disappears | **enforced by m0039** (`ck_alerts_type`, `ck_alerts_priority`, generated from the enums) |
| `jobs.status` | vocabulary CHECK | a status outside `ALL_STATES` escapes the terminal-state sweep in the job manager | **enforced by m0039** (`ck_jobs_status`) |
| `job_events.event_type` | vocabulary CHECK | an unknown event type is invisible to any consumer that switches on it | **enforced by m0039** (`ck_job_events_event_type`), after `job_state.EVENT_TYPES` was corrected — it had been missing `PROGRESS`, `JOB_PAUSED` and `FAILED`, so a CHECK built on the old tuple would have rejected the manager's own events |
| `report_artifacts.sha256` | format CHECK (`^[0-9a-f]{64}$`) | the column is `NOT NULL` and paired with `byte_size = octet_length(content)`, so a malformed digest is detectable; nothing checks its shape | **proposed, not applied** (MIGRATION_PLAN step 3) |
| `report_baselines.criteria_hash` | format CHECK | same class, lower impact (`last_max_id` is a watermark) | **recorded** |
| `analyst_file_categories.assigned_by`, `analyst_categorization_log.analyst_id`, `audit_log.user_id` | foreign key to `users` | **deliberately absent**: m0009 says the audit trail must survive user deletion, mirroring `audit_log`; the username is the snapshot | **intentional — do not "fix"** |
| `content_signal_runs.job_id` and the four other `job_id` provenance columns | FK to `jobs` | job retention prunes old jobs; a cascade FK would delete evaluation history, a restrict FK would block retention | **open decision, DB-6** |

### One definition per vocabulary

The four vocabularies exist once. `services/jobs/job_state.py` owns
`ALL_STATES` and `EVENT_TYPES`; `core/monitoring/notification_service.py` owns
`NotificationType` and `NotificationPriority`. Both consumers import them rather
than repeating the lists:

* `database/migrations/m0039_vocabulary_constraints.py` imports the module at
  migration time and builds the CHECK from what it finds, so a value added
  there is enforced by the next constraint refresh and a value removed there
  cannot silently stay legal in the schema;
* `tools/db/integrity_audit.py::VOCABULARY_CHECKS` names the same four sources
  and resolves them at runtime, so the reader and the writer agree by
  construction.

The one gap that mechanism cannot close - a value the *application emits* but
the constant omits - is covered by
`tests/unit/test_job_event_vocabulary.py`, which derives the emitted set from
the writer call sites in `services/jobs/manager.py`. That test is what caught
`EVENT_TYPES` being three values short before the CHECK made it a rejection.

## Orphans and dangling references

All 66 foreign keys are validated and enforced, so the only way an orphan can
exist is if it predates a constraint or was written while one was `NOT VALID`.
Neither state is present in the migrated schema. The audit tool:

* walks **every** FK and counts children whose parent is missing
  (`orphans`), reporting `validated: false` constraints explicitly;
* counts duplicate values for the business keys of 18 tables
  (`duplicate_keys`);
* counts values outside the four vocabularies (`vocabularies`);
* counts NULLs in the columns the application cannot render
  (`required_in_practice`: `analyst_file_categories.assigned_by`,
  `audit_log.user_id` + `username`, `content_signals.confidence`);
* reports duplicate index shapes (`redundant_indexes`, informational).

On a freshly migrated, empty database every count is zero — that is a statement
about the **schema**, not about production data. The tool has been shown to
detect injected violations (an out-of-vocabulary job status, duplicate business
keys, unattributable audit rows), so the checks work; running them against the
deployment database is what converts "unknown" into evidence.

## Referential vs semantic integrity checks

Beyond the mechanical checks, these were verified by reading the code that reads
and writes the data:

* **`words_hashs`/`keywords_hashs` duplicates**: the write path
  (`database/services/dedup_service.py`) inserts with
  `ON CONFLICT (hash_id, word_id) DO UPDATE`, i.e. it relies on the unique
  constraint rather than on application logic. Verified against the migrated
  schema (the `ON CONFLICT` target columns match the constraint).
* **`paths` has no unique on `(context_id, file_path)`**: the same location may
  legitimately occur under different contexts; re-imports are matched by
  `dedup_service.find_occurrence` (content identity + location), not by a
  constraint.
* **`paths.parent_path_id`** is a self-reference with `ON DELETE SET NULL`,
  so deleting a parent does not delete the child hierarchy rows.
* **`content_signals.dedup_key`** is a sha256 with a format CHECK; the unique
  constraint makes re-detection idempotent.
* **`report_run_datasets`** ordering is explicit (`position`) and unique per
  run, so an analysis cannot be replayed out of order.

## What was not verifiable here

Row counts, orphan counts, duplicate-key counts and vocabulary counts on the
**real** database. Also unverifiable without data: whether any index is unused
(needs `pg_stat_user_indexes.idx_scan` from a workload), and whether the nine
removed indexes had any row-level benefit. The commands to close those gaps are
in deliverable A.
