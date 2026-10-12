# Responsibility matrix (deliverable B)

Every pair or cluster of tables that could plausibly be considered the "same
thing", analysed as the eight duplication forms. Nothing here was decided from
names or column similarity: each row names the artifact that establishes it.

Measured on a database built by the real migrations (m0001…m0039). Counts:
51 tables, 1 view, 490 columns, 66 foreign keys, 48 primary keys, 24 unique
constraints, 116 check constraints, 179 indexes, 5 triggers.

## The eight duplication forms

| Form | What was found |
| --- | --- |
| **Exact duplication** | 9 index pairs with byte-identical shape; 1 pair of them (hash_contexts) is **two UNIQUE constraints**, i.e. one invariant enforced twice. See DB-1/DB-2. |
| **Entity duplication** | No table duplicates another. The closest candidates are resolved below (contents/contents_raw, path_geo_mentions/…_m0015, categorys/analyst_categories). |
| **Functional duplication** | `alerts` is written by two code paths (live manager + legacy repository). The legacy path has no caller; the schema is not at fault. Recorded in DB-7. |
| **Attribute duplication** | `alerts.file_name`/`file_path` copy `paths`; `analyst_file_categories.assigned_by_username` and `analyst_categorization_log.analyst_username` copy `users.username`. The second set is deliberate (below); the first is a stored snapshot (DB-5). |
| **Relationship duplication** | `paths.context_id` (FK) and `hash_contexts.hash_id` express the content↔occurrence relationship once. No competing path exists. |
| **Lifecycle duplication** | `report_*` tables and `*_versions` tables separate definition/evaluation/outcome deliberately; every stage has its own key and immutability trigger. |
| **Schema-generation duplication** | `database/SYLTHARAE.sql` is a second definition of the same schema, stale by two migrations (DB-3). Everything else is generated from the migrations. |
| **Historical/legacy duplication** | `path_geo_mentions_m0015` is the only legacy copy, and it is still read (through the view) for content the places detector has not covered; `contents.content_data` is the pre-m0010 representation, still read as a fallback. Both are decisions, not accidents. |

## Cluster 1 — `contents` vs `contents_raw` (intentional separation)

* `contents.content_data` is **zlib-compressed, pickled word-ID pairs** — the
  search source (`database/database/queries/content_queries.py`,
  `core/search/*`). It is keyed by `hash_id`.
* `contents_raw.content` is the **verbatim extracted text**, chunked
  (`uq_contents_raw_hash_chunk (hash_id, chunk_seq)`), and is what displays
  (`database/database/repository/contents_repo.py::load_text_content`,
  `Api/routes/files.py`).
* m0010 documents the precedence: readers prefer the raw text and fall back to
  the word-join reconstruction for content ingested before it.
* **Classification: intentional separation** (different fidelity for different
  jobs, one defined fallback). No consolidation. The historical defect — a
  reader taking the wrong store (STAT-01 in `Api/blueprints/files.py`) — is
  already annotated in the code as such.

## Cluster 2 — `path_geo_mentions` (view) vs `path_geo_mentions_m0015` (table) (historical)

* m0019 renames the old table to `_m0015` and creates the view. The view's
  signal branch filters `detector='places'`, `resolution='identified'`,
  `confidence IN ('high','medium')`; the legacy branch emits m0015 rows only
  `WHERE NOT EXISTS` a non-failed places run for that hash.
* The two branches are **mutually exclusive by construction**, so no hash is
  double counted; each row carries `provenance` (`signals` / `legacy_m0015`).
* Consumers read the **view**: `services/reporting/ingestion_batch.py`
  (after this session's repair), `core/reporting/datasets.py`,
  `Api/routes/places.py`.
* **Classification: historical/legacy duplication, intentional.** Retirement
  condition: every hash has a non-failed places run. It cannot be evaluated
  without the operator's database, so the table stays (its retirement is a data
  question, not a schema cleanup).

## Cluster 3 — `categorys`/`words_categorys` vs `analyst_categories`/`analyst_file_categories` (intentional separation)

