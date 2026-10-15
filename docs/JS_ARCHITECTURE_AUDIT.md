# JavaScript architecture audit

Status of the audit as of the commit that introduces this file. Every number
below was produced by a script over the repository at that commit; none is
estimated. Scripts used are described under *Method* so they can be rerun.

## 1. Inventory

| Area | Files | Notes |
| --- | --- | --- |
| `static/js/modules/` | 91 | shared modules: core 32, ui 15, file-operations 11, views 5, search 5, rendering 5, messages 5, charts 5, navigation 4, upload 3, modals 2, map 2, documents 2, api 2 |
| `static/js/pages/` | 55 | one entry per page; loaded by `universal-initializer.js` (dynamic `import()`) or directly by a template |
| `static/js/settings/`, `i18n/`, `managers/`, top level | 35 | settings UI, locale catalogs, managers, wrappers |
| `static/vendor`, `static/dist` | 4 | third-party builds (Bootstrap, jQuery, Chart.js, jsPDF) and one dist bundle |
| `tests/js/` | 23 | Node harnesses (`.mjs`), driven by pytest wrappers |
| `tests/browser/` | 3 | browser lifecycle `.mjs` harnesses |
| `tools/` | 7 | verification and smoke scripts |

Total: 181 files under `static/js`, 76,668 lines. There is no `package.json`
and no bundler. Files are served as-is, so every import is a browser-resolved
ES module path.

## 2. Loading modes (what decides whether `import` is legal)

A page file can use `import` only when the browser loads it as a module.
Measured per page file:

| Mode | Files | Consequence |
| --- | --- | --- |
| dynamic `import()` from `universal-initializer.js` | most of `pages/` | module; imports allowed |
| `<script type="module">` in a template | `keywords-list`, `sides-list`, `sources-list`, `keyword-detail`, `side-detail`, `source-detail`, `users`, `word-detail`, `import-export`, … | module; imports allowed |
| **`<script src=…>` (classic) in `templates/Category/categories_list.html`** | `pages/categories-list-page.js` | **classic script; an `import` line is a SyntaxError.** Any change must switch the tag to `type="module"` and be verified in a browser. |

## 3. Dependency map

304 relative edges (static `import`, re-export and dynamic `import()`) among the
181 files.

**Import cycles (strongly connected components of size > 1):**

1. `modules/views/source-categories-keywords-view.js`, `modules/navigation/navigator.js`, `modules/ui/view-mode.js`, `modules/views/file-view.js`, `modules/views/item-view.js` (5 files)
2. `modules/file-operations/file-navigation.js`, `modules/file-operations/file-details.js` (2 files)

Cycles are recorded, not yet broken. Breaking them requires moving the shared
symbol into a third module; that is planned for a later stage with its own
tests because both cycles sit on the file-view navigation path.

**Most depended-on modules:** `core/utils.js` (35 importers), `core/config.js`
(20), `core/state.js` (15), `api/api-client.js` (15), `api/endpoints.js` (11),
`rendering/unified-pagination.js` (10). `core/utils.js` is the correct home for
stateless helpers and is already the canonical location for `escapeHtml`,
`escapeAttribute`, `formatFileSize`, `getCSRFToken`, `getCSRFTokenAsync`,
`buildUrl`, `debounce`.

## 4. Duplicate-function register

Method: every `function NAME(` declaration in `static/js` was extracted with its
brace-balanced body, whitespace-normalised, and hashed. Equal hashes mean
identical bodies after whitespace normalisation.

Names declared in two or more files: **166**. Most are not duplicates in
behaviour (for example `init`, `render`, `t`, `el`), and are not touched. The
register below covers only names whose bodies were compared.

### 4.1 `getCSRFToken`

12 definitions, 2 distinct bodies.

| Body | Count | Where | Decision |
| --- | --- | --- | --- |
| `modules/core/utils.js` (canonical) | 1 | — | canonical |
| identical copy | 11 | 10 `pages/*.js` files, including `categories-list-page.js` | consolidate to the canonical import, except `categories-list-page.js` (classic script, §2) |

### 4.2 `escapeHtml`

26 definitions, 14 distinct bodies. Variants differ in ways that change output:

| Variant | Count | Behaviour difference | Decision |
| --- | --- | --- | --- |
| canonical `modules/core/utils.js` | 1 | `null`/`undefined` → `''`; DOM-based; quotes not escaped (documented contract, see `escapeAttribute`) | canonical, unchanged |
| `textContent = text` without null guard | 10 | `undefined` renders as the text `undefined` | consolidate; a visible-text defect fix, covered by a regression test |
| `value || ''` | 2 (`map-viewer`, `path-analysis` family) | **numeric `0` becomes `''`** | **defect**, not migrated in this stage; needs a per-page decision because it changes dashboard numbers from blank to `0` |
| `if (!text) return ''` | 2 (`comprehensive-dashboard`, `path-analysis`) | **numeric `0` becomes `''`** | same defect, deferred |
| string-replace variants (with and without `'` escaping) | 5 | do not use the DOM; output escapes `"` in some and not others | deferred; attribute contexts must use `escapeAttribute` |
| `results-export.js` copy | 1 | file is dead (§6) | removed with the file |

