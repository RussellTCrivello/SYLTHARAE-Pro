# Interface and Table Coverage Matrix

Status of the system-wide audit. Built from a real-browser crawl of the running
app (`tests/browser`-style inventory, admin account, seeded browser database)
and from the route and template map of the code. Each row says what was
observed, and what has been **behavior-tested** (clicked, paged, sorted,
searched). A crawl only proves that a display loads.

Legend for **Test status**
- `behavior-tested`: exercised in a real browser (Show More, page size, paging, sort, filter, search, reload, error capture).
- `crawl-only`: loaded in a real browser; table, controls and console recorded; interactions not yet exercised.
- `blocked`: cannot be exercised with the current seed data, or needs an interaction not yet scripted.
- `defect`: a verified defect is open on this display.

## 1. Scope mapping

| Interface named in the directive | Route(s) | Template |
|---|---|---|
| File Library | `/files` | `file/files_list.html` |
| Browse by File Type | `/files/types`, `/files/types/<type>/documents` | `file/file_types*.html` |
| Advanced Search | `/search/advanced` (results in the view menu) | `Search/…` |
| Search Files | `/search` (results in the view menu) | `Search/…` |
| Enhanced Search | `/search/enhanced` (results in the view menu) | `Search/…` |
| Keywords | `/keywords`, `/keywords/<id>`, `/keywords/<id>/documents` | `Keyword/keywords_list.html`, `Keyword/keyword_detail.html` |
| Words | `/words`, `/words/<id>`, `/categories/<id>/words` | `Word/Word_list.html`, `Word/Word_detail.html` |
| File Management and Analysis | `/archives` (tabs: Category, Keywords, Titles, Sources, Sides, Relations, Geolocation, File Types) | `file/File_Management_Analysis_System.html` |
| Analyst Categorization | `/analyst/categorization` | `Analyst/…` |
| Reports | `/reports` | `Reports/…` |
| Report Catalog | `/reports/dashboard` (`catalogTable`) | `Reports/dashboard.html` |
| Schedules | `/schedules` | `Scheduling/…` |
| Reports Dashboard | `/reports/dashboard` | `Reports/dashboard.html` |
| Detection | `/signals/detection` | `Signals/…` |
| Jobs | `/operations/jobs`, `/operations/jobs/<id>` | `Operations/…` |
| Retention | `/retention` | `Retention/…` |
| User Management | `/users` | `…` |
| Audit Log | `/admin/audit` | `…` |
| Translation Management | `/translations/manage` | `…` |
| Horizon & Signal Explorer | `/signals` | `Signals/…` |

Sides and Sources are also File Management tabs, and their list pages are
`/sides` and `/sources`.

## 2. Crawl results (load, 26 URLs, after commit 8a72e9e)

| Display | URL | Tables on load (data rows) | Controls seen | Console / page / HTTP errors |
|---|---|---|---|---|
| File Library | `/files` | `filesTable` (50 of 382 files) | Show More, per-page `filesTablePerPage` (default 50) | 0 / 0 / 0 |
| Browse by File Type | `/files/types` | `fileTypesTable` (1) | per-page `fileTypesTablePerPage` | 0 / 0 / 0 |
| Search Files | `/search` | none before a search | — | 0 / 0 / 0 |
| Advanced Search | `/search/advanced` | none before a search | Show more content (disclosure) | 0 / 0 / 0 |
| Enhanced Search | `/search/enhanced` | none before a search | — | 0 / 0 / 0 |
| Keywords | `/keywords` | `keywordsTable` (50 on this account) | Show More, Previous, Next, per-page `perPage` | 0 / 0 / 0 |
| Keyword detail | `/keywords/18` | none (detail) | — | 0 / 0 / 0 (was 3 / 1 before 8a72e9e) |
| Words | `/words` | `wordsTable` (10) | Show More, Previous, Next, per-page `perPage` | 0 / 0 / 0 |
| Word detail | `/words/21` | none (detail) | — | 0 / 0 / 0 |
| File Mgmt (`/archives`) | `/archives` | none on load (tab content loads on selection) | Previous/Next File, per-page section | 0 / 0 / 0 |
| Sides | `/sides` | `sidesTable` (10) | Show More, Previous, Next, `sidesPerPage` | 0 / 0 / 0 |
| Side detail | `/sides/42` | none (detail) | — | 0 / 0 / 0 |
| Sources | `/sources` | `sourcesTable` (10) | Show More, Previous, Next, `sourcesPerPage` | 0 / 0 / 0 |
| Source detail | `/sources/62` | none (detail) | — | 0 / 0 / 0 |
| Categories | `/categories` | `categoriesTable` (3) | `categoriesTablePerPage` | 0 / 0 / 0 |
| Analyst Categorization | `/analyst/categorization` | one table without id (0) | — | 0 / 0 / 0 |
| Reports | `/reports` | `runTable`, `runDataTable`, `fileTable` (0 each) | — | 0 / 0 / 0 |
| Report Catalog / Reports Dashboard | `/reports/dashboard` | `catalogTable` (12), `runsTable` (0), `schedulesTable` (0) | Show More, per-page ×3 | 0 / 0 / 0 |
| Schedules | `/schedules` | `schedulesTable` (0), `schedulesJobsTable` (0) | per-page ×2 | 0 / 0 / 0 |
| Detection | `/signals/detection` | `coverageTable` (3), `runTable` (0) | — | 0 / 0 / 0 |
| Horizon & Signal Explorer | `/signals` | `horizonTable` (0), `explorerTable` (0) | date-range buttons | 0 / 0 / 0 |
| Jobs | `/operations/jobs` | `jobsTable` (0) | — | 0 / 0 / 0 |
| Retention | `/retention` | `retentionTable` (9) | per-page `retentionTablePerPage` | 0 / 0 / 0 |
| User Management | `/users` | `usersTable` (1), one table without id (4) | — | 0 / 0 / 0 |
| Audit Log | `/admin/audit` | `auditTable` (28) | — | 0 / 0 / 0 |
| Translation Management | `/translations/manage` | one table without id (50) | Previous, Next | 0 / 0 / 0 (the API `/api/translations` returns **HTTP 500**; see §5) |