* The system taxonomy is a *smart* structure whose category **is** a word
  (`categorys.word_id REFERENCES words(id)`, `UNIQUE (word_id)`); membership is
  `words_categorys`.
* The analyst taxonomy is operator-owned: `analyst_categories` (name,
  description, creator), `analyst_file_categories` (path assignment, unique per
  path+category), `analyst_categorization_log` (the append-only trail).
* m0009 states the rule explicitly: the audit trail must survive user deletion,
  which is why `analyst_category_id`-style columns are intentionally FK-free,
  mirroring `audit_log`.
* **Classification: intentional separation.** FR-1.4 requires it; merging them
  would break analyst-label history and the smart taxonomy.

## Cluster 4 — `hash_contexts` uniqueness twice (confirmed accidental duplication)

* m0011 created `uq_hash_contexts_identity UNIQUE (hash_id, source_id, side_id)`
  for the three-level content model.
* m0013 ("relationship deduplication") re-declared the same invariant as
  `uq_hash_contexts_hash_source_side UNIQUE (hash_id, source_id, side_id)` when
  it consolidated duplicate rows. Both are UNIQUE constraints → both maintain a
  physical index on the same keys on every write.
* The dedup logic in m0013 is valuable; the second constraint is not.
* **Classification: confirmed accidental duplication.** Resolved by m0038
  (kept `uq_hash_contexts_identity`). Nothing names either constraint in SQL
  (`ON CONFLICT … DO UPDATE` targets the columns, `ON CONFLICT ON CONSTRAINT`
  appears nowhere), and `paths.context_id` references `hash_contexts(id)` (the
  PK), so the drop cannot affect a dependent object.

## Cluster 5 — duplicate non-unique indexes (confirmed accidental duplication)

Nine pairs, each **`btree`, same columns in the same order, no predicate, no
expression, default operator class** (shape extracted from `pg_indexes`):

| Table | Duplicate shape | Members | Which one survived m0038 |
| --- | --- | --- | --- |
| analyst_categories | (name) | `analyst_categories_name_key` (UNIQUE), `idx_analyst_categories_name` | the UNIQUE (invariant) |
| categorys | (word_id) | `categorys_word_id_key` (UNIQUE), `idx_categorys_word_id` | the UNIQUE |
| hashs | (hash) | `hashs_hash_key` (UNIQUE), `idx_hashs_hash` | the UNIQUE |
| keywords_hashs | (keyword_id) | `idx_keywords_hashs_keyword_id`, `idx_keywords_paths_keyword_id` | the table-consistent name |
| punctuation | (punctuation_text) | `punctuation_punctuation_text_key` (UNIQUE), `idx_punctuation_text` | the UNIQUE |
| words | (word) | `words_word_key` (UNIQUE), `idx_words_word` | the UNIQUE |
| words_hashs | (hash_id, word_id) | `uq_words_hashs_hash_word` (UNIQUE), `idx_words_hashs_hash_word` (m0035) | the UNIQUE |
| words_hashs | (word_id) | `idx_words_hashs_word_id`, `idx_words_paths_word_id` (m0002, legacy name) | the table-consistent name |
| hash_contexts | (hash_id, source_id, side_id) | see cluster 4 | the surviving UNIQUE |

`idx_words_hashs_word_hash` (m0036, `(word_id, hash_id)`) is **not** a duplicate:
its column order is the reverse of the unique constraint and it serves word-first
lookups that constraint's index cannot.

**Classification: confirmed accidental duplication.** 9 redundant indexes and 1
redundant constraint, removed by m0038 with a round-trip-tested downgrade.

## Cluster 6 — `alerts` snapshot columns (attribute duplication, decision pending)

`alerts.file_name` / `alerts.file_path` copy `paths.file_name` /
`paths.file_path` at creation (`core/monitoring/notification_service.py` writes
them; `Api/routes/notifications.py` reads them back). Written once, never
updated, and `alerts.file_id` is `ON DELETE CASCADE`, so the copy cannot outlive
its source. Either the copy is an **as-of snapshot** (then it should be
documented as such) or it is **duplicated state** that shows a stale name after a
rename (then the reader should join `paths`). `path_revisions` exists, so renames
do happen. **Classification: attribute duplication awaiting a business decision
(DB-5).** Not a database-structure defect; no migration proposed until the
product answers.

