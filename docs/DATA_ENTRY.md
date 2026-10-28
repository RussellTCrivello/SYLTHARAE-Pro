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

### 2. When it happens without you

The workbook is authoritative, which is only true if something notices when the
database has fallen behind. Three mechanisms, in the order most operators meet
them:

**On startup.** The service compares the workbook with the database and acts
according to `SYLTHARAE_TAXONOMY_SYNC`:

| value | behaviour |
|---|---|
| `apply` (default for `run_web.py`) | write the difference at startup |
| `check` | say in the log how many changes are pending, write nothing |
| `0` / `off` | neither |

The fingerprint of the last applied run is kept in `APP_DATA_DIR`, so a restart
with an unchanged file costs one digest and no database work. An edit made while
the service was down is therefore applied the next time it starts, and nothing
else is touched. The fingerprint covers three things - the workbook's bytes, the
rules that interpret it, and `SYNC_LOGIC_VERSION` in
`services/importing/taxonomy_sync.py` - because a changed rule makes the same
file mean something different, and a fingerprint over the bytes alone would let
the fast path skip work that the new rules would have written.

Measured on this workstation: the unchanged path costs 0.42 ms (one digest,
0.21 ms of it) and the slow path 56.5 ms for a 30-category workbook; the test
that measures it is `test_the_fast_path_costs_a_hash_and_the_slow_path_costs_the_plan`.

### Why the entry point still applies

`run_web.py` sets `SYLTHARAE_TAXONOMY_SYNC=apply`. Every other entry point - the
API, the CLI, a test - defaults to `check`. The reason is the rule at the top of
this page: an edit to the workbook must reach the database without anybody
remembering a command, and a served deployment is the only place where nobody is
watching. It stays safe because three guards stand in front of the write:

| guard | what it does |
|---|---|
| rule validation | a workbook that breaks a rule is refused, nothing written |
| shrink limit (`SYLTHARAE_TAXONOMY_SHRINK_MAX`, default `0.25`) | a sync that would remove more than a quarter of the stored memberships and keywords is **refused**, with the numbers in the message. This is what stops a truncated or half-saved workbook becoming an authoritative deletion. `1` allows any removal |
| apply lock (advisory) | two instances booting together cannot both apply; the second reports `already_syncing`. A crashed process releases the lock with its connection |

A refusal is a log line and an `action: "refused"` in `GET /api/taxonomy/status`;
the database is untouched and the fingerprint is not recorded, so the next start
tries again rather than treating the refusal as "in sync".

**From the interface.** `GET /api/taxonomy/status` answers "is the database up to
date?" with the pending counts; `POST /api/taxonomy/sync` runs the job. Neither
can delete a category unless the request asks for it by name
(`prune_categories`), because a half-saved workbook and a deliberate deletion
look identical to the reader.

**On a schedule.** Not available yet, and not because the scheduler is missing:
`job_schedules.schedule_type` carries a CHECK constraint from `m0001` that admits
only `scenario_evaluation` and `retention`. Giving the workbook its own schedule
type therefore needs an authorised additive migration. Until then, startup and
the interface cover the unattended case.

**Continuously, on one machine.** `python3 tools/i18n/sync_taxonomy.py --watch`
applies on every save. It is what you want while editing the file.

Every one of these calls `services/importing/taxonomy_sync_service.py`, so they
cannot disagree about what the difference is.

### 3. The importer (legacy route)

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

## What an automatic run will and will not do

| it does | it does not |
|---|---|
| create categories a new worksheet describes | delete a category whose worksheet vanished (reported; `--prune-categories` says otherwise) |
| rename a category when the content proves the rename | guess a rename when the content also changed - that is reported as one missing, one new |
| add, link and unlink terms | delete a word row (a keyword phrase may reference it) |
| add and delete phrases | store a phrase in two categories (`keywords.keyword` is unique) |

An applied run also returns a snapshot of the taxonomy as it was
(`sync_workbook(..., apply=True)`), so a wrong edit can be put back with
`restore_state`. A workbook that breaks a rule is never written at all.

Undoing an apply is scoped: `restore_state(conn, snapshot, names=[...])` puts back
only the categories the sync wrote and removes only those, so a category another
user created while the sync was running survives the undo. Word rows are never
deleted by a restore - the vocabulary is shared, and an unused word is harmless
where a wrongly deleted one is not. Without `names` a restore means "the whole
taxonomy as it was", which is the right tool for a deliberate rollback and the
wrong one for undo.

## What the rules do not cover

* **Arabic names.** A term's Arabic name is not in this workbook; it lives in
  `term_names` and is not machine-translated. See
  [REGISTRY_EVIDENCE.md](REGISTRY_EVIDENCE.md).
* **Case.** The spelling in the workbook is the spelling the interface shows, so
  it is kept: the sync tool stores it as written, and the importer reuses an
  existing row whatever its casing rather than adding a twin. Because
  `words.word` is unique case-**sensitively**, two spellings could still exist
  side by side if an older build created both; both tools then pick the
  spelling you typed. Keep one spelling per file.
* **Phrase ownership beyond one category.** The schema stores a keyword once, so
  a phrase in two sheets belongs to one of them. `_Keyword Owners` records which;
  the other sheet's claim is reported, not stored.
