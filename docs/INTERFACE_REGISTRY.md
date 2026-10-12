# Interface Registry

Every page, section and internal surface the product presents is declared once,
in `core/interfaces/registry.py`, and every declaration is checked against the
application it describes. A page that is served but not declared fails
`tests/integration/test_interface_coverage.py`; a declaration that names an
endpoint the application does not have fails the same file. The registry is not
documentation *about* the product - it is the product's own statement of what
it offers, and the document below is generated from it.

## What the registry is for

Three things, in the order they matter:

1. **Ownership.** Each user-facing page is owned by exactly one interface, so
   there is always an answer to "where does this live, and who is responsible
   for it" - including for pages nothing links to.
2. **Navigation.** The sidebar, the command palette and the interface pickers
   are rendered from the registry rather than from a hand-written list, so a
   page cannot be reachable from one and missing from another.
3. **Governance.** Switching an interface off is a declared operation with
   declared consequences: the registry records what an interface depends on,
   so a configuration that would break a page is refused with an explanation
   instead of producing a page that half-works.

## The registry is frozen

From the productization directive onward, a new surface is not "a page somebody
added": it is a declaration. The registry is **frozen** in the sense that the
five things a user can rely on are all derived from it, and adding a page
without declaring it fails the suite:

* **register** - every interface is declared once, with a stable ID;
* **navigation** - the sidebar, command palette and pickers are rendered from
  the declarations, so a page cannot be reachable in one place and missing from
  another;
* **shortcut** - keyboard sequences are declared and unique (`validate_registry`
  rejects a collision rather than letting the palette pick a winner);
* **help** - each interface names its help topic, so "how do I use this" has an
  answer that lives next to the page's own declaration;
* **visibility** - the role and default state decide who may reach it, and the
  request gate enforces that at the endpoint, not only in the menu.

The guardrails are ordinary tests, not promises: coverage against a live
application, registry integrity, this document, template purity, lifecycle, and
visibility. Adding a page without registering it fails the coverage suite.

## How this document is generated

The reference table below is produced by `core/interfaces/docgen.py` and
compared with the registry by `tests/unit/test_interface_docs.py`. Nothing in
it is typed by hand; regenerate it with:

```
python3 -m core.interfaces.docgen docs/INTERFACE_REGISTRY.md
```

The prose is held to the same rule: counts belong in the generated block. Where
a number *is* written outside it, it is a **historical** figure kept for
context, and it is labelled as such - an earlier revision of the productization
map listed three different endpoint counts (57, 40 and 41) for the same
application because each was typed at a different time. That is the failure
this document is designed not to repeat.

## Reading the table

* **ID** - the stable interface identifier. It is what settings, permissions
  and translations refer to; route names may change, IDs may not.
* **Domain** - the declared domain vocabulary in `core/interfaces/domains.py`.
  A declared domain with no interface yet is intentional: it is the place the
  next interface in that domain will go, not a defect.
* **Route** - the canonical endpoint the interface navigates to. Endpoints the
  interface owns but does not navigate to are listed under **Aliases**; they
  exist for request-level authorization and are never navigation entries.
* **Role / Default** - who may reach it and whether it is on before an operator
  chooses otherwise.
* **Depends on** - interfaces that must be reachable for this one to work.
  Dependencies are validated for cycles and unknown targets.
* **Status** - `ACTIVE` or `DEPRECATED`. A Deprecated interface is still served
  but is no longer offered in navigation, and the policy for what that means
  lives in `core/interfaces/lifecycle.py` (nothing else may hard-code it).
  Retired IDs are kept in `RETIRED_INTERFACE_IDS` so a settings file written
  before the interface was retired still resolves.

