# Changelog

Notable changes to SYLTHARAE, newest first. The version in `version.py` and
`pyproject.toml` is the single source of truth for what a build is; this file
records what changed, and every entry below is verifiable from the commit or the
working tree that carries it.

Format: a heading per version, with an explicit state — **released** or
**unreleased** — and entries grouped as Added, Fixed, Changed, Removed or
Database. A change is listed as released only once it is in a tagged build.

## v2.2.0 — unreleased

Version 2.2.0 is the value declared in `version.py` and `pyproject.toml` (build
date 2026-09-26). The changes below are on the current branch and are **not**
released; the schema migrations in particular have been verified against
disposable databases, not applied to a deployment.

### Database

* **m0038 `redundant_enforcement_removal`** — nine structures were enforcing or
  indexing exactly what another structure already enforced or indexed:
  `hash_contexts` carried its uniqueness under two constraint names (m0011's
  `uq_hash_contexts_identity` and m0013's re-declaration
  `uq_hash_contexts_hash_source_side`), and eight indexes had a byte-identical
  shape to a surviving index or to the index behind a `UNIQUE` constraint. The
  redundant member of each pair is dropped; the enforcing, consistently named
  survivor is kept, and `idx_words_hashs_word_hash` (m0036, reversed column
  order) is deliberately untouched because it answers word-first lookups the
  constraint's index cannot. The migration refuses to drop anything whose
  survivor is missing or shape-drifted, and `downgrade()` recreates all nine
  from the original DDL. No data is touched.
* **m0039 `vocabulary_constraints`** — four columns accepted any text while the
  application understands a fixed set: `alerts.type`, `alerts.priority`,
  `jobs.status` and `job_events.event_type`. Each now has a CHECK generated at
  migration time from the module that owns the values (`NotificationType`,
  `NotificationPriority`, `job_state.ALL_STATES`, `job_state.EVENT_TYPES`), added
  `NOT VALID` and then validated inside the migration's transaction. A value
  outside the vocabulary used to be stored silently and then never match a
  filter — an invisible notification, a job the terminal-state sweep never
  picks up. Before adding a constraint the migration counts violating rows and
  refuses with the offending values listed, changing nothing.
* **`job_state.EVENT_TYPES` was incomplete** — it listed 18 of the 21 event
  types `services/jobs/manager.py` publishes (`PROGRESS`, `JOB_PAUSED` and the
  terminal status were missing), so a CHECK built on the old tuple would have
  rejected the job manager's own events. Corrected first, and
  `tests/unit/test_job_event_vocabulary.py` now derives the emitted set from the
  writer call sites so the constant and the writers cannot drift apart again.
* `docs/reference/DATABASE_SCHEMA.md` regenerated from a freshly migrated
  database; `tools/docs/generate_schema.py --check` is clean.

### Fixed

* **Ingestion batch report read a table that no longer exists** —
  `services/reporting/ingestion_batch.py::_query_categories` still joined
  `words_paths` / `wp.path_id`, which m0011 renamed and re-keyed, so every batch
  report logged `Batch report query failed: categories` and rendered an empty
  categories section. The join now walks `paths → hash_contexts → words_hashs`,
  the shape the neighbouring keyword query already used.
* **Place mentions read through two access paths** — `_query_places` read the
  legacy table `path_geo_mentions_m0015` directly, bypassing the
  `path_geo_mentions` view's coverage, confidence and provenance rules. It now
  reads the view, so one entity has one read path.
* **A UTF-8 BOM broke `Api/routes/archives_api.py`** — the file began with
  U+FEFF, so anything that read and parsed it failed with
  `SyntaxError: invalid non-printable character U+FEFF (line 1)`. Removed, and
  `tests/unit/test_experience_contract.py` covers the parse.
* **Two interfaces shared a keyboard sequence** — the map viewer declared `g m`,
  which Monitoring already owned; `validate_registry` rejects a duplicate, and a
  user pressing it would land on whichever the palette listed first. The map
  takes `g g`.
* **Stored monitoring rules could not be read back** — `SignalFilter.canonical()`
  writes the match-mode keys (`evidence_mode`, `surface_mode`, `value_mode`) into
  every stored rule, and `parse_signal_filter` refused them, so a rule (or a
  scenario condition) could not be parsed from its own stored form. The parser
  now accepts them, together with `surface_text` and `value_text`, matching what
  the Explorer's parser accepts.
