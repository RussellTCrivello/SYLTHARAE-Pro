# Multilingual category / term / keyword labels — implementation plan

Status: **decisions taken, first slice implemented.** The questions in §11 are
answered (2026-10-27): the schema freeze is extended by one additive
`m0005_term_names.py` (D1), search expansion covers the taxonomy only (D3), and
curation starts as a CSV import and gains in-UI editing after it (D5).

Implemented so far — the half that needs no database:

| slice | state | evidence |
| --- | --- | --- |
| T0 surface inventory | **done** | `tools/audit/scan_term_label_surface.py`, `audit_report/r20/term_label_surface.csv` |
| T2a normalisation (`term_key`, `key_variants`, `script_ok`) | **done** | `core/i18n/term_key.py`, `tests/unit/test_term_key.py` — 26 passed |

Everything else in this document is still a plan, and the integration slices (T1,
T3–T7) need a rebuilt environment: the sandbox was re-cloned mid-session and the
virtualenv and PostgreSQL instance lived in `/tmp`.

Every number below carries the command that produced it. Anything I could not
measure is labelled **inferred** or **unverified**.

---

## 1. What is being asked for, as testable requirements

| # | Requirement | Where it is verified |
|---|---|---|
| R1 | A category keeps its canonical name and gains names in ar / he / fa / hr (extensible) | `test_term_names_schema.py` |
| R2 | The interface shows the label in the user's current language, and never a blank one | `test_term_names_display.py` |
| R3 | Terms assigned to a category (`words_categorys`) and keywords are labelled the same way | `test_term_names_display.py` |
| R4 | A search in any language finds the entity: Arabic query → English-named category, and the reverse | `test_term_names_search.py` (**the core acceptance test**) |
| R5 | Analysts and administrators can curate names without SQL; no machine translation | `test_term_names_curation.py`, `test_translation_memory_rules.py` (existing) |

"Without a significant expansion of the architecture" is taken literally: one new
table, one resolver module, and changes at two boundaries (display, search). No
new service, no new datastore, no per-endpoint translation logic.

---

## 2. What already exists (measured, not proposed)

| Fact | Evidence |
|---|---|
| A category's name *is* a `words` row: `categorys.word_id INTEGER UNIQUE NOT NULL → words(id)`, `words.word TEXT UNIQUE NOT NULL` | `database/migrations/m0001_baseline.py` |
| Term membership is `words_categorys(word_id, category_id)`; a keyword is a packed list of word ids in `keywords.keyword BYTEA` | same file |
| There is already a multilingual name table for places: `geo_place_names(place_id, name, match_key, language, script, name_type)` with `idx_geo_place_names_key` | same file, `m0001` §gazetteer |
| Normalisation for Arabic/Persian/Hebrew already exists and is tested: NFKC, harakat/tatweel/ZWNJ removal, alef/yeh/keheh folding, Hebrew geresh | `core/geo/names.py` |
| Interface language is already resolved per request (cookie → session → system setting → `Accept-Language` → default) and exposed as `resolve_interface_language(app)` | `Api/routes/common.py:120` |
| A UI-string override store already exists (`translation_overrides(locale, message_key, msgid, translation)`) with admin CRUD, caching and cache invalidation | `Api/migrations` m0001 §translation overrides, `Api/services/translation_management.py` |
| Label reads are spread wide: **158** SQL literals selecting `w.word`, in **29** modules that also declare **148** routes; **12** templates and **17** page scripts render a label | `python3 tools/audit/scan_term_label_surface.py --csv audit_report/r20/term_label_surface.csv` |
| Highest-density files: `Api/utils/utils.py` 29, `Api/blueprints/analytics.py` 16, `Api/routes/file_analysis.py` 12, `Api/services/lexis_queries.py` 10, `Api/routes/api.py` 10, `services/categories/tree.py` 9 | same CSV |

Two consequences shape the design:

1. **Translations must not become `words` rows.** `words.word` is globally
   UNIQUE and `categorys.word_id` is UNIQUE, so inserting `سياسي` into `words`
   would create a *second* category with an Arabic name, not a translation of
   `political` — and it would break the "unique name per sibling" rule the tree
   service enforces.