## Cluster 7 — job/event/notification provenance (attribute typing, not duplication)

`content_signal_runs.job_id`, `rule_evaluations.job_id`,
`scenario_evaluations.job_id`, `report_artifacts.job_id`,
`job_schedules.last_job_id` (and `jobs.job_id` itself) are `text`; only
`job_events.job_id` has a FK (`ON DELETE CASCADE`). Job ids are generated as
`uuid4().hex[:12].upper()` in `services/jobs/manager.py`, so the value domain is
understood but not declared. Retention prunes old jobs, so a plain FK with
`CASCADE` would delete evaluation history and a plain FK with `RESTRICT` would
block retention. **Classification: intentionally-independent provenance,
unenforced (DB-6).** The audit tool counts values that match no job, which is
the measurement needed before deciding between `SET NULL` FKs and leaving the
strings.

## Duplication matrix

One row per candidate the audit considered, with the evidence, the consumers
that decide ownership, the canonical owner, the decision, and the tests that
hold the decision in place. Classifications: **confirmed accidental**,
**intentional separation**, **legacy compatibility**, **derived read-model**,
**unresolved**.

| Candidate structures | Evidence of overlap | Current consumers | Canonical owner | Decision | Required tests |
| --- | --- | --- | --- | --- | --- |
| `hash_contexts`: `uq_hash_contexts_identity` + `uq_hash_contexts_hash_source_side` | both `UNIQUE (hash_id, source_id, side_id)`; two physical indexes maintained per write; m0011 created the first and m0013 re-declared it | none names either constraint in DDL or `ON CONFLICT ON CONSTRAINT`; `paths.context_id` references `hash_contexts(id)` | `uq_hash_contexts_identity` (the m0011 name, asserted by `test_bootstrap_migrations.py`) | **confirmed accidental** - removed by m0038, survivor guarded | `test_redundant_enforcement_removal.py` (5; incl. uniqueness still enforced and a refusal guard) |
| 8 further index pairs (`analyst_categories(name)`, `categorys(word_id)`, `hashs(hash)`, `keywords_hashs(keyword_id)`, `punctuation(punctuation_text)`, `words(word)`, `words_hashs(hash_id,word_id)`, `words_hashs(word_id)`) | identical `USING btree (...)` shape, no predicate, no expression, default operator class; in each pair one member duplicates a UNIQUE constraint's index or a same-table index | application + planner query by column, never by index name (searched `*.py`, `*.js`, `*.html`) | the enforcing / consistently named member of each pair (table in `DUPLICATION_REGISTER.md` DB-2) | **confirmed accidental** - 8 removed by m0038; `downgrade()` recreates all nine | same file; plus `test_db_integrity_audit.py`'s shape tripwire (any new shape fails) |
| `contents.content_data` vs `contents_raw.content` | same source bytes, different representation: zlib+pickle word-ID pairs vs verbatim chunked text | search reads `contents.content_data`; display and exports read `contents_raw` through `load_text_content`, falling back to the word join for pre-m0010 rows | neither - they answer different questions | **intentional separation** (documented precedence in m0010) | `tests/integration/test_content_identity.py`, `tests/integration/test_original_file_view.py` |
| `path_geo_mentions` (view) vs `path_geo_mentions_m0015` (table) | view's legacy branch reads the renamed table for hashes with no successful `places` run; branches are mutually exclusive by construction | all readers go through the view (after Repair 2); nothing reads the table directly | the **view**; the table is a legacy source kept for coverage | **legacy compatibility** - retirement gated on "every hash has a non-failed places run" measured on real data | `test_places_pg.py`, `test_ingestion_batch_categories.py` |
| `categorys` / `words_categorys` vs `analyst_categories` / `analyst_file_categories` / `analyst_categorization_log` | both assign categories to content, but the system taxonomy's category *is* a word (`categorys.word_id UNIQUE`) while the analyst's is operator-owned and has an append-only log | system pipeline writes the first; analyst UI writes the second; m0009 states the audit trail must survive user deletion | two owners, by design (system taxonomy vs analyst taxonomy) | **intentional separation** - merging would break analyst history and the smart taxonomy | `tests/integration/test_analyst_categorization.py`, `tests/integration/test_bootstrap_migrations.py` |
| `alerts.file_name` / `alerts.file_path` vs `paths.file_name` / `paths.file_path` | copied at insert, never updated; `alerts.file_id` cascades so the copy cannot outlive its source | `notification_service` writes them; `Api/routes/notifications.py` displays them | undecided: `paths` (live truth) or a documented as-of snapshot | **unresolved** (DB-4) - owner decision; both readings fit the code | none yet; the decision determines whether a later migration drops the columns |
| 5 `job_id` provenance columns vs `jobs.job_id` | same value domain (12-hex uppercase ids from `manager.py`), but no FK; retention prunes old jobs | evaluations/artifacts/report provenance columns are read for forensics | `jobs` is authoritative; provenance intentionally outlives it | **unresolved** (DB-5) - adding a cascade FK would delete history, a restrict FK would block retention | `tools/db/integrity_audit.py` reports values matching no job; the decision needs that measurement |
| `database/SYLTHARAE.sql` vs `database/migrations/` | two definitions of one schema; dump already behind (2 indexes, 1 constraint value set) | nothing reads it - no code, deployment or test | the **migrations** (`schema_migrations` is the ledger) | **legacy compatibility** - documented as non-authoritative in `docs/DATABASE.md`; regenerate-or-retire is an open owner decision (DB-6) | `tests/integration/test_schema_reference.py` pins the generated reference that *is* authoritative |
| `ContentDBService.create_alert` → `AlertsRepository.insert_alert` vs `core/monitoring/notification_service.py` | two implementations of "create an alert" over one table | only `notification_service` is called; the repository path has no caller (searched) | `notification_service` | **confirmed accidental (dead code)** - recorded as DB-10; not deleted, because removing legacy surface is a product decision | none; recorded so the next change is made in the live path |
| `analyst_file_categories.assigned_by_username` / `analyst_categorization_log.analyst_username` vs `users.username` | copied strings rather than an FK | audit/history views | the history tables themselves | **intentional separation** - m0009: the trail must survive user deletion | `tests/integration/test_analyst_categorization.py` |

