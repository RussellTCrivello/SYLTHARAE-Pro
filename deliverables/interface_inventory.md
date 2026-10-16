# Front-end interface inventory and screenshot report

**Repository snapshot:** `aa2b865a24c429e242a457a60d2aef84661389b2` (2026-10-16). The generated `docs/INTERFACE_REGISTRY.md` declares 34 interfaces and 81 owned endpoints (33 active, 1 deprecated in this snapshot). The sidebar/navigation registry, page identity, interface permissions and declared dependencies are authoritative in `core/interfaces/`.

## Authentic capture method and limits

The application was installed and run locally with Flask and an ephemeral PostgreSQL 16.2 cluster. Captures were made directly from live Flask routes using Chromium/Puppeteer, not drawn or fabricated. Main desktop captures use 1600×1050 CSS pixels at 1.25 device scale (2000×1313 PNG); four mobile spot checks use 390×844 CSS pixels at 2× (780×1688 PNG). `screenshot_manifest.csv` records each image, route, viewport and data context; `interface_screenshots.zip` bundles the image files. `interface_inventory.csv` maps every registry interface to its image, source template and full-size slide reference.

The gallery uses a synthetic two-file training dataset only. Some screens therefore show empty/low-data states. The setup wizard capture is the actual first-run screen before the setup installer completed. Desktop screen captures exist for every registry interface; mobile capture coverage is limited to File Library, Search, Input/Ingestion and Settings. This is a visual inspection, not exhaustive browser, accessibility or breakpoint testing.

## Shared shell and implementation

`templates/base.html` provides branding/logo, registry-driven sidebar, breadcrumbs, notification entry point, locale controls, toast region, account menu and responsive menu shell. `templates/components/sidebar_nav.html` renders the interface registry's navigation model. CSS/JS include responsive behavior, centralized status vocabulary, confirmation dialogs, search control, pagination, file navigation, record actions and interaction/feedback components.

## Registered interface groups and implementation paths

| Group | Important screens and source | Exposed capabilities |
|---|---|---|
| Work / discovery | `Analysis/dashboard.html`; `file/files_list.html`; `Search/search.html`, `search_advanced.html`, `search_enhanced.html`, `saved_searches.html`; Sources, Side, Keyword, Word, Category, Email Words and Notifications templates | Overview, file collection, search variants, source/side, vocabulary/category exploration, alerts. |
| Analyze / classify | `Analysis/analysis_batch.html`, `charts_dashboard.html`, `comprehensive_dashboard.html`, `file_classification.html`, `path_analysis.html`; `Analyst/analyst_categorization.html`; `map/map_viewer.html` | Batch work, analytics, classification, path/geo exploration and analyst categorization. |
| Operate / ingest | `Operations/input.html`, `import_center.html`, `jobs.html`, `job_detail.html`; `Signals/detection.html`, `signals.html`; `Monitoring/monitoring.html`; `ImportExport/import_export.html`; `concurrency/dashboard.html` | Intake, import, persistent jobs, signal/detection views, monitoring, import/export, concurrency. |
| Report / administer | Reports, Schedules and Retention templates; `Settings/settings.html`, `translation_manager.html`; `auth/users.html`, `audit.html` | Report/dashboards/schedules, retention, configuration, translations, accounts and audit. |
| Supporting screens | `Setup/install_wizard.html`; `auth/login.html`; `file/file_detail.html`, `full_content.html`; `403.html`, `404.html`, `500.html`; shared components under `templates/components/` | First-run bootstrap, authentication, file detail/reader, error states, filters, actions, status and feedback patterns. |

## End-to-end UI behavior observed live

1. Used the real `/operations/input` interface to select two synthetic files and source/side.
2. Ran the live preflight; it returned two discovered, two to read, zero unreadable, 770 B.
3. Started the actual ingestion job; the job detail reached `COMPLETED`, 100%, 4/4 work units.
4. Queried `CASE-DEMO-042` in the live Search screen; two real demo rows appeared, with source/side/date and record actions.
5. Opened file detail and full-content routes for the first synthetic record.

All shown file text, source/side names and counts are synthetic and do not represent a real case or customer corpus. The local demo admin label is visible in captures; no password is embedded in screenshots.
