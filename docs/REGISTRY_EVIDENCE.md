# Registry Evidence

The productization directive (steps 1-2) ends with an evidence set: the facts an
operator or reviewer needs before any shell work starts, none of them typed by
hand. This document carries them, generated from two sources that cannot
disagree with the product:

* the **registry block**, generated from `core/interfaces/registry.py` - what
  the product declares; and
* the **application block**, generated from a live Flask application - what it
  actually serves, including the rendered navigation.

Both blocks are compared with their sources by tests, so the document cannot
drift: `tests/unit/test_interface_docs.py` holds the registry half,
`tests/integration/test_interface_coverage.py` holds the application half.

Regenerate:

```
python3 -m core.interfaces.evidence --write docs/REGISTRY_EVIDENCE.md
INFORAXIS_WRITE_EVIDENCE=1 python3 -m pytest \
    tests/integration/test_interface_coverage.py -k evidence
```

## The evidence set, and where each item comes from

| # | Item | Source |
| --- | --- | --- |
| 1 | Registry inventory | registry block |
| 2 | Endpoint coverage result | application block |
| 3 | Interface count | registry block |
| 4 | Unmanaged endpoint count | application block |
| 5 | Internal endpoint exception count | application block |
| 6 | Alias count | registry block |
| 7 | Dependency validation result | registry block |
| 8 | Registry integrity and test result | registry block |
| 9 | Legacy settings migration result | application block |
| 10 | Rendered navigation result | application block |

## How coverage is decided

An endpoint is *user facing* when it answers a browser with a page rather than
JSON, or when it is a page the application redirects to. The coverage rule is
that each one is owned by exactly one interface. Two exception sets are
declared - one for endpoints that are part of the machinery rather than the
product, and one for the pages that are internal - and their size is part of
the evidence: an exception list that grows is a decision somebody has to make
on purpose.

The remaining legacy surface is named, not hidden: `INTERFACE_METADATA` and
`LEGACY_INTERFACE_IDS` in `core/interfaces/registry.py` hold settings keys and
interface IDs from earlier revisions. They are kept so a settings file written
by an older version still resolves, and they are reported here so nobody
mistakes them for the current vocabulary.

<!-- BEGIN GENERATED REGISTRY EVIDENCE -->
### 1. Registry inventory

- Interfaces declared: **35**
- Cross-cutting features (not interfaces): **1**
- Endpoints owned (canonical routes + aliases): **81**
- With a keyboard shortcut: **18**
- With a help topic: **33**
- Declared domain vocabulary: **12**
- Domains currently containing interfaces: **10**
- Declared domains holding no interface yet: **2**

Domains are **declared** in `core/interfaces/domains.py`; a declared domain may hold no interface yet. The two numbers are different, and both are reported:

| Domain | Interfaces | Status |
| --- | --- | --- |
| WORK | 1 | in use |
| DISCOVER | 11 | in use |
| INGEST | 2 | in use |
| PROCESS | 0 | declared, empty |
| ANALYZE | 4 | in use |
| CLASSIFY | 2 | in use |
| REPORT | 5 | in use |
| OPERATE | 3 | in use |
| ADMINISTRATION | 3 | in use |
| SETTINGS | 3 | in use |
| SECURITY | 0 | declared, empty |
| INTERNAL | 1 | in use |

Declared aliases: **47**, across **13** interfaces. An alias is an endpoint the interface owns but does not navigate to; aliases never become navigation entries.