* **Search short-circuit answered zero without looking** — a term missing from
  the indexed word vocabulary was treated as proof that the query is empty, but
  interactive search also matches file name, file type, source, side, raw text
  and tokens. A filename fragment such as `e04c07fc` in
  `alpha-report-e04c07fc.txt` matched files, yet the short-circuit returned no
  results without running a query. The short-circuit now proves its case with a
  bounded existence probe per unresolved term, so a genuinely empty search still
  skips the expensive work while a non-empty one is answered correctly.
* **A test left the shared session database with the wrong schema** — replaying
  m0013 (as `tests/unit/test_relationship_deduplication.py` does to exercise its
  consolidation logic) re-creates that migration's own constraint name and does
  not restore the canonical one, so the `hash_contexts` uniqueness was missing
  for every later test in the session. Three tests failed when the suite was
  ordered that way. The cleanup now restores the canonical constraint and
  re-applies m0038, and a new test pins it.
* **Component-library pins and the document had drifted** — `counts()` in
  `core/frontend/component_audit.py` was right and the test's expectations were
  stale; the pins and `docs/COMPONENT_LIBRARY.md` were corrected (never the
  templates).
* **Licensing gates** — `THIRD_PARTY_NOTICES.md` was missing although
  `pyproject.toml` declares it, README carried no licence statement, and the
  first-run setup page — the only page a fresh install can reach — rendered
  neither the AGPL section 13 source link nor the running version. All three are
  repaired; `tests/unit/test_licensing.py` passes.
* **OCR degraded to "no engine" on headless Linux hosts** —
  `rapidocr-onnxruntime` declares `opencv-python` (the GUI build) as a
  dependency while the project pins `opencv-python-headless`. Both distributions
  unpack into the same `cv2` directory, so whichever is installed last owns the
  files; when the GUI build wins, `import cv2` raises
  `ImportError: libGL.so.1: cannot open shared object file`, rapidocr reports
  itself unusable, and every image or scanned PDF is stored as
  `ocr_required_engine_unavailable` with no other symptom — an operator sees a
  host that "has OCR installed" extract nothing. The trap, the check
  (`python3 -c "import cv2"`) and the repair
  (`pip uninstall -y opencv-python && pip install --no-deps --force-reinstall opencv-python-headless`)
  are now documented in [docs/CONFIGURATION.md](docs/CONFIGURATION.md). Verified
  on the affected host: 179 of the 180 OCR-reader tests that failed with it pass
  after the repair.
* **Operator remediation named an undocumented setting** — the OCR self-check's
  `invocation_failed` advice pointed at `TESSERACT_CMD`, which
  `core/ocr/engines.py` honours, but no document named it, so
  `tools/ci/ocr_selfcheck.py` sent the operator to a setting they could not look
  up. `TESSERACT_CMD` and `TESSDATA_PREFIX` are now documented in
  [docs/CONFIGURATION.md](docs/CONFIGURATION.md) with their readers;
  `tests/unit/test_ocr_selfcheck.py::test_remediations_name_only_real_settings`
  pins that.
* **`tests/integration/test_report_catalog_api.py` pinned superseded versions** —
  the catalog test still expected `keyword_intelligence@1` and
  `category_analysis@1` in `/api/reports/definitions` and a manifest reporting
  `version: 1`, but both families were revised (v2 active, v1 `superseded`) and
  `server.visible_to` offers active versions only — the same contract
  `tests/unit/test_report_catalog_keyword_category.py` and
  `tools/verify/runtime_check_keyness.py` ("v1 superseded, not offered") pin.
  The test now asserts the active versions *and* that no superseded version is
  offered, and the manifest assertion compares the recorded version with the
  version the run used. Four failures gone; no production code changed.
* **A translation call offered its own lookups as messages (NARR-02)** —
  `core/analytics/narrative.py` passed `record["msgid"]` /
  `record["msgid_plural"]` straight into `ngettext`, and a message extractor
  walks a translation call's arguments for string constants, so every catalog
  gained a message pair whose text was the *keys*:

  ```
  msgid "msgid"
  msgid_plural "msgid_plural"
  ```

  `msgmerge` then matched that pair onto the existing "Side" entry — the pair
  and `Side` share the key `msgid` — and marked the real entry fuzzy. Babel does
  not compile fuzzy entries, so a reviewed translation that four locales already
  had was silently dropped from the shipped `.mo` and the page fell back to
  English: `gettext('Side')` returned `'Side'` in Arabic, Hebrew, Persian and
  Croatian before this change and returns `'الجوانب'`, `'צד'`, `'طرف'`,
  `'Strana'` after it. The same shape existed
  in `core/reporting/render.py` (`t.gettext(a["title"])`,
  `t.gettext(report["description"])`, `t.gettext(report["help_summary"])`),
  `core/reporting/entry_template.py` and `Api/routes/reports.py`. Every value is
  now read into a local before the call - behaviour is unchanged, and the
  extraction of `narrative.py` produces no message at all. The three artifact
  entries were pruned from all five catalogs with
  `scripts/catalog_maintenance.py` (obsolete history intact, `.mo` recompiled).
  `tests/unit/test_catalog_extraction.py` pins the mechanism (an AST scan for a
  lookup inside a message argument, plus a deterministic-extraction check), and
  the fix was verified by reintroducing the defect: both tests fail, then pass
  again once it is restored.