<!-- BEGIN GENERATED REGISTRY TABLE -->
- Interfaces: **35** (features declared separately: **1**)
- Endpoints owned: **81**
- With a keyboard shortcut: **18**; with a help topic: **33**
- By domain: ADMINISTRATION 3, ANALYZE 4, CLASSIFY 2, DISCOVER 11, INGEST 2, INTERNAL 1, OPERATE 3, REPORT 5, SETTINGS 3, WORK 1
- By status: ACTIVE 34, DEPRECATED 1
- By kind: INTERNAL 1, PAGE 33, SECTION 1


### WORK (1)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dashboard` | Dashboard | WORK | `index` | — | any | on | — | work/dashboard | g w | ACTIVE |

### DISCOVER (11)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `file_library` | File Library | DISCOVER | `files.files_list` | `files.file_detail`, `files.file_content_lazy`, `files.file_content_page`, `files.file_full_content`, `files.file_search_all_pages`, `files.file_chart_data`, `files.file_types_page`, `files.file_type_documents`, `files.delete_file`, `files.bulk_delete_files`, `files.bulk_export_files` | any | on | — | discover/file-library | g f | ACTIVE |
| `search` | Search | DISCOVER | `search_page` | `search_advanced`, `search_enhanced_page`, `saved_searches_page`, `search_advanced_api` | any | on | — | discover/search | g s | ACTIVE |
| `sources` | Sources | DISCOVER | `sources_list` | `source_add`, `source_detail`, `source_edit`, `source_categories_keywords` | any | on | — | discover/sources | — | ACTIVE |
| `sides` | Sides | DISCOVER | `sides_list` | `side_add`, `side_detail`, `side_edit`, `side_categories_keywords` | any | on | — | discover/sides | — | ACTIVE |
| `keywords` | Keywords | DISCOVER | `keywords_list` | `keyword_detail`, `keywords_add`, `keyword_documents` | any | on | — | discover/keywords | — | ACTIVE |
| `words` | Words | DISCOVER | `words_list` | `word_detail`, `words_add` | any | on | — | discover/words | — | ACTIVE |
| `categories` | Categories | DISCOVER | `categories_list` | `category_words`, `category_add`, `category_documents` | any | on | — | discover/categories | — | ACTIVE |
| `email_words` | Email Words | DISCOVER | `email_words` | — | any | on | — | discover/email-words | — | ACTIVE |
| `notifications` | Notifications | DISCOVER | `notifications_page` | — | any | on | — | discover/notifications | g n | ACTIVE |
| `signal_horizon` | Horizon & Signal Explorer | DISCOVER | `signals_page` | — | any | on | — | discover/signals | g h | ACTIVE |
| `monitoring` | Monitoring | DISCOVER | `monitoring_page` | — | any | on | `signal_horizon`, `notifications` | discover/monitoring | g m | ACTIVE |

### INGEST (2)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `input_ingestion` | Input / Ingestion | INGEST | `operations_input_page` | `files.upload_page`, `files.get_active_tasks`, `files.upload_progress`, `files.api_cancel_task`, `files.pause_task`, `files.resume_task`, `ingestion_batch_print` | any | on | — | ingest/input | g i | ACTIVE |
| `import_center` | Import Center | INGEST | `operations_import_page` | — | any | on | — | ingest/import-center | — | ACTIVE |

### ANALYZE (4)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `archives` | File Management and Analysis | ANALYZE | `archives_page` | — | any | on | `file_library` | analyze/archives | g a | ACTIVE |
| `path_analysis` | Path Analysis | ANALYZE | `path_analysis_page` | — | any | on | `file_library` | analyze/path-analysis | g p | ACTIVE |
| `map_viewer` | Map Viewer | ANALYZE | `map_viewer_page` | — | any | on | `archives`, `file_library` | analyze/map-viewer | g g | ACTIVE |
| `batch_analysis` | Batch Analysis | ANALYZE | `analysis_batch` | `analysis_batch_process` | any | on | `file_library` | analyze/batch | g b | ACTIVE |

