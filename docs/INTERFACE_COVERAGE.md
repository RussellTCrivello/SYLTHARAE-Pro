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

## 6. Show More contract (implemented for the shared table engine)

Terms (decided by the user):
- **Items per page** — the rows in one page of paged navigation (the page-size select). It also sets the Show More batch size.
- **Show More** — reveals the next batch of rows below the rows already shown. It never changes the pager's page.
- **Pagination** — moves to another page and replaces the rows. It resets the Show More window.
- **Counter** — `first–last of total`, from the rows in the window and the server total.

How it works (`static/js/modules/ui/unified-table.js`):
1. The window starts at the page's first row (`data-first-row`) and holds `data-shown` rows.
2. Show More requests the next block of `page size` rows after `first-1 + shown`. Because the window always grows in whole batches, that block is an aligned server page: `page = offset/size + 1`, `per_page = size`. The response is never larger than one page.
3. Only the rows past the ones already shown are appended (`adoptAppendedRows` skips `offset mod size`). No duplicates.
4. `data-page` (the pager) is never read or written by Show More. Its request does not carry the pager's page.
5. Show More is offered while rows remain after the window (`renderUnifiedPagination`), not only when there is a next page. The block's first row comes from the page, not from 1.
6. The `ut:loadmore` event carries `first`, `shown`, `total`; the keywords counter uses them.

Implementation note: the user chose "reveal from a loaded set". The implementation instead requests only the next aligned block, so already shown rows are not fetched again. The reveal happens in the browser either way, and the rows, counter and pager behave as the option describes. Tell me if the literal re-fetch of shown + batch rows is required.

| # | Requirement | Status after this change |
|---|---|---|
| 1 | Show More appends the next batch | met on list pages (`verify_lists.cjs` 71/71 incl. Show More appends; keyword browser checks 13/13) |
| 2 | No duplicated rows | met (unique-row checks on keywords, page 1 and page 2) |
| 3 | Batch size configurable and consistently interpreted | met as decided: batch = Items Per Page |
| 4 | Final partial batch reveals only what remains | met for keywords (page 2, size 50: 50 → 70 of 120, window 51–120) |
| 5 | Show More hidden when nothing remains | met in the engine smoke test (`unified_state_sync_smoke`); not yet checked in a browser per display |
| 6 | Filter/search resets the set | empty search verified (`verify_lists`); filter and search reset of the Show More window not yet verified |
| 7 | Sort reorders without loss | sort asc/desc verified (`verify_lists`); sort combined with an expanded Show More window not yet verified |
| 8 | Show More does not conflict with page size or paging | met for keywords: pager stays on its page (live check); Next/Prev after Show More not yet verified |
| 9 | Empty, boundary, final-partial, changed-dataset | empty and final-partial pass in the engine smoke test; changed-dataset clamp is engine-only; exact-boundary per display not verified |
| 10 | Controls and layout kept | yes |

Known gap: callers of `renderUnifiedPagination` that do not pass `pageSize` (about 10 call sites) keep the old offer rule and first-row formula. Keywords passes the page size. The others need the same one-line change, verified per display.

Open decision (unchanged): the server's default page size. See §4 item 4.