## 3. Behavior-tested coverage (the four list pages)

Scenario runner: `/tmp/browser-tools/verify_lists.cjs`, results at
`/tmp/browser_run/results/lists.json`. Run on commit `8a72e9e`: **71 passed, 0 failed.**

| Display | Initial load | Page size | Show More | Next/Prev | Filter | Sort (both) | Reload | Empty search | Out-of-range page | Errors |
|---|---|---|---|---|---|---|---|---|---|---|
| Categories | pass | pass | — (no Show More) | — | — | pass | pass | pass | pass | none |
| Keywords | pass | pass | pass (append, no duplicates, counter follows rows) | pass | pass (status=active) | pass | pass | pass (no range) | pass | aborted superseded search requests (9) — expected |
| Sides | pass | pass | pass | pass | — | pass | pass | pass | pass | none |
| Sources | pass | pass | pass | pass | — (ownership filter is in the Add/Edit modal, not the list) | pass | pass | pass | pass | none |

Still to behavior-test: **every other row in §2.** Words, Files, Reports
Dashboard, Schedules, Detection, Horizon, Jobs, Retention, Users, Audit Log,
Translation Management, and the search-results views need the same runner
extended to their table ids, plus seeded data where the table is empty today.

## 4. Known open findings (verified)

1. **Keywords Show More is a page navigation, not an append (design defect).** Show More requests page N+1 at the current page size and advances the shared `data-page` state, so Next/Previous move from the wrong page afterwards. Batch size equals page size, so the two cannot differ. Fix requires the shared Show More contract (see §6). Not fixed in this commit.
2. **Keywords fetches every matching record on each request.** `Api/routes/keywords.py` logs `Fetched 120 keyword rows` for a `per_page=10` page request. The page is sliced in Python after loading the full set. Verified from the application log.
3. **Translation API returns HTTP 500.** `GET /api/translations` → 500. Not yet traced.
4. **Page-size default is a product decision.** The saved `items_per_page` preference defaults to 50 in `settings/settings_models.py`; the Settings page falls back to 10; the list route renders 10 on the server. The page now applies the saved preference deterministically (50 here). Which default is intended is open.
5. **Search results and File Management tabs are not yet crawled.** They render their tables only after a search or a tab selection. The seed has 382 files, so search and tab results can be exercised; the scripted interactions do not exist yet. Status: `blocked` until they are scripted.

## 5. Coverage limits (stated, not hidden)

- Seed data (verified from the API and the crawl): 382 files, 120 keywords, 62 sources, 42 sides, 3 categories, 23 words, 9 retention items, 28 audit rows, 4 signals. Zero jobs, schedules, and report runs. Empty tables (jobs, schedules, report runs, Horizon explorer) prove only the empty state, not behavior with data.
- The four list pages have behavior coverage. The other rows in §2 have load coverage only.
- Browser: Chromium via `@sparticuz/chromium`; single-process mode (closing a context takes the browser down), so one context is used per run.

## 6. Show More contract (specification; implementation pending)

Terms:
- **Items per page** — the number of rows in one page of paged navigation. Set by the page-size select.
- **Show More batch** — the number of rows one Show More activation appends. Configurable; default equal to the saved page size **only until the batch size is made separate** (see open decision D-SM1).
- **Pagination** — explicit page navigation. Changes the visible rows to another page. It never appends.
- **Counter** — `visible range` and `total`, derived from the rows actually in the DOM and the server total. Never a stale label.

Required behavior (from the directive §3), with the current state:

| # | Requirement | Current state (verified) |
|---|---|---|
| 1 | Show More appends the next batch to the visible list | Keywords/Sides/Sources/Words: appends (verified on keywords, sides, sources) |
| 2 | No duplicated rows | verified (unique count 20/20 after one activation) |
| 3 | Batch size configurable and consistently interpreted | **Not met**: batch = page size |
| 4 | Final partial batch loads only what remains | not yet tested |
| 5 | Show More hidden when nothing remains | observed hidden on last page; not yet tested per display |
| 6 | Filter/search resets the set | verified on keywords (filter); search reset not yet tested per display |
| 7 | Sort reorders without loss/duplication | verified on the four list pages |
| 8 | Page size and paging do not conflict with Show More | **Not met**: Show More advances the pager's page, so Next then shows rows already visible |
| 9 | Empty, exact-boundary, final-partial, changed-dataset cases | empty verified; boundary and changed-dataset not yet tested |
| 10 | Existing controls and layout kept | yes (no control moved) |

**Root cause of requirement 8 (verified in code):** `static/js/modules/ui/unified-table.js` `updateLoadMoreBlock` and `nextPageUrl` advance `data-page`, the same attribute the numbered pager reads. Show More therefore changes the pager's current page.

Open decisions (need user confirmation before implementation):
- **D-SM1:** Should the Show More batch size be a separate control, or stay tied to the page size?
- **D-SM2:** Server-side Show More should use an offset (`offset`, `limit`) rather than a page number, so a batch can differ from a page. This needs an offset-capable fetch in each list route. The keywords route currently loads the full set (finding 2), so an offset fetch there also needs a SQL-level or cached sort.