2. **158 SQL sites cannot be edited one by one.** The resolver has to sit at
   the boundary where rows become HTML/JSON (bounded: the templates and a
   measured list of label endpoints), and search has to be expanded at the few
   *entry points* where a human types a query (six, listed in §6.2).

---

## 3. Design in one paragraph

One new table, `term_names`, keyed on `words.id` — because category names,
category terms and keyword words are all `words` rows, so one table covers R1
and R3. Reading is a batched lookup (`word_id = ANY(...)`) with fallback
`requested language → en → canonical`, applied at the presentation boundary. A
Jinja filter `| term` covers server-rendered tables; the JSON helpers cover the
API; `GET /api/i18n/term-labels` covers page scripts that only hold ids.
Searching is *query expansion*: normalise the typed query with the existing
`core.geo.names` rules, resolve it against `term_names.match_key` to a set of
word ids, and add `OR w.id = ANY(%s)` to the existing `ILIKE` predicates — so an
Arabic query and an English query hit the same rows, and results are then
displayed in the reader's language.

```
          query text (any language)
                    │  term_key()  (match_key + casefold)
                    ▼
        term_names.match_key  ──►  word_id set W
                    │
   existing ILIKE on w.word  OR  w.id = ANY(W)   ← one extra OR, index-backed
                    ▼
             result rows (canonical w.word)
                    │  resolve_labels(rows, lang)
                    ▼
        HTML (| term filter) / JSON (label helper) / client (id → label API)
```

---

## 4. Storage

### 4.1 Chosen: `m0005_term_names.py` (freeze exception approved, D1)

Additive only; nothing in `m0001`–`m0004` is edited. Mirrors `geo_place_names`
so the vocabulary, the script rule and the match-key discipline are already
familiar to anyone who has read the gazetteer.

```sql
CREATE TABLE term_names (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    word_id    INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE ON UPDATE CASCADE,
    name       VARCHAR(255) NOT NULL CHECK (length(btrim(name)) > 0),
    match_key  VARCHAR(255) NOT NULL CHECK (length(match_key) > 0),
    language   VARCHAR(8)   NOT NULL CHECK (language IN ('en','ar','he','fa','hr')),
    name_type  VARCHAR(16)  NOT NULL CHECK (name_type IN ('preferred','alternate','transliteration')),
    script     CHAR(4)      NOT NULL CHECK (
                   -- a transliteration is Latin by definition
                   (name_type = 'transliteration' AND script = 'Latn')
                OR (name_type <> 'transliteration' AND (
                       (language IN ('en','hr') AND script = 'Latn')
                    OR (language IN ('ar','fa') AND script = 'Arab')
                    OR (language =  'he'      AND script = 'Hebr')
                   ))),
    source     VARCHAR(40)  NOT NULL DEFAULT 'curated'
                            CHECK (source IN ('curated','imported','admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (word_id, language, match_key, name_type)
);

CREATE INDEX idx_term_names_key ON term_names (match_key);
CREATE INDEX idx_term_names_word_language ON term_names (word_id, language);
-- exactly one preferred name per (word, language)
CREATE UNIQUE INDEX uq_term_names_preferred
    ON term_names (word_id, language) WHERE name_type = 'preferred';
```

`match_key` is always computed server-side (`term_key()`, §5.1), never accepted
from a client — a wrong key silently defeats search.

**Not yet executed.** This environment has no PostgreSQL running, so the DDL
above is reviewed by hand, not applied; the first task in T1 is to run it as a
migration with its own upgrade → insert → downgrade → upgrade test, which is
also what validates the `script` CHECK and the partial unique index. Downgrade drops the table
and its three indexes; `test_term_names_schema.py` mirrors
`tests/integration/test_m0004_downgrade_upgrade.py`.

Volumetrics (**inferred** from the existing tables, not measured on production
data): `words` rows ≈ number of distinct terms; at 100 000 terms × 3 languages
the table is ≈ 300 000 rows, ≈ 40 MB with indexes — the same order as
`words_hashs`, which the schema already paginates.

### 4.2 Fallback: no schema change (D1 refused)

