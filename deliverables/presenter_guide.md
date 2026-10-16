# Presenter guide — SYLTHARAE-Pro Technical Briefing

## Evidence and live-instance context

This 91-slide editable deck combines technical analysis with authentic screenshots from an isolated local application instance. Snapshot: `aa2b865a24c429e242a457a60d2aef84661389b2`; application version 2.2.0; capture date 2026-10-16.

**Runtime actually brought up:** Python 3.11 virtual environment; project base plus PDF, Office, OCR, ebook, audio, media, Waitress, and development extras; bundled ephemeral PostgreSQL 16.2 via `pgserver`; 39 migrations applied through `0039`; setup installer completed; Flask app served on port 5000. `verify_readiness.py` completed 31 checks with 0 failures. Live browser captures were made using Chromium/Puppeteer at desktop 1600×1050 CSS viewport (2000×1313 output, device scale 1.25) and mobile 390×844 CSS viewport (780×1688 output, device scale 2).

The test dataset is **synthetic**: two short fictional TXT files; source `Arena Synthetic Case File`; side `Synthetic Training Set`; no real case data. UI capture includes the temporary demo admin display name. Do not reuse the demo account or local development credentials outside this isolated preview.

## Narrative and slide guide

1. **Cover:** Frame this as an evidence-based technical review, not product marketing.
2. **Executive summary:** State the file-centric intelligence workflow and PostgreSQL/filesystem operational core.
3. **Agenda/evidence:** Differentiate repository evidence from recommendations.
4. **At a glance:** Python, Flask, PostgreSQL, browser UI, CLI and optional extras.
5. **Purpose:** Mixed-format collections, extraction and connection; personas are inferred rather than user-research validated.
6. **Value:** Concrete design mechanisms; no market or quantified performance claims.
7. **Architecture:** Browser → proxy → WSGI/Flask → route/service/core/pipeline/database → PostgreSQL/files.
8. **Repository:** Where to find each functional layer.
9. **Boundaries:** HTTP routes vs services vs domain/core vs migration/database ownership.
10. **Request path:** Setup/auth/authz/rate limit precede service action.
11. **Ingestion:** Code-derived general execution model; later product tour shows the actual synthetic example.
12. **Search:** Word/index candidate flow, filters and cursor pagination.
13. **Signals/reporting:** Versioned detection, rules/scenarios, alerts and reproducible report artifacts.
14. **Data model:** Hash/context/path distinction and coupled database/filesystem recovery.
15. **Jobs:** Durable state/events; cooperative cancellation; in-process worker constraint.
16. **Search/analytics:** Capabilities are demonstrated, not benchmarked.
17. **Readers:** Format support depends on extras, external engines and validation corpus.
18. **Configuration:** Precedence, live vs reserved names, proxy/secret concerns.
19. **Install:** Python, PostgreSQL, secure settings, setup flow; backend setup executed in local sandbox.
20. **Commands:** Repository-supported examples; broad test suites not run.
21. **Deployment:** Single process per DB and paired data backup.
22. **Troubleshooting:** Readiness checks, setup gate, path roots, OCR and job status.
23–24. **Security:** Source/tests evidence, trust boundaries and operational residual risk.
25. **Quality:** 31 readiness checks passed; this is not equivalent to the full pytest suite.
26. **Design choices:** Registries, migrations, resumability and single-process trade-off.
27–31. **Evaluation:** Hypothetical enterprise use cases, validation plan, risks, recommendations and conclusion.
32. **Live dashboard:** Authentic screenshot showing registry sidebar, operation summary and actual demo collection counts.
33. **Search:** Authentic query result view.
34. **Jobs:** Authentic actual job-list view.
35. **Settings:** Authentic page and visible tabs.
36. **Ingestion preflight:** Real dry-run state: 2 discovered, 2 to read, 0 unreadable, 770 B.
37. **Search result:** Actual two synthetic records returned for `CASE-DEMO-042`.
38. **Completed job detail:** Actual completed ingestion job (4/4 work units, 100%). The visible job ID is local demo data.
39. **Monitoring:** Actual running page, currently an empty/low-data state because no rules/geo signals were configured.
40. **Front-end source map:** Templates and component module locations.
41. **Responsive comparison:** Actual desktop and mobile File Library captures; spot-check only, not exhaustive breakpoint testing.
42–47. **Technical appendices:** Feature matrix, settings, dependencies, live execution/research limits, glossary/sources.
48–53. **Interface index:** 34 registry interfaces, endpoints and template sources.
54–87. **Visual interface reference:** Full-size authentic capture for each registry-declared screen—not a thumbnail grid. Empty states reflect the demo database.
88–91. **Additional interfaces:** Login, first-run setup, file details and full-content reader.

## Accuracy and disclosure

- `verify_readiness.py` passed 31 checks, including PostgreSQL connectivity, migration state, Flask route construction, authentication gates, representative ingest/search, archive/path defenses, rollback, rate limiting and startup configuration. A readiness probe record was cleaned by the check. This is not the project’s full test suite.
- The two-file intake was uploaded through the live UI; source/side were selected; preflight was run; a job completed; search returned the two synthetic records. No OCR sample was included.
- The UI screenshots are genuine pages served by the running local Flask application. They are not modified mockups. Screenshot annotations are separate slide elements, not edits to interface pixels.
- The local PG instance is ephemeral and no production topology, TLS proxy, persistent deployment, backup/restore or external security review was performed.
- `THIRD_PARTY_NOTICES.md`, `docs/LICENSING.md` and the AGPL-3.0-or-later obligations still apply to deployments.

## Screenshot files

The full screenshot archive is `interface_screenshots.zip`; the uncompressed source files are under `screenshots/`. `screenshot_manifest.csv` records route, interface, viewport, and data context. `interface_inventory.csv` maps registry entries to screenshot filenames and slides.