Nothing in this matrix was decided from names: every row cites the catalog, a
migration or a call site.

## Table lifecycle (each table's role, once)

| Lifecycle stage | Tables |
| --- | --- |
| Definition | `words`, `punctuation`, `categorys`, `sources`, `sides`, `keywords`, `analyst_categories`, `geo_places`, `geo_place_names`, `monitoring_rules`, `scenarios`, `users` |
| Versioned definition | `monitoring_rule_versions`, `scenario_versions` |
| Content identity | `hashs`, `hash_contexts`, `contents`, `contents_raw`, `titles_content`, `words_hashs`, `keywords_hashs` |
| Occurrence | `paths`, `path_revisions` |
| Association | `words_categorys`, `analyst_file_categories`, `content_signal_places` |
| Derived / read model | `path_geo_mentions` (view), `path_geo_mentions_m0015` (legacy source), `contents.content_data` (search index) |
| Signal state | `content_signals`, `content_signal_runs` |
| Execution | `jobs`, `job_events`, `job_schedules` |
| Evaluation / outcome | `rule_evaluations`, `rule_subject_ledger`, `scenario_evaluations`, `scenario_outcomes` |
| Reporting | `report_runs`, `report_run_datasets`, `report_run_analyses`, `report_artifacts`, `report_baselines` |
| Notification | `alerts` |
| Audit / history | `audit_log`, `analyst_categorization_log`, `saved_search_imports`, `geo_gazetteer_loads` |
| Identity / session / preference | `users`, `sessions`, `user_navigation_prefs`, `saved_searches` |
| Localisation | `translation_overrides` |
| Infrastructure | `schema_migrations` |

No two rows in that table answer the same question.