| Interface | Aliases |
| --- | --- |
| `batch_analysis` | `analysis_batch_process` |
| `categories` | `category_add`, `category_documents`, `category_words` |
| `concurrency_monitor` | `concurrency.get_async_tasks`, `concurrency.get_metrics`, `concurrency.get_pools`, `concurrency.get_processes`, `concurrency.get_threads` |
| `file_library` | `files.bulk_delete_files`, `files.bulk_export_files`, `files.delete_file`, `files.file_chart_data`, `files.file_content_lazy`, `files.file_content_page`, `files.file_detail`, `files.file_full_content`, `files.file_search_all_pages`, `files.file_type_documents`, `files.file_types_page` |
| `input_ingestion` | `files.api_cancel_task`, `files.get_active_tasks`, `files.pause_task`, `files.resume_task`, `files.upload_page`, `files.upload_progress`, `ingestion_batch_print` |
| `jobs` | `operations_job_detail_page` |
| `keywords` | `keyword_detail`, `keyword_documents`, `keywords_add` |
| `reports` | `entry_dossier_print` |
| `search` | `saved_searches_page`, `search_advanced`, `search_advanced_api`, `search_enhanced_page` |
| `settings` | `settings_api.settings_page` |
| `sides` | `side_add`, `side_categories_keywords`, `side_detail`, `side_edit` |
| `sources` | `source_add`, `source_categories_keywords`, `source_detail`, `source_edit` |
| `words` | `word_detail`, `words_add` |

### 3. Dependency validation

- Validation result: **no issues**
- Interfaces declaring a dependency: **15**
- Interfaces other interfaces depend on: **11**

| Interface | Requires | Required by |
| --- | --- | --- |
| `file_library` | — | `analyst_categorization`, `archives`, `batch_analysis`, `charts_dashboard`, `classification`, `comprehensive_dashboard`, `map_viewer`, `path_analysis` |
| `search` | — | `reports` |
| `words` | — | `classification` |
| `analyst_categorization` | `file_library` | — |
| `notifications` | — | `monitoring` |
| `signal_horizon` | — | `detection`, `monitoring` |
| `monitoring` | `notifications`, `signal_horizon` | `schedules` |
| `archives` | `file_library` | `map_viewer` |
| `path_analysis` | `file_library` | — |
| `map_viewer` | `archives`, `file_library` | — |
| `batch_analysis` | `file_library` | — |
| `classification` | `file_library`, `words` | — |
| `comprehensive_dashboard` | `file_library` | — |
| `reports` | `jobs`, `search` | `reports_dashboard`, `retention`, `schedules` |
| `reports_dashboard` | `jobs`, `reports`, `schedules` | — |
| `retention` | `jobs`, `reports` | — |
| `schedules` | `jobs`, `monitoring`, `reports` | `reports_dashboard` |
| `charts_dashboard` | `file_library` | — |
| `detection` | `jobs`, `signal_horizon` | — |
| `jobs` | — | `detection`, `reports`, `reports_dashboard`, `retention`, `schedules` |
| `settings` | — | `interface_manager` |
| `interface_manager` | `settings` | — |

### 4. Registry integrity

`validate_registry()` reports no issues: identifiers unique, domains from the closed set, roles known, routes declared consistently, no dependency is unknown or circular, and no two interfaces share a keyboard shortcut.

### 5. Lifecycle and migration

- Interfaces by status: **ACTIVE 34, DEPRECATED 1**
- Interfaces by kind: **INTERNAL 1, PAGE 33, SECTION 1**

Renames and merges the registry understands (a stored value under an old key reaches the interface that replaced it; the code may not name the old key):

| Legacy key | Reaches |
| --- | --- |
| `advanced_search` | `search` |
| `analytics` | `comprehensive_dashboard` |
| `file_analysis` | `archives` |
| `file_browser` | `file_library` |
| `file_upload` (retired: no interface of its own) | `input_ingestion` |
| `upload_files` | `input_ingestion` |

### 6. Feature declarations

A feature is a cross-cutting capability with no page of its own. Everything the application gates this way is declared here; `tests/unit/test_interface_lifecycle.py` fails if a declared feature is not actually gated in code, or if a cross-cutting gate exists without a declaration.

| Feature | Default | Gated in | Description |
| --- | --- | --- | --- |
| `page_tips` | on | `templates/components/page_tips.html` | Explanatory tips at the top of each page, describing the elements on it, how to use them and how to add data. |

Cross-cutting settings that are **not** features (they belong to an existing interface, so they are values in the settings engine and nothing to do with the registry):