### 4.3 `formatFileSize`

8 definitions, 4 distinct bodies. **Conflicting user-visible output, not a
duplicate:**

| Body | Used by | `0` renders as | unit label |
| --- | --- | --- | --- |
| canonical `core/utils.js` | canonical | `0 Bytes` | `Bytes`, `KB`, `MB`, `GB`, `TB` |
| `e3ee1034` | `search/results-export` (dead), `charts-dashboard`, `comprehensive-dashboard`, `search-advanced` | `0 B` (`!bytes` guard) | `B`, `KB`, … |
| `64dc9f08` | `dashboard`, `path-analysis` | `0 B` | `B`, … |
| `d0867872` | `email-words` | `0 B`; also clamps to PB and rejects non-numbers | `B`, … |

Consolidating these changes visible text (`Bytes` vs `B`). That is a product
decision and is **not** made in this audit. Open decision D1 (§9).

### 4.4 Other names compared

`showError` (14 definitions), `showToast` (7), `notify` (6), `loadCategories` (6),
`renderRows` (5), `applyFilters` (5), `resetFilters` (4), `renderKeywords` (4),
`renderCategories` (4), `loadKeywords` (4). Not yet compared body-by-body. These
are the next items in the register and belong to the pagination/filter stage.

## 5. Four list pages (Categories, Keywords, Sides, Sources)

| Page | Lines | Imports | Pagination | Fetch sites |
| --- | --- | --- | --- | --- |
| `categories-list-page.js` | 827 | none (classic script) | local | 9 |
| `keywords-list-page.js` | 2,234 | none | local; 12 textual mentions of "unified" but no import of `unified-pagination.js` | 18 |
| `sides-list-page.js` | 627 | none (module) | local, no unified pagination | 5 |
| `sources-list-page.js` | 787 | none (module) | local, no unified pagination | 7 |

The four pages each carry their own copies of `escapeHtml`, `getCSRFToken`,
data-loading and per-page logic. Consolidating the pagination/filter/fetch path
is the largest remaining duplication and is the next stage. It is not done in
this audit; the browser verification of these four pages is the gate for it.

## 6. Dead code (removed in this stage)

Method: each file's basename and stem was searched across every `.js`, `.mjs`,
`.html`, `.py`, `.md`, `.json`, `.toml`, `.yml`, `.ps1`, `.bat`, `.sh` and
template in the repository (excluding `.git`). Zero references for all three:

| File | Exports | Git history |
| --- | --- | --- |
| `static/js/modules/core/loading-manager.js` | — | initial commit only |
| `static/js/modules/core/settings-error-handler.js` | — | initial commit only |
| `static/js/modules/search/results-export.js` | `exportSearchResults`, `printSearchResults` | initial commit only |

## 7. Defects and root causes found so far

| ID | Defect | Root cause | Status |
| --- | --- | --- | --- |
| DEF-1 | `escapeHtml` renders `undefined` as the word `undefined` in 10 page/module copies | copy-pasted variant without the null guard | fixed by consolidation (regression test) |
| DEF-2 | `escapeHtml` renders numeric `0` as empty in 4 variants | `\|\|` / truthiness guard on a value that may be `0` | **open**, §4.2 |
| DEF-3 | `formatFileSize` shows `0 Bytes` on one screen and `0 B` on others | independent implementations | **open, decision D1** |
| DEF-4 | three dead modules | files left behind after refactors | removed |
| DEF-5 | import cycles across the file-view navigation path | shared symbols kept in the module that consumes them | **open**, §3 |
| DEF-6 | `categories-list-page.js` cannot take imports | classic `<script>` tag in its template | **open**, requires tag change and browser test |

## 8. Method and reproduction

* Function bodies: Python, regex `^\s*(export\s+)?(async\s+)?function\s+NAME\s*\(`,
  brace-balanced extraction, whitespace-normalised MD5.
* Import graph: regex for `import … from`, `export … from` and `import(` with
  relative specifiers, resolved against the file path; cycles via Tarjan SCC.
* Loading mode: regex over `templates/**/*.html` for `<script … src=…>` with and
  without `type="module"`, plus `import('./name')` in JS.
* Dead code: basename and stem search over the repository text.
* JavaScript harness baseline: the 20 Python test files that drive `.mjs`
  harnesses (`grep -l '\.mjs'` over `tests/unit`, `tests/integration`,
  `tests/browser`, `tests/e2e`). Result before any change: **296 passed,
  1 skipped, 0 failed**.

## 9. Open decisions and risks

* **D1 (product):** one `formatFileSize` label convention. `Bytes` (canonical) or
  `B` (three pages). Needs a choice before consolidation.
* **D2 (product):** whether dashboards should show `0` where they currently
  show blank (`escapeHtml` `||` variants). The correct value is `0`, but the
  numbers on those screens change from blank to visible.
* **Risk:** `categories-list-page.js` switching to `type="module"` changes
  execution to deferred and strict mode. Verify in a browser before shipping.
* **Risk:** the 2 import cycles. Not changed here; changing them touches the
  file-view navigation path that the browser verification must cover.
