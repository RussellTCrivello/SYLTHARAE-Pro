# Canonical entity map (deliverable E)

For each entity: the canonical table, its identity key, who writes it, who reads
it, and what is NOT canonical (duplicates, retired shapes, copies). Derived from
the migrated schema plus the code that touches it. This is the map to check
before adding a table, column or join - if the entity is already here, use it.

## Content (the three levels)

| Entity | Canonical table | Identity | Written by | Read by |
| --- | --- | --- | --- | --- |
| Content identity | `hashs` | `UNIQUE (hash)` (sha256 hex) | ingestion (`Api/services/import_service.py`) | search, analytics, reporting, `verify_readiness.py` |
| Context identity | `hash_contexts` | `UNIQUE (hash_id, source_id, side_id)` (DB-1: two names, one invariant) | ingestion | files/analytics routes, detection, reporting |
| Occurrence | `paths` | `id`; `context_id NOT NULL`; occurrence identity = content identity + location, resolved in `database/services/dedup_service.py::find_occurrence` (`ORDER BY p.id`) | ingestion; `path_revisions` records changes | nearly everything that lists files |
| Raw display text | `contents_raw` | `UNIQUE (hash_id, chunk_seq)` | ingestion (extractor) | `core/content_markers.py`, `core/word_limits.py`, report renderers |
| Word-ID store (search) | `contents` | `hash_id` (`content_data` = zlib+pickle of word-ID pairs) | ingestion | search index rebuild, `Api/cursor_pagination.py` |
| Title text | `titles_content` | `id`, `hash_id` indexed (one row per hash in practice; `title_content_id` self-reference carries the chain) | ingestion | search, analytics |
| Words per content | `words_hashs` | `UNIQUE (hash_id, word_id)` | ingestion / vocabulary rebuild | search, analytics, files |
| Keywords per content | `keywords_hashs` | `UNIQUE (hash_id, keyword_id)` | analyst keywords apply | api routes, analytics |
| Taxonomy | `words`, `punctuation`, `categorys`, `words_categorys` | `words.word` UNIQUE; `categorys.word_id` UNIQUE | schema seed + analyst workflow | everywhere words/categories are shown |
| Analyst taxonomy (separate by contract) | `analyst_categories`, `analyst_file_categories`, `analyst_categorization_log` | `analyst_categories` UNIQUE(name)+UNIQUE(lower(name)); file assignment `UNIQUE (path_id, category_id)` | `Api/services/analyst_categories.py` | `Api/routes/analyst_categories.py`, search service, reports |
| Sources and sides | `sources`, `sides` | `sources.name` UNIQUE; `sides.name` UNIQUE | setup/API | context creation, listings |

**Not canonical:**
* `path_geo_mentions_m0015` - a preserved pre-gazetteer table. After DB-3 was
  repaired it has **no application reader**: everything goes through the
  `path_geo_mentions` view. Keep it until the operator confirms every hash has a
  places run; retire only then (see `MIGRATION_PLAN.md`).
* `path_geo_mentions` (view) - the canonical *read* path for place mentions.
* Any name of the form `words_paths` / `wp.path_id` - retired by m0011; DB-9 was
  the last occurrence in code.

## Detection and place intelligence

| Entity | Canonical table | Identity | Written by | Read by |
| --- | --- | --- | --- | --- |
| A finding | `content_signals` | `UNIQUE (dedup_key)`, 15 CHECKs (provenance triple, offsets, resolution rules) | `services/detection/signal_store.py`, `redetection.py` | places/notifications routes, `core/reporting/datasets.py` |
| Scan ledger | `content_signal_runs` | `PRIMARY KEY (hash_id, detector)` | detection admin + redetection | detection admin, notifications |
| Place candidates of a signal | `content_signal_places` | `PRIMARY KEY (signal_id, place_id)`; `place_id` RESTRICT | `services/geo/gazetteer.py` | places route, reporting datasets |
| Place entity | `geo_places` | `id`, 7 CHECKs | gazetteer load | places route, place_intel, reports |
| Place names | `geo_place_names` | `UNIQUE (place_id, language, match_key)` | gazetteer load | place search |
| Gazetteer release | `geo_gazetteer_loads` | `id` | `services/geo/gazetteer.py` | places route (provenance banner) |
| Place mentions (read model) | `path_geo_mentions` (view) | derived | - | reporting (`ingestion_batch._query_places`) |