* **Operator documentation pointed at a file that does not exist** —
  `scripts/reset_admin_password.py` (four messages), `tools/ci/ocr_selfcheck.py`
  (its docstring and the OCR remediation the self-check prints),
  `tools/licenses/check_licenses.py` and `static/js/pages/install-wizard-page.js`
  all sent the reader to `docs/INSTALL.md`, which this repository has never
  contained - the OCR advice was therefore unanswerable and the recovery
  procedure unreachable. Each now points at the document that holds it
  (`docs/OPERATIONS.md` — which gains the administrator-password recovery
  procedure the script implements — or `docs/CONFIGURATION.md`, which documents
  the OCR settings).
* **Two integration tests depended on their neighbours** — `tests/integration/test_db_integrity_audit.py`
  audits a *freshly migrated* database, but ran against the session database
  shared with eleven other files in its batch: rows left behind by a neighbour
  showed up as a `required_in_practice` finding and an index set left behind by
  a migration-replay test as a duplicate shape, so the file passed alone and
  failed in a batch. It now creates a database of its own through
  `database.bootstrap` and points the tool at it with `DB_*` (batch 2: 2 failed
  → 118 passed). `tests/integration/test_retention_pg.py` seeded alerts with a
  made-up type (`'retention-test'`), which m0039's vocabulary constraint refuses;
  the fixture now uses a real `NotificationType` value, and the test's subject -
  retention pruning by age - is unchanged.

### Added

* **LEXIS Cosmos** (`/lexis`, registry `lexis_cosmos`, CLASSIFY) — the taxonomy
  browser from the supplied single-file design, rebuilt as a translated page
  over the whole Q1.1-Q11.2 SQL catalogue. `Api/services/lexis_queries.py` holds
  the statements, `Api/services/lexis_cosmos.py` the read/write service and
  `Api/routes/lexis_cosmos.py` 43 rules (`/api/lexis/{health,lenses,tree,
  outline,find,filter-options,scope,search,facets,file/<id>,file/<id>/text,
  file/<id>/matches,files/<id>/{rename,duplicate},files/bulk-{delete,side},
  manage/{dashboard,files},export/{review,text,originals,structured,columns},
  taxonomy/{categories,categories/<id>,categories/<id>/color,duplicate,
  keywords,keywords/<id>,terms},views,views/<id>,views/<id>/touch,activity}`).
  Every URL the page script uses is rendered into it (`_page_payload()`), so no
  endpoint is reachable only from documentation: the lens strip reads Q2.1, the
  viewer's "why it matched" table reads Q5.4, and the manage tree's colour
  action writes Q8.5. 307 strings are translated into ar/he/fa/hr by
  `scripts/fill_lexis_cosmos_i18n.py` (0 missing, 0 unused rows), and
  `tests/integration/test_lexis_cosmos_api.py` (28 tests) walks the real joins
  against a seeded database. The "empty items" decision is one piece of state
  with two controls - the canvas button and a switch in the sidebar's filter
  cards, kept in step by `syncEmptyControls()` - and it hides categories and
  subcategories that hold no files in scope, not just bare terms; turning it on
  while a now-empty category is in focus steps the view up to its nearest
  visible ancestor instead of leaving the chart pointing at a card that is no
  longer part of the structure. Choosing a file type (or a source, a side, a
  date range, a name) now narrows the *structure* as well: the filter controls
  went through `refreshPanel()` only, which re-read the file list and left the
  cached tree on the canvas, so a category whose every file the filter had
  excluded stayed on screen with its unfiltered counts. All of them now call
  `filtersChanged()`, which invalidates the tree and re-reads it; a node the new
  envelope emptied is also dropped from the expanded set. Three defects a
  screenshot pass exposed are
  fixed with it: a lens card claimed "0 terms · 0 files" because it read
  `info.counts`, a field no node carries (Q2.1 answers `term_count` and
  `file_count`); breadcrumb, card and sidebar title read "words" because
  `nodeLabel()` trusted the payload's machine name over the page's own name for
  the lens; and the chart keyed its geometry by node id, so one document
  matching two expanded terms produced a single file card with the other branch
  pointing at nothing (positions are now addressed by path). The Depth selector
  also reports the depth actually drawn instead of the depth last chosen, and
  the page's CSS/JS carry a cache-busting `?v=` so an upgrade cannot be served
  from a stale browser cache. Two defects the seeding exposed are fixed in the
  same change: the Q2.2/Q2.3 category trees joined subcategories with a bare
  `LEFT JOIN`, so a main category holding both direct terms and subcategories
  reported zero terms and zero files and disappeared under `hide_empty` (now a
  `UNION ALL` over the main row and its subs), and the keyword term list carried
  a raw psycopg2 `memoryview` into the JSON response, which made every
  keyword-subcategory request answer 500.
