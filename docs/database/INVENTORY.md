# Database inventory (deliverable A)

The tables the migrated schema actually contains, with their key structure. This
is the reference the other audit deliverables cite.

## How this was produced

* The catalogue was read from a **disposable database built by running the real
  migrations** (`database/bootstrap.py` → `database/migration_runner.py`,
  `m0001` … `m0039`) through `information_schema`, `pg_constraint`, `pg_indexes`
  and `pg_trigger`. No production database was touched.
* Authority is the **migration directory**, not `database/SYLTHARAE.sql`: the
  committed dump is a schema-only snapshot of an earlier revision (see
  deliverable D, finding DUPLICATION-3). Where the two disagree, the migrations
  win.
* Counts are from `COUNT(*)`, never from parsing `psql` output. (`psql -A` still
  prints a header and an `(N rows)` footer; an early pass that counted those
  lines reported "53 tables" and a table named `table_name`. Both were
  artefacts of the parser, not of the schema.)
* Static consumers were counted by scanning `*.py`, `*.js`, `*.html` and `*.sql`
  for each table name (`test-doc/` is an Apache Tika test corpus, excluded).

## What the schema contains

**51 base tables and 1 view** (`path_geo_mentions`, defined in m0019 and kept in
step with `content_signal_places` + `geo_places`).

| Object | Count | Note |
| --- | --- | --- |
| Base tables | 51 | this document |
| Views | 1 | `path_geo_mentions` |
| Columns | 490 | |
| Constraints | 254 | 48 primary keys, 66 foreign keys, 24 unique, 116 check |
| Indexes | 179 | after m0038 removed nine exact duplicates |
| Triggers | 5 | report immutability, append-only outcomes, updated-at |
| Functions | 5 | the trigger functions above |
| Sequences | 3 | serial columns |

Every foreign key in the schema is `VALID` (no `NOT VALID` constraint), so the
constraints are enforced for the rows already stored.

## Table inventory

<!-- BEGIN GENERATED TABLE INVENTORY -->

| Table | Columns | Primary key | Unique keys | FKs out |
| --- | --- | --- | --- | --- |
| `alerts` | 18 | id | - | 6 |
| `analyst_categories` | 6 | id | UNIQUE (name) | - |
| `analyst_categorization_log` | 10 | id | - | - |
| `analyst_file_categories` | 7 | id | UNIQUE (path_id, category_id) | 2 |
| `audit_log` | 8 | id | - | - |
| `categorys` | 2 | id | UNIQUE (word_id) | 1 |
| `content_signal_places` | 2 | signal_id, place_id | - | 2 |
| `content_signal_runs` | 12 | hash_id, detector | - | 1 |
| `content_signals` | 25 | id | UNIQUE (dedup_key) | 1 |
| `contents` | 4 | id | - | 1 |
| `contents_raw` | 6 | id | UNIQUE (hash_id, chunk_seq) | 1 |
| `geo_gazetteer_loads` | 9 | id | - | - |
| `geo_place_names` | 10 | id | UNIQUE (place_id, language, match_key) | 1 |
| `geo_places` | 13 | id | UNIQUE (place_key) | - |
| `hash_contexts` | 5 | id | UNIQUE (hash_id, source_id, side_id)<br>UNIQUE (hash_id, source_id, side_id) | 3 |
| `hashs` | 2 | id | UNIQUE (hash) | - |
| `job_events` | 5 | event_id | - | 1 |
| `job_schedules` | 15 | id | UNIQUE (owner_user_id, name) | 1 |
| `jobs` | 19 | job_id | - | - |
| `keywords` | 3 | id | UNIQUE (keyword) | 1 |
| `keywords_hashs` | 3 | - | UNIQUE (hash_id, keyword_id) | 2 |
| `monitoring_rule_versions` | 6 | rule_id, version | - | 2 |
| `monitoring_rules` | 16 | id | - | 2 |
| `path_geo_mentions_m0015` | 8 | id | UNIQUE (hash_id, place_name) | 1 |
| `path_revisions` | 7 | id | - | 2 |
| `paths` | 18 | id | - | 2 |
| `punctuation` | 2 | id | UNIQUE (punctuation_text) | - |
| `report_artifacts` | 18 | id | - | 2 |
| `report_baselines` | 4 | user_id, criteria_hash | - | 1 |
| `report_run_analyses` | 13 | run_id, "position" | UNIQUE (run_id, analysis_key) | 1 |
| `report_run_datasets` | 12 | run_id, "position" | UNIQUE (run_id, dataset_key) | 1 |
| `report_runs` | 22 | id | - | 2 |
| `rule_evaluations` | 16 | id | - | 1 |
| `rule_subject_ledger` | 16 | rule_id, subject_key | - | 5 |
| `saved_search_imports` | 8 | id | UNIQUE (file_sha256) | - |
| `saved_searches` | 15 | id | UNIQUE (legacy_source, legacy_id) | 1 |
| `scenario_evaluations` | 19 | id | - | 2 |
| `scenario_outcomes` | 13 | id | - | 3 |
| `scenario_versions` | 6 | scenario_id, version | - | 2 |
| `scenarios` | 14 | id | - | 2 |
| `schema_migrations` | 3 | version | - | - |
| `sessions` | 7 | session_id | - | 1 |
| `sides` | 4 | id | UNIQUE (name) | - |
| `sources` | 15 | id | UNIQUE (name) | 1 |
| `titles_content` | 5 | id | - | 2 |
| `translation_overrides` | 6 | locale, message_key | - | 1 |
| `user_navigation_prefs` | 5 | user_id, interface_id | - | 1 |
| `users` | 12 | id | UNIQUE (username) | - |
| `words` | 2 | id | UNIQUE (word) | - |
| `words_categorys` | 2 | - | UNIQUE (word_id, category_id) | 2 |
| `words_hashs` | 4 | - | UNIQUE (hash_id, word_id) | 2 |

<!-- END GENERATED TABLE INVENTORY -->

## What this inventory cannot tell you without the operator's database

The audit ran against an **empty** database (a fresh migration chain). It can
therefore state what the *schema* is and what the *code* does with it, and it
cannot state anything about stored data: row counts, whether any foreign key has
orphans in practice, whether any value falls outside a vocabulary, and which
indexes a real workload uses are all unknown until the checks run against the
real database.

The read-only commands for that are:

```
python3 tools/db/integrity_audit.py                # findings + per-check counts
python3 tools/db/integrity_audit.py --json         # machine-readable
python3 tools/db/integrity_audit.py --counts       # rows per table
```

They open the database the application is configured with (`DB_*` / the
application settings) and perform only `SELECT`s. Nothing in the audit writes,
locks beyond a read, or drops anything; the write-side changes it recommends are
in deliverable F and require approval.