## Monitoring, rules and scenarios

| Entity | Canonical table | Identity | Notes |
| --- | --- | --- | --- |
| Rule definition | `monitoring_rules` | `id`; versioned by `monitoring_rule_versions`; `CHECK (baselined_version <= version)` | case-insensitive name uniqueness per owner, live rules only |
| Rule evaluation | `rule_evaluations` | `id` | `job_id` provenance unenforced (DB-5) |
| Scenario definition | `scenarios` + `scenario_versions` | `id` / `(scenario_id, version)` | immutable versions |
| Scenario evaluation | `scenario_evaluations` | `id`, 6 CHECKs | `job_id` unenforced (DB-5) |
| Scenario outcome | `scenario_outcomes` | `id`, append-only trigger | the report source |
| Evaluation/signal links | `rule_subject_ledger` | `id` | |
| Notifications | `alerts` | `id` | one row per delivered notification; `type`/`priority` vocabulary unchecked (DB-7); copies file name/path (DB-4) |

## Reporting

| Entity | Canonical table | Identity | Notes |
| --- | --- | --- | --- |
| A report run | `report_runs` | `id`, terminal-state immutability trigger | `job_id` unenforced (DB-5) |
| Datasets of a run | `report_run_datasets` | `PRIMARY KEY (run_id, position)` + `UNIQUE (run_id, dataset_key)` | write-once trigger |
| Analyses of a run | `report_run_analyses` | `PRIMARY KEY (run_id, position)` + `UNIQUE (run_id, analysis_key)` | write-once trigger |
| Produced file | `report_artifacts` | `id`; `sha256`/`byte_size` CHECKs + immutability trigger | the bytes and their manifest |
| Frozen comparison points | `report_baselines` | `PRIMARY KEY (user_id, criteria_hash)` | `last_max_id` watermark |

## Identity, access, configuration, operational

| Entity | Canonical table | Notes |
| --- | --- | --- |
| User | `users` | referenced by 20+ FKs |
| Session | `sessions` | |
| Audit trail | `audit_log` | append-only, FK-free user reference **by design** (m0009) |
| Navigation preferences | `user_navigation_prefs` | `UNIQUE (user_id, interface_id)`; interface ids come from the frozen interface registry (`docs/INTERFACE_REGISTRY.md`) |
| Saved searches | `saved_searches` | `legacy_id` preserved for migrated rows |
| Saved-search import | `saved_search_imports` | provenance of one import batch |
| Translation overrides | `translation_overrides` | operator overrides on top of the catalogs |
| Jobs / events / schedules | `jobs`, `job_events`, `job_schedules` | `job_id` is the PK |
| Migration ledger | `schema_migrations` | **the authority for schema state** |

## Canonical rules that follow from the map

1. **Content-derived data is keyed by `hash_id`**, never by `path_id`
   (m0011). A path-scoped feature joins `paths.context_id -> hash_contexts` to
   reach it. DB-9 was a violation of exactly this rule.
2. **Place mentions are read through the view.** Only a new places run
   supersedes a mention, never a direct table read (DB-3).
3. **Occurrence identity is resolved in code, not by a constraint.** `paths`
   has no unique on `(context_id, file_path)`: the same location can legitimately
   appear under different contexts, and re-imports are matched by
   `dedup_service.find_occurrence` (content identity + location, earliest id
   wins). Do not add a unique constraint here without confirming that with the
   ingestion owner.
4. **Analyst and system taxonomies never join each other** (m0009, FR-1.4).
   Reports that show both must present them as separate sections.
5. **Report history is immutable**; corrections are new runs, never updates.
   This is enforced by triggers and must not be "fixed" by adding update paths.
6. **`schema_migrations` decides the schema.** `database/SYLTHARAE.sql` is a
   snapshot with no authority (DB-6).
7. **The interface registry is the only source of interface ids** used by
   `user_navigation_prefs` (`docs/INTERFACE_REGISTRY.md`; frozen).