* `THIRD_PARTY_NOTICES.md`: vendored front-end assets and fonts with the
  versions and licences their own shipped headers state, and the Python
  dependency closure grouped by the licence expression each distribution
  declares (112 compatible, 0 incompatible, 0 unknown via
  `tools/licenses/check_licenses.py`).
* `docs/LICENSING.md`, `docs/CONFIGURATION.md`, `docs/SECURITY.md`,
  `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/OPERATIONS.md`,
  `docs/TESTING.md` — the operational and architectural documentation the tests
  require; `docs/ARCHITECTURE.md` carries a job-state diagram verified against
  `services/jobs/job_state.py`, and `docs/SECURITY.md` quotes the
  Content-Security-Policy the application actually serves.
* `docs/EXPERIENCE_CONTRACT.md`, `docs/ACTION_SURFACE_AUDIT.md`,
  `docs/SCREEN_INSPECTOR_EVIDENCE.md` — generated from the registries, with the
  hand-written half free of counts.
* `scripts/catalog_maintenance.py` — the catalogs' maintenance tool. It
  classifies every entry (approved / empty / fuzzy / obsolete / artifact),
  restores an empty or fuzzy entry from that catalog's own obsolete block when
  the msgid is identical and the `%(name)s` placeholders agree, prunes entries
  an extractor made out of code identifiers, reports what still needs a human
  translation **by language**, and refuses to write when a catalog's obsolete
  history would shrink. `--check` (default) changes nothing; `--write` writes
  and recompiles every `messages.mo`; both are idempotent. It never fills a
  missing translation with English.
* `tools/db/integrity_audit.py` — a read-only database audit (orphans,
  duplicate business keys, vocabulary drift, unattributable audit rows,
  duplicate index shapes, required-in-practice NULLs) with `--json` and
  `--counts`, suitable for running against a deployment.
* `deploy/nginx/syltharae.conf` and `deploy/systemd/syltharae.service` — the
  supported deployment shape, covered by the deployment and proxy tests.
* `docs/database/` — the database audit deliverables (inventory, responsibility
  matrix, relationship integrity, duplication register, canonical entity map,
  migration plan, repair report, final integrity report).

### Changed

* **Advanced search results viewport.** On desktop (1200px and wider) the results
  header and pagination stay in place while the result list scrolls on its own;
  the search controls above scroll in their own region. Narrower screens keep the
  normal page flow.
* **Results per page.** The advanced search offers 20, 50, 100, 200 or 500 results
  per page (default 20). The search API and the "Current page only" export accept
  up to 500 (previously 200). Larger pages are rendered in full; list virtualization
  is not implemented (see `docs/search/PERFORMANCE_ARCHITECTURE.md`).


* `verify_readiness.py` pins the surviving index and constraint names
  (`hashs_hash_key`, `uq_hash_contexts_identity`) instead of the duplicates
  m0038 removed.
* Translation catalogues refreshed for the live/obsolete split; `messages.po`
  and `messages.mo` are kept in step for every language. Arabic, Hebrew and
  Persian keep their right-to-left layout.
* Performance records annotate the two index names m0038 consolidated
  (`docs/perf/CAPACITY_REPORT.md`, `docs/search/PERFORMANCE_ARCHITECTURE.md`):
  the measurements are quoted as taken, with the note that the successor index
  answers the same plan.

### Verified in this revision

Everything here was run, not reasoned about; the commands are in
`docs/TESTING.md` and `docs/OPERATIONS.md`.