Reuse the existing `translation_overrides` table with a reserved key namespace:
`locale = 'ar'`, `msgid = 'term:<word_id>'`, `translation = 'سياسي'`,
`message_key = sha256(msgid)`. Zero migrations, reuses the existing admin UI,
caching and audit trail.

What it costs:
* no FK — a deleted word leaves an orphan string (must be swept, or read-time
  filtered by joining `words`);
* no `match_key` column and no index on `msgid` — every search expansion becomes
  a full scan of the override table and a Python normalisation pass. Fine at
  10 000 keys (**inferred**: sub-millisecond), not at 10⁶;
* no script CHECK, no one-preferred-per-language constraint;
* it mixes data labels with UI strings in one table, which makes the Settings
  translation manager show `term:1234` rows unless it filters the prefix.

§4.1 is the chosen route (D1, approved 2026-10-27); §4.2 is kept here because it
is the fallback if the freeze is reinstated, and because it states exactly what
the schema buys.

---

## 5. Resolution layer (new code, no SQL surface changes)

### 5.1 `core/i18n/term_key.py` (new, ~60 lines)

Thin, single-source normalisation. **Imports** `match_key`, `script_of`,
`normalize_with_index`, `LANGUAGE_SCRIPT` from `core/geo/names.py` — no second
copy of the folding table, so a future Arabic fix reaches places and terms at
once.

```python
def term_key(text: str) -> str:
    """Match key for a term name or a query: place-name rules + casefold."""

_ARABIC_ARTICLE = "ال"

def key_variants(text: str) -> list[str]:
    """Keys to try for a query: the key itself, minus a leading Arabic
    definite article, and with one added. `السياسي` and `سياسي` must meet;
    the gazetteer never needed this because place names rarely carry it."""
```

Unit tests pin the behaviour that matters: harakat and tatweel are dropped,
ZWNJ (Persian half-space) folds to nothing, `ي`/`ی`/`ى` meet, Hebrew niqqud is
dropped, Latin is case-insensitive for terms (unlike place names, where case is
significant — this is the one deliberate difference and it is tested).

### 5.2 `services/i18n/term_labels.py` (new, ~180 lines)

```python
PREFERRED, ALTERNATE, TRANSLITERATION = "preferred", "alternate", "transliteration"
LANGUAGE_FALLBACKS = {"ar": ("ar", "en"), "he": ("he", "en"), "fa": ("fa", "en"),
                      "hr": ("hr", "en"), "en": ("en",)}

def labels_for(cur, word_ids, lang) -> dict[int, str]:
    """One query, no N+1: preferred name in each fallback language, then
    alternate/transliteration, then None (caller keeps the canonical word)."""

def label_map(run, word_ids, lang) -> dict[int, str]:
    """Same, through Api.utils.execute_query, for route code."""

def word_ids_for_query(cur, query, *, languages=None) -> set[int]:
    """Query expansion: key_variants(query) → term_names.match_key → word ids.
    `languages=None` means every language, which is what makes R4 work in both
    directions."""

def invalidate(lang=None) -> None:
    """Drop the process-local label cache; called by every curation write."""
```

Cache: `dict[(lang, word_id)] -> str` per process, TTL like
`translation_management._CACHE_TTL_SECONDS`, invalidated by the write paths. A
label map is stable data, so a stale entry can only be a curation edit seconds
old.

---

## 6. Display (R2, R3)

### 6.1 Rules

1. Requested language → `en` → canonical `words.word`. Never empty, never a
   placeholder.
2. The requested language is `resolve_interface_language(app)` by default, so an
   Arabic interface shows Arabic labels with no extra parameter. Explicit
   override: `?lang=` on any GET, and `X-Term-Language` for `POST`.
3. Every rendered label sits in a `dir="auto"` element (or `<bdi>`), because a
   page can be LTR while a single name is Arabic or Hebrew.
4. Exports (JSON/CSV) honour the same `?lang=`, and carry the canonical name in a
   separate field so a downstream consumer never loses the join key.

### 6.2 Where the change lands (bounded, measured)