### CLASSIFY (2)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `analyst_categorization` | Analyst Categories | CLASSIFY | `analyst_categorization_page` | — | any | on | `file_library` | classify/analyst-categories | — | ACTIVE |
| `classification` | Classification | CLASSIFY | `file_classification_page` | — | any | on | `file_library`, `words` | classify/classification | — | ACTIVE |

### REPORT (5)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `comprehensive_dashboard` | Comprehensive Dashboard | REPORT | `comprehensive_dashboard` | — | any | on | `file_library` | report/detailed-dashboard | — | ACTIVE |
| `reports` | Reports | REPORT | `reports_page` | `entry_dossier_print` | any | on | `search`, `jobs` | report/reports | g r | ACTIVE |
| `reports_dashboard` | Reports Dashboard | REPORT | `reports_dashboard_page` | — | any | on | `reports`, `jobs`, `schedules` | report/dashboard | — | ACTIVE |
| `schedules` | Schedules | REPORT | `schedules_page` | — | any | on | `reports`, `jobs`, `monitoring` | report/schedules | — | ACTIVE |
| `charts_dashboard` | Charts Dashboard | REPORT | `charts_dashboard` | — | any | on | `file_library` | report/charts | — | ACTIVE |

### OPERATE (3)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `detection` | Detection | OPERATE | `detection_page` | — | admin | on | `signal_horizon`, `jobs` | operate/detection | g d | ACTIVE |
| `jobs` | Jobs | OPERATE | `operations_jobs_page` | `operations_job_detail_page` | any | on | — | operate/jobs | g j | ACTIVE |
| `import_export_console` | Import/Export | OPERATE | `import_export_page` | — | admin | on | — | — | — | DEPRECATED |

### ADMINISTRATION (3)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `retention` | Retention | ADMINISTRATION | `retention_page` | — | any | on | `jobs`, `reports` | operate/retention | — | ACTIVE |
| `users` | User Management | ADMINISTRATION | `users_page` | — | admin | on | — | administration/users | g u | ACTIVE |
| `audit_log` | Audit Log | ADMINISTRATION | `audit_page` | — | admin | on | — | administration/audit | g l | ACTIVE |

### SETTINGS (3)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `settings` | Settings | SETTINGS | `settings_page_direct` | `settings_api.settings_page` | admin | on | — | settings/overview | g , | ACTIVE |
| `interface_manager` | Interface Manager | SETTINGS | — | — | admin | on | `settings` | settings/interfaces | — | ACTIVE |
| `translation_manager` | Translation Management | SETTINGS | `translations.translation_management_page` | — | admin | on | — | settings/translations | g t | ACTIVE |

### INTERNAL (1)

| ID | Name | Domain | Route | Aliases | Role | Default | Depends on | Help | Shortcut | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `concurrency_monitor` | Concurrency Monitor | INTERNAL | `concurrency.dashboard` | `concurrency.get_metrics`, `concurrency.get_threads`, `concurrency.get_processes`, `concurrency.get_pools`, `concurrency.get_async_tasks` | admin | on | — | — | — | ACTIVE |

### Features (not interfaces)

| ID | Name | Description | Default |
| --- | --- | --- | --- |
| `page_tips` | Page Tips & Documentation | Explanatory tips at the top of each page, describing the elements on it, how to use them and how to add data. | on |
<!-- END GENERATED REGISTRY TABLE -->

## Related documents

* `docs/REGISTRY_EVIDENCE.md` - the generated evidence report: coverage against
  the running application, unmanaged endpoint count, the alias and dependency
  reports, and the rendered navigation observation.
* `docs/endpoint_inventory.json` - the deterministic snapshot of every route
  the application serves, with its classification and owner.
* `docs/PRODUCTIZATION_MAP.md` - the map of what is finished and what is
  legacy, pointing at the two generated sources above rather than restating
  their numbers.
* `docs/EXPERIENCE_CONTRACT.md` - what each interface promises the reader:
  columns, filters, actions, states and help.
