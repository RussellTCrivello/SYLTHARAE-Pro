# C. Feature Verification Matrix

**Verification basis:** static source inspection only. Runtime verification (frontend, API, persistence) is BLOCKED because the app cannot start without PostgreSQL (F-01) and no browser is available (F-04). Statuses reflect what could be confirmed from the current checkout, not executed behavior.

Interface source of truth: `core/interfaces/registry.py` (30 interfaces + 1 feature across 10 domains) and `core/interfaces/inventory.py` (endpoint classification + coverage guardrail).

| # | Feature (interface) | Domain | Route (endpoint) | Frontend template | Required role | Frontend coverage | API coverage | Business logic coverage | Persistence coverage | Verification status | Evidence |
|---|---------------------|--------|------------------|-------------------|---------------|-------------------|--------------|-------------------------|----------------------|---------------------|----------|
| 1 | Dashboard | WORK | `index` | `Analysis/dashboard.html` | any | static | dashboard.py: `index()` | aggregates | reads paths/contents | BLOCKED (no runtime) | registry, dashboard.py |
| 2 | File Library | DISCOVER | `files.files_list` | `file/files_list.html` | any | static | Api/routes files blueprint | file routing | reads paths | BLOCKED | registry |
| 3 | Search | DISCOVER | `search_page` (+ advanced/enhanced/saved) | `Search/search*.html` | any | static | search.py | core/search | reads contents/words | BLOCKED | registry, search.py |
| 4 | Sources | DISCOVER | `sources_list` (+ add/detail/edit) | `Sources/sources_list.html` | any | static | sources.py | sources service | sources table | BLOCKED | registry |
| 5 | Sides | DISCOVER | `sides_list` (+ add/detail/edit) | `Side/sides_list.html` | any | static | sides.py | sides service | sides table | BLOCKED | registry |
| 6 | Keywords | DISCOVER | `keywords_list` (+ detail) | `Keyword/keywords_list.html` | any | static | keywords.py | keyword service | keywords table | BLOCKED | registry |
| 7 | Words | DISCOVER | `words_list` (+ detail) | `Word/Word_list.html` | any | static | words.py | word service | words table | BLOCKED | registry |
| 8 | Categories | DISCOVER | `categories_list` (+ words) | `Category/categories_list.html` | any | static | categories.py | category service | categorys/words_categorys | BLOCKED | registry |
| 9 | Email Words | DISCOVER | `email_words` | `email_words/email_words.html` | any | static | (route) | — | — | BLOCKED | registry |
| 10 | LEXIS Cosmos | CLASSIFY | `lexis_cosmos_page` | `Lexis/cosmos.html` | any | static | lexis_cosmos.py | lexis_queries | taxonomy tables | BLOCKED | registry |
| 11 | Analyst Categories | CLASSIFY | `analyst_categorization_page` | `Analyst/analyst_categorization.html` | any (depends file_library) | static | analyst_categories.py | analyst service | analyst_* tables | BLOCKED | registry |
| 12 | Notifications | DISCOVER | `notifications_page` | `Notifications/notifications.html` | any | static | notifications.py | notification service | notifications table | BLOCKED | registry |
| 13 | Horizon & Signal Explorer | DISCOVER | `signals_page` | `Signals/signals.html` | any | static | signals.py | detection service | content_signals | BLOCKED | registry |
| 14 | Monitoring | DISCOVER | `monitoring_page` (+ depends signal_horizon,notifications) | `Monitoring/monitoring.html` | any | static | monitoring.py | scenario/rule engine | scenarios/evaluations | BLOCKED | registry |
| 15 | Input / Ingestion | INGEST | `operations_input_page` (+ upload control) | `Operations/input.html` | any | static | operations_pages.py | ingestion service | jobs/paths/contents | BLOCKED | registry |
| 16 | Import Center | INGEST | `operations_import_page` | `Operations/import_center.html` | any | static | operations_pages.py | import service | — | BLOCKED | registry |
| 17 | Archives / File Mgmt & Analysis | ANALYZE | `archives_page` (+ depends file_library) | `file/File_Management_Analysis_System.html` | any | static | archives.py | analysis service | hashs/paths | BLOCKED | registry |
| 18 | Path Analysis | ANALYZE | `path_analysis_page` (+ depends file_library) | `Analysis/path_analysis.html` | any | static | path_analysis routes | path service | paths | BLOCKED | registry |
| 19 | Map Viewer | ANALYZE | `map_viewer_page` (+ depends archives,file_library) | `map/map_viewer.html` | any | static | map_api.py | geo service | geo_places | BLOCKED | registry |
| 20 | Batch Analysis | ANALYZE | `analysis_batch` (+ depends file_library) | `Analysis/analysis_batch.html` | any | static | analysis.py | batch processing | jobs | BLOCKED | registry |
| 21 | Classification | CLASSIFY | `file_classification_page` (+ depends file_library,words) | `Analysis/file_classification.html` | any | static | classification routes | classification service | categorys/words | BLOCKED | registry |
| 22 | Comprehensive Dashboard | REPORT | `comprehensive_dashboard` (+ depends file_library) | `Analysis/comprehensive_dashboard.html` | any | static | analytics.py | analytics service | aggregates | BLOCKED | registry |
| 23 | Reports | REPORT | `reports_page` (+ depends search,jobs) | `Reports/reports.html` | any | static | reports routes | reporting service | report runs | BLOCKED | registry |
| 24 | Reports Dashboard | REPORT | `reports_dashboard_page` (+ depends reports,jobs,schedules) | `Reports/dashboard.html` | any | static | reports routes | reporting service | report runs | BLOCKED | registry |
| 25 | Charts Dashboard | REPORT | `charts_dashboard` (+ depends file_library) | `Analysis/charts_dashboard.html` | any | static | analytics.py | analytics service | aggregates | BLOCKED | registry |
| 26 | Retention | ADMINISTRATION | `retention_page` (+ depends jobs,reports) | `Retention/retention.html` | admin | static | retention.py | retention service | pruning/audit | BLOCKED | registry |
| 27 | Schedules | REPORT | `schedules_page` (+ depends reports,jobs,monitoring) | `Scheduling/schedules.html` | any | static | schedules.py | scheduler | job_schedules | BLOCKED | registry |
| 28 | Detection | OPERATE | `detection_page` (admin; depends signal_horizon,jobs) | `Signals/detection.html` | admin | static | signals.py | detection service | content_signal_runs | BLOCKED | registry |
| 29 | Jobs | OPERATE | `operations_jobs_page` (+ job detail) | `Operations/jobs.html` | any | static | operations_api/pages | JobManager | jobs/job_events | BLOCKED | registry |
| 30 | Import/Export (deprecated) | OPERATE | `import_export_page` (admin, DEPRECATED) | `ImportExport/import_export.html` | admin | static | import_export.py | export service | — | BLOCKED | registry |
| 31 | User Management | ADMINISTRATION | `users_page` (admin) | `auth/users.html` | admin | static | auth.py | auth service | users/sessions | BLOCKED | registry |
| 32 | Audit Log | ADMINISTRATION | `audit_page` (admin, read-only) | `auth/audit.html` | admin | static | audit.py | audit service | audit_log | BLOCKED | registry |
| 33 | Settings | SETTINGS | `settings_page_direct` (admin) | `Settings/settings.html` | admin | static | settings routes | settings service | settings.json | BLOCKED | registry |
| 34 | Translation Management | SETTINGS | `translations.translation_management_page` (admin) | `Settings/translation_manager.html` | admin | static | translations routes | translation service | translation_overrides | BLOCKED | registry |
| — | Concurrency Monitor (INTERNAL) | INTERNAL | `concurrency.dashboard` (admin) | — | admin | static | concurrency.py | resource coordinator | runtime state | BLOCKED | registry |
| — | Login / First Admin / Setup | — | `auth.login`, `setup.setup_page` | `auth/login.html`, `Setup/install_wizard.html` | public (setup gated to zero-users) | static | auth.py, setup.py | bootstrap_admin | users (first admin) | BLOCKED | registry, setup.py |
| — | Page Tips (feature) | — | — | — | — | — | — | — | — | source only | registry FEATURES |

**Missing verification boundaries (every row above):**
- No frontend page was rendered in a browser (F-04).
- No API endpoint was called; no status code, payload, or header observed (F-01).
- No database row was read/written; no persistence confirmed (F-01).
- The interface inventory's declared endpoint→route ownership was not validated against a live URL map (app cannot import).