| Boundary | Change | Files |
|---|---|---|
| Jinja | register a `term` filter + `t_term()` in the app factory; wrap label cells | 12 templates from the scan (`templates/Category/*`, `templates/Keywords/*`, analytics tables) |
| JSON endpoints | pass `name`/`category_name`/`word` through `label_map` in the dict builders | the modules the scan ranks highest: `Api/routes/api.py` (`/api/categories/search`, `/api/words/search`, category list), `Api/routes/category_tree.py`, `Api/routes/keywords.py`, `Api/routes/categories.py`, `Api/routes/file_analysis.py`, `Api/routes/archives*.py`, `Api/blueprints/analytics.py` |
| Page scripts | `window.SYL.termLabel(id, fallback)` backed by `GET /api/i18n/term-labels?ids=…&lang=…` (batched, cached, 200 ids per call) | 17 scripts; only those that render a label from an id need the call |
| Tree SQL | `_ROW_SQL` keeps `w.word` (canonical) and the route localises `name`/`path` on the way out — the recursive CTE stays untouched | `services/categories/tree.py`, `Api/routes/category_tree.py` |

The `/api/i18n/term-labels` endpoint is what keeps this from touching every
page script: it is one call, cached, and the label of an id is the only thing a
script actually needs.

### 6.3 Keyword phrases

A keyword is a sequence of word ids, so a translated keyword is its words
translated and rejoined (`"political stability"` → `"الاستقرار السياسي"` word by
word). Word order is wrong for real Arabic/Persian phrasing. Two mitigations,
both in the plan:

* `name_type = 'alternate'` on a single word allows a curated phrase token
  (`الاستقرار السياسي` attached to the keyword's *first* word) — cheap, no new
  table, and the display code prefers an alternate whose key matches the whole
  phrase;
* **backlog**: a `keyword_names(keyword_id, language, name)` table if analysts
  ask for proper phrase translation (needs the same freeze decision again).

This limitation is stated in the UI: the keywords table header shows
"translated word by word" as a tooltip only when the label was assembled from
more than one translation.

---

## 7. Search (R4 — the core requirement)

### 7.1 Algorithm

```
q_keys   = key_variants(query)                      # normalise, article-tolerant
W        = term_names.word_id WHERE match_key = ANY(q_keys)     # all languages
results  = SELECT … WHERE (<existing ILIKE predicate>) OR w.id = ANY(W)
```

Properties that matter, each with a test:

* Works in both directions: an Arabic query finds the English-named category, and
  an English query still finds it when the interface is Arabic (the language
  filter is a display concern, not a search concern).
* No recall change for a miss: `W` empty → the predicate is exactly today's.
* One extra parameter, one indexed lookup (`idx_term_names_key`, verified with
  `EXPLAIN`), independent of table size for the `ILIKE` planner path.
* Ranking unchanged: expansion adds rows to the candidate set, and the existing
  `ORDER BY` decides. Where relevance is computed in SQL
  (`core/search/sql_relevance.py`) a matched-by-translation row gets the same
  weight as a matched-by-text row; the plan notes this is a **product decision**
  (a translation hit could be ranked lower) and defaults to equal weight.

### 7.2 The six entry points that have to change

| # | Entry point | Current predicate | Change |
|---|---|---|---|
| 1 | `/categories` page search (`Api/utils/utils.py::get_categories_paged`) | `where_sql = "WHERE w.word ILIKE %s"` | `… OR w.id = ANY(%s)` |
| 2 | `/api/categories/search` (`database/database/queries/category_queries.py::search_categories`) | `WHERE %s IS NULL OR w.word ILIKE %s` | add the same `OR`; the repo passes `word_ids` through |
| 3 | Category tree search (`services/categories/tree.py::_search_rows`, and the `matched` CTE in `fetch_tree`) | `WHERE w.word ILIKE %s` | `… OR c.word_id = ANY(%s)` |
| 4 | `/api/words/search` (term picker, `Api/routes/api.py`) | `WHERE w.word ILIKE %s` | same, plus exact-match branch for a translated name |
| 5 | `/api/keywords` and the keywords page (`core/keyword_search.py::_scan`) | Python `needle` on decoded text | add `needle_ids`: a keyword matches if any of its word ids ∈ `W`, OR the text contains the needle (existing behaviour preserved) |
| 6 | Archives / file-analysis facets (`Api/routes/archives_api.py`, `Api/routes/file_analysis.py`, `Api/routes/archives.py`) | `filters['w.word'] = {'ILIKE': …}` | facet-resolution step that turns the query into `W` and unions the filter |

### 7.3 Out of scope for R4 (and why)

Full-document search (`/api/search`, `core/search/boolean_or_flat.py`) matches
document content, which is stored as word ids. Expanding a query there would make
an Arabic query return documents that only contain the English word. That is a
real feature (R4 can be read that way) but it changes recall on the main search
page, so it is a separate, opt-in step with a toggle — decision D4, default off,
measured separately.

---

## 8. Curation (R5)

* **API** (`Api/routes/term_names.py`, new): `GET /api/term-names?word_id=|category_id=|q=`,
  `POST`, `PUT /api/term-names/<id>`, `DELETE`, `POST /api/term-names/import`
  (CSV). Writes are admin-only, reads analyst+. Validation: language in the
  supported set, script matches language (or `transliteration`), no duplicate
  preferred, `match_key` computed server-side, 255 chars, no control characters.
* **Audit**: every write lands in `audit_log` with before/after, like the
  existing translation-override writes.
* **UI**: a "Names" tab in the category edit dialog (one row per language, RTL
  input for ar/he/fa), a "Terms" page listing coverage per language
  (translated / missing / stale), and a CSV export for offline curation.
* **Seed**: `data/glossary/terms_seed.json` in the gazetteer seed shape, loaded
  by an idempotent upsert keyed on `(word_id, language, match_key, name_type)`,
  with the same fingerprint/integrity checks as `services/geo/gazetteer.py`.
  Curated by a human; **no machine translation** — the standing rule and
  `tests/integration/test_translation_memory_rules.py` both forbid it.
* **New UI strings for this feature** (tab titles, column headers) must reuse
  existing catalog vocabulary or the i18n coverage test fails — the constraint
  that bit the LEXIS page. Any genuinely new string needs catalog rows in
  ar/he/fa/hr, which is a separate, authorised task (D5).

---

## 9. Tests first (each is written failing before the code)

| File (new) | First failing assertion |
|---|---|
| `tests/integration/test_term_names_schema.py` | the table and its three indexes exist; a second `preferred` for one `(word, language)` is refused; deleting a word cascades; a Latin name in `ar` without `transliteration` is refused; downgrade/upgrade round-trips |
| `tests/unit/test_term_key.py` | `term_key('السِّياسي')` == `term_key('سياسي')` == `term_key('سیاسی')`; Hebrew niqqud dropped; ZWNJ dropped; Latin casefolded |
| `tests/integration/test_term_names_display.py` | `/categories?lang=ar` renders `سياسي`; `?lang=en` renders `political`; a language with no row falls back to `political` and never to `""`; the cell carries `dir="auto"`; `/api/categories/search` returns `name` in the requested language and `canonical_name` unchanged |
| `tests/integration/test_term_names_search.py` | **the acceptance test**: with only `political`/`سياسي` seeded, `GET /categories?search=سياسي` finds it; `/api/categories/search?q=سياسي` finds it; `/api/words/search?q=سياسي` returns the word; `/api/keywords?q=سياسي` returns keywords containing it; `/api/categories/tree?search=سياسي` marks the node `is_match`; an English query in an Arabic session finds it; a harakat/tatweel spelling finds it; an unknown query returns exactly what it returns today |
| `tests/integration/test_term_names_curation.py` | non-admin POST → 403; analyst PUT → 403; admin POST → 201 + `audit_log` row; duplicate preferred → 409; wrong script → 400; the label cache reflects the write on the next request |
| `tests/integration/test_term_names_scale.py` | 100 000 words × 3 languages: one page of 200 labels issues **one** query (assert the cursor call count); `EXPLAIN` for the expanded search uses `idx_term_names_key`; p95 page latency recorded |
| `tests/unit/test_term_label_surface.py` | runs `tools/audit/scan_term_label_surface.py` and fails if a label site is not localised and not in a declared allowlist — this is the guard that stops the 158 sites growing back to English-only |

The surface scan already exists (`tools/audit/scan_term_label_surface.py`,
committed with this plan) so the allowlist starts from a generated inventory
rather than from memory.

---

## 10. Workstreams, commits, effort

| # | Workstream | Deliverable | Effort (**inferred**) | Blocked by |
|---|---|---|---|---|
| T0 | Surface inventory | scan script + CSV — **done** | 0.5 d | — |
| T1 | Migration + schema tests | `m0005_term_names.py`, `test_term_names_schema.py` | 0.5 d | environment: no PostgreSQL in this session |
| T2 | Normalisation + resolver | `core/i18n/term_key.py` **done** (26 passed); `services/i18n/term_labels.py` pending | 1 d (0.4 d done) | resolver needs a database |
| T3 | Display | Jinja filter, label helper, `/api/i18n/term-labels`, templates, scripts | 1.5 d | T2 |
| T4 | Search expansion | six entry points + acceptance test | 1.5 d | T2 |
| T5 | Curation | API, UI tab, CSV import/export, seed sync | 2 d | T1, T3 |
| T6 | Scale + EXPLAIN | 100 k fixture, query-count assertions | 1 d | T3, T4 |
| T7 | Generated artefacts | `docs/endpoint_inventory.json`, `docs/reference/HTTP_ROUTES.md`, `docs/reference/DATABASE_SCHEMA.md`, interface registry | 0.5 d | T1, T5 |

≈ 8 developer-days, one commit per workstream, tests committed with their
workstream. T7 is not optional: the endpoint and schema docs are generated and
the existing contract tests fail when they drift (`test_interface_coverage`,
`test_reference_docs`).

---

## 11. Decisions

| # | Decision | Answer (2026-10-27) | Consequence |
| --- | --- | --- | --- |
| **D1** | Extend the schema freeze to one additive `m0005_term_names.py`, and regenerate the generated docs it affects | **approved** | T1 proceeds as §4.1; `m0001`–`m0004` untouched; T7 regeneration is part of the change, not opportunistic drift-fixing |
| D2 | Keyword phrases: phrase-level translations or word-by-word? | **word-by-word now** | §6.3; a `keyword_names` table stays in the backlog |
| D3 | Should a translated query also expand full-document search? | **no — taxonomy only** | §7.3 stays out of scope; the six entry points in §7.2 are the whole surface |
| D4 | Ranking of a translation-only hit | **equal weight** (unchanged) | no relevance contract change |
| D5 | Who produces the first names, and through what? | **CSV import first, then in-UI curation** | T5 ships importer + validator + coverage report first; the "Names" tab follows in the same workstream |
| D6 | New UI strings this feature needs | **reuse existing catalog vocabulary** | authoring new catalog rows is not permitted by the standing rules and is not part of this work |

## 12. Verification gate for this feature (same discipline as the audit rounds)

1. Full unit + integration suites on a fresh database, twice (sequentially — two
   concurrent runs OOM the 3.9 GB box), diffed by test id against the parent
   commit; every non-passing id classified.
2. `git diff HEAD -- database/migrations` shows exactly `m0005_term_names.py`.
3. `EXPLAIN` recorded for each of the six search entry points, with and without
   a translation hit; the 100 k scale test in the same run.
4. Probe counts re-run (`tools/audit/probe_param_routes.py`) so the new endpoints
   are covered by the malformed / query-string / parameterised sweeps.
5. Browser E2E: interface in Arabic → category list shows Arabic names →
   search typed in Arabic → the English-named category appears; switch to
   English → the same rows show English names.
6. Raw XML, logs, `EXPLAIN` output and screenshots committed under the round's
   output directory before the numbers are quoted in `REPORT.md`.

## 13. Claim status

* **Measured**: schema shape and constraints (§2), the `words`/`categorys`
  uniqueness trap, normalisation location, language resolution, override store,
  and the 158 / 29 / 148 / 12 / 17 surface counts — the last from
  `python3 tools/audit/scan_term_label_surface.py` at commit `3703c90`.
* **Inferred**: table sizes, latencies, effort estimates, and that the six
  entry points are exhaustive (the scan is regex-based: a label built by
  string concatenation across lines, or in a query loaded from a file, would be
  missed).
* **Unverified**: anything about production data volume; the current environment
  has no dataset beyond the test fixtures.
