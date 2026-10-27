# Data entry: the category workbook

`classification/domain_data.xlsx` is the authoritative record of taxonomy
content. The database follows the workbook; the workbook never follows the
database. This page is the operator's contract for editing it.

## The rules

Four rules, all enforced by one module —
`apps/importing/validators/workbook_rules.py` — so the importer, the sync tool
and the test suite cannot disagree about them.

| # | Rule | Refused with |
|---|------|--------------|
| 1 | **The worksheet name is the category name.** | `SHEET_EMPTY`, `SHEET_NAME` |
| 2 | **A worksheet's rows are its content:** column `Term` and column `Keyword`. | `MISSING_HEADER`, `NON_TEXT_CELL`, `HEADER_IN_DATA` |
| 3 | **A term is exactly one word.** | `TERM_HAS_WHITESPACE`, `TERM_TOO_LONG` |
| 4 | **A keyword is two or more words** (a phrase or expression). | `KEYWORD_SINGLE_WORD` |

Plus three that keep a sheet readable: no repeated entry in a sheet
(`DUPLICATE_TERM`), no text that is both a term and a keyword in the same sheet
(`TERM_ALSO_KEYWORD`), and no phrase claimed by two sheets without saying which
sheet owns it (`KEYWORD_SHARED` → see `_Keyword Owners`).

### Layout

```
Networks            <- worksheet name = category name
  A1: Term    B1: Keyword    <- headers, spelled exactly like this
  A2: Router  B2: Load balancing
  A3: Switch  B3: Port mirroring
```

* `_README` — what the file is for.
* `_Keyword Owners` — only needed for a phrase listed in more than one sheet.
  The database stores a keyword **once**, so ownership has to be a decision.
  Put the phrase in column A and the owning worksheet's name in column B.
* `Master Index` — derived. It is regenerated, never edited, and never read as
  data.

Any sheet whose name starts with `_` is treated as a helper sheet. Other
worksheets are categories, in the order they appear in the file.

## The two ways content reaches the database

### 1. Sync (the normal path)

```bash
python3 tools/i18n/sync_taxonomy.py                 # what would change
python3 tools/i18n/sync_taxonomy.py --apply         # do it, in one transaction
python3 tools/i18n/sync_taxonomy.py --check         # rules only, no database
```

`--dry-run` is the default: the tool prints the plan and writes nothing. `--apply`
writes exactly that plan in a single transaction.

What an edit does:

| Edit in the workbook | Effect on the database |
|----------------------|------------------------|
| add a worksheet | the category is created |
| rename a worksheet | the category is renamed (`--rename "Old=New"`) |
| add a `Term` | the word is created or reused, then linked to the category |
| delete a `Term` | the link is removed; the word row stays (it may be shared) |
| add a `Keyword` | the phrase is stored under its owning category |
| delete a `Keyword` | the phrase row is deleted |
| delete a worksheet | reported only — see `--prune-categories` |

Deliberately explicit, because each can destroy data:

* `--rename OLD=NEW` — a rename is told to the tool, not inferred. Without it a
  renamed sheet looks like a new category plus a missing one. Repeat the flag
  for several renames.
* `--prune-categories` — delete categories whose worksheet is gone.
* `--prune-words` — delete words no row references any more. Words that appear
  only inside a keyword phrase are **not** orphans; deleting one would corrupt
  another category's phrase.

Exit codes: `0` success, `1` the workbook breaks a rule, `2` the database
refused the write.

The tool is idempotent: running it twice in a row performs no second write, and
re-syncing an unchanged file reports every count as zero.

### 2. The importer (legacy route)

`apps/importing` reads the same workbook through the same rules, so a file the
sync tool accepts is a file the importer accepts, and a file that breaks a rule
is refused with the sheet and cell named:

```
domain_data.xlsx breaks the category data rules: Networks!A3: [TERM_HAS_WHITESPACE] ...
```

The importer is not the reconciliation path: it inserts, it does not delete, and
it cannot rename a category. Use the sync tool when the workbook is the source
of truth, which it is.

## Before committing an edit

```bash
python3 tools/i18n/sync_taxonomy.py --check     # rules, and the shared-phrase decisions
python3 -m pytest tests/unit/test_committed_workbook.py -q
```

`test_committed_workbook.py` re-reads the real file on every run: it applies the
rules, asserts the reviewed counts, checks that `Master Index` agrees with the
category sheets, and refuses a stray third column. A count that changes is the
review — the test failing is the tool telling you what your edit did.

## What the rules do not cover

* **Arabic names.** A term's Arabic name is not in this workbook; it lives in
  `term_names` and is not machine-translated. See
  [REGISTRY_EVIDENCE.md](REGISTRY_EVIDENCE.md).
* **Case variants across sheets.** `Server` and `server` in two different sheets
  are two words in `words`. The import lower-cases; the sync tool keeps the
  workbook's spelling, which is what the interface displays. Keep the spelling
  consistent within a file.
* **Phrase ownership beyond one category.** The schema stores a keyword once, so
  a phrase in two sheets belongs to one of them. `_Keyword Owners` records which;
  the other sheet's claim is reported, not stored.