* **The documented live protocol passes end to end** against a real server
  (Waitress, `FLASK_ENV=production`, `TRUSTED_PROXY_COUNT=1`, PostgreSQL 16.2):
  the setup wizard installs a **fresh empty database** over HTTP (39 migrations
  applied, `.env` written, a second install refused with 409) - 4/4 checks;
  `run1` - 53/53; restart; `run2` - 53/53. The pass covers login/CSRF/security
  headers, ingestion of text/CSV/DOCX/ZIP/PNG with OCR provenance, duplicate
  suppression on re-ingestion, upload staging, search (including the deferred
  snippet path), per-file analysis, original-file download, the event stream,
  settings/search exports, and the analyst lifecycle (created, gated until the
  password change, denied admin settings, old password refused, logout,
  session invalidation) with the audit log recording the real client address.
* **A fresh database migrates two ways**: by the wizard (above) and by the
  application at startup (`Applied schema migrations 0001…0039 … schema now at
  version 0039`), and a restart reports `Database schema is up to date
  (version 0039)`. The startup also prints the m0039 vocabularies as enforced
  (`alerts.type: 12 allowed values, 0 row(s) validated by ck_alerts_type`, and
  the same for `alerts.priority`, `jobs.status`, `job_events.event_type`).
* **Administrator password recovery works on a live database**:
  `scripts/reset_admin_password.py --list`-style reporting found the account (and
  its failed-login count), reset the password, revoked sessions, cleared the
  lockout, and exited 0; the temporary password then forced a change
  (`403 password_change_required`), and changing it cleared the flag.
* **This environment needs `waitress` for the production shape**
  (`pip install -e ".[server]"`). Without it the application warns, states the
  remediation and falls back to the development server, which discloses its own
  version in the `Server` header (`Werkzeug/3.1.9 Python/3.11.2`); under Waitress
  the header is the application's own `SYLTHARAE` (`apps/web/serve.py`, `ident=`).
  Deploying without the `.[server]` extra is therefore a real, visible downgrade
  in header hygiene, not only a performance one.

### Known issues at this revision

Recorded so this changelog is not mistaken for a stability claim:

* **The translation catalogs are incomplete.** 42 of the 46 tests in
  `tests/integration/test_translation_coverage.py` pass;
  `test_no_catalog_entry_is_empty_or_fuzzy` fails for all four maintained
  catalogs, and the counts are now the measured ones after this revision's
  maintenance pass: Arabic **319**, Hebrew **294**, Persian **294**, Croatian
  **361** entries empty or fuzzy (was 449 / 296 / 296 / 501 before the obsolete
  restores and the artifact prune). The gap is real rather than cosmetic: the
  fuzzy entries carry the text of a *similar older* msgid (Hebrew
  `Screen Inspector` → "screen translations", `Element` → "event", `State` →
  "began") - so approving fuzzy entries wholesale, as an earlier attempt in this
  branch did, ships text that belongs to a different msgid; that attempt was
  reverted and the tool now restores only entries whose msgid is identical.
  Because Babel does not compile fuzzy entries, the runtime effect *today* is
  English fallback rather than wrong text (`gettext('Screen Inspector')` returns
  the English string; the risk is what an approval pass would introduce). Almost
  all of the gap is live text: 318/319 (ar), 293/294 (he, fa) and 360/361 (hr)
  are msgids the current sources reference (extraction: 3 526 msgids). **What
  remains needs authored translations**, one language's own reviewers at a time:
  no translation service is reachable from this environment and none was
  fabricated, because unreviewed machine output in a shipped catalogue is worse
  than a visible English fallback. `python3 scripts/catalog_maintenance.py`
  prints the exact counts per language and the entries behind them; `--write`
  cannot close them by itself, by design.
* `tests/integration/test_places_pg.py` passes on its own (21 passed) and inside
  the clean integration batch that contains it (128 passed with
  `test_places_crud_pg.py`). The two failures recorded earlier came from a
  contaminated run - two batch runners executing against the same disposable
  servers - and could not be reproduced sequentially; the gazetteer seed
  fingerprint test (`test_migration_loaded_the_seed_and_the_fingerprint_describes_the_rows`,
  defect #9) passes with them.
* Production data integrity is unverified: the audit checks have run against
  freshly migrated, empty databases only. Running
  `python3 tools/db/integrity_audit.py --json` against a real deployment is what
  turns those from unknown into measured.
* Three decisions are pending with the repository owner: whether
  `alerts.file_name` / `file_path` are historical snapshots or should be read
  through `paths` (DB-4); whether the `job_id` provenance columns should carry
  foreign keys given that job retention prunes jobs (DB-5); and whether
  `database/SYLTHARAE.sql` should be regenerated from the migrations or retired
  (DB-6) — it is a stale schema-only snapshot and is not a deployment authority.