| Setting | Owner |
| --- | --- |
| `system.animations_enabled` | Display preferences (no product surface) |
| `system.show_breadcrumbs` | Display preferences (no product surface) |
| `system.notifications_enabled` | the `notifications` interface |
| `search.enable_history` | the `search` interface |
| `search.enable_saved_searches` | the `search` interface |
| `display.show_file_preview` | the `file_library` interface |
| `display.show_metadata` | the `file_library` interface |
<!-- END GENERATED REGISTRY EVIDENCE -->

<!-- BEGIN GENERATED APPLICATION EVIDENCE -->
### 7. Endpoint coverage

- Endpoints in the application's URL map (static excluded): **460**
- User-facing page endpoints: **63**
- Owned by an interface: **81**
- **Unmanaged user-facing endpoints**: **0**
- Interfaces with a navigable route: **34**

Unmanaged user-facing endpoints: **0** — every page the application serves is owned by exactly one interface.

### 8. Endpoint classification

| Classification | Endpoints |
| --- | --- |
| ACTION | 9 |
| API_ENDPOINT | 370 |
| INTERNAL_PAGE | 1 |
| REDIRECT | 1 |
| SYSTEM_ENDPOINT | 16 |
| TEST_ENDPOINT | 1 |
| USER_INTERFACE | 62 |

By blueprint:

| Blueprint | Endpoints |
| --- | --- |
| (app) | 240 |
| analytics | 22 |
| archives_api | 12 |
| auth | 12 |
| concurrency | 6 |
| content_analysis | 6 |
| cursor_api | 3 |
| error_dashboard | 4 |
| exports | 2 |
| file_analysis | 20 |
| file_operations | 3 |
| files | 32 |
| health | 1 |
| import_export | 6 |
| map_api | 11 |
| operations_api | 29 |
| paths | 3 |
| performance | 7 |
| preview | 2 |
| settings_api | 27 |
| setup | 5 |
| translations | 7 |

### 9. Declared exceptions

The coverage rule tolerates exactly these, by name — a new page cannot be added to an exception list by accident, because each list is declared in `core/interfaces/inventory.py` and reproduced here.

**SYSTEM_ENDPOINTS** (17): `auth.change_password`, `auth.first_admin_create`, `auth.first_admin_page`, `auth.login`, `auth.login_page`, `auth.logout`, `auth.me`, `favicon`, `get_csrf_token`, `health.health`, `set_language`, `setup.check_setup_status`, `setup.run_installation`, `setup.setup_page`, `setup.system_check`, `setup.test_database`, `static`

**INTERNAL_PAGE_ENDPOINTS** (1): `concurrency.dashboard`

**REDIRECT_ENDPOINTS** (1): `files.upload_page`

**TEST_ENDPOINT_PREFIXES** (1): `/_test/`

Endpoints the interface switch does not gate (API, system and infrastructure; authentication and authorization are unchanged): **387**

### 10. Rendered navigation

`GET /` as an administrator returned 200; the sidebar renders **9 domains** and **33 entries**, all of them from the registry:

- Work
- Discover
- Ingest
- Analyze
- Classify
- Report
- Operate
- Administration
- Settings

Entries, in render order: `index`, `files.files_list`, `search_page`, `sources_list`, `sides_list`, `keywords_list`, `words_list`, `categories_list`, `email_words`, `notifications_page`, `signals_page`, `monitoring_page`, `operations_input_page`, `operations_import_page`, `archives_page`, `path_analysis_page`, `map_viewer_page`, `analysis_batch`, `analyst_categorization_page`, `file_classification_page`, `comprehensive_dashboard`, `reports_page`, `reports_dashboard_page`, `schedules_page`, `charts_dashboard`, `detection_page`, `operations_jobs_page`, `import_export_page`, `retention_page`, `users_page`, `audit_page`, `settings_page_direct`, `translations.translation_management_page`

Marked active on this page: `index`
<!-- END GENERATED APPLICATION EVIDENCE -->
