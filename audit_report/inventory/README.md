# Inventory verdicts — how each row earned its status

The eleven inventories below are **generated**, not written:

| script | produces |
|---|---|
| `tools/audit/build_inventories.py` | `routes`, `templates`, `js_modules`, `css`, `schema`, `modules`, `sql`, `jobs`, `env_vars`, `i18n_msgids`, `interfaces` |
| `tools/audit/probe_routes.py` | `routes_runtime` (every role × every parameterless GET/POST) |
| `tools/audit/probe_mutations.py` | `findings/mutations_runtime` (empty-body sweep over mutating routes) |
| `tools/audit/browser_walk.py` | `browser/walk.json` (35 pages in Chromium) |
| `tools/audit/apply_verdicts.py` | the **status** column of every file above |

Generation answers *what exists*. `apply_verdicts.py` answers *whether it works*,
and it only accepts evidence that some other step recorded. Running it twice
produces the same file (the runtime verdict is re-derived from the recorded
status codes, not from its own previous output).

## Allowed verdicts

`VERIFIED-OK` · `FIXED+TEST` · `DEFECT-OPEN` · `NEEDS-DECISION` ·
`ENV-BLOCKED` · `DEAD-CODE`

A verdict may carry a `: reason` suffix; the token before the colon is what the
checker counts. `python tools/audit/apply_verdicts.py --check` fails if any row
carries anything else (in particular, `UNTOUCHED`).

## The rule for each inventory

| inventory | verdict rule |
|---|---|
| `routes_runtime` | `DEFECT-OPEN` if any of the four roles got a 5xx or a transport error; otherwise `VERIFIED-OK` (re-derived from `anon/viewer/analyst/admin`). |
| `routes` | `VERIFIED-OK` when the rule+method was executed by the role matrix or the mutation sweep; `FIXED+TEST` for a route this audit repaired; `ENV-BLOCKED` naming the exact blocker when neither probe can reach it (path-parameterised routes have no fixture row; `/auth/logout` ends the session mid-sweep). |
| `interfaces` | `VERIFIED-OK` when the browser walk returned 200 with no page errors; `FIXED+TEST` for the two pages whose missing `<h1>` was repaired. |
| `templates` | `VERIFIED-OK` when a route renders it, or another template includes it, or code renders it by name; otherwise `DEAD-CODE`. |
| `schema` | live `pg_catalog` against the frozen `m0001–m0003` chain (columns parsed with paren depth, `ALTER TABLE … ADD COLUMN` included). `schema_migrations` is bookkeeping, not domain schema. |
| `sql` | `VERIFIED-OK` unless `findings/sql_schema.csv` records a statement that disagrees with the schema. |
| `i18n_msgids` | `complete` → `VERIFIED-OK`; `gap` → `DEFECT-OPEN` (a translation is missing); `unused` → `NEEDS-DECISION` (prune, or keep for a dynamic key). |
| `env_vars` | documented → `VERIFIED-OK`; read by code but undocumented → `DEFECT-OPEN`. |
| `css` / `js_modules` | referenced by a template, stylesheet or ES import → `VERIFIED-OK`; otherwise `DEAD-CODE`. |
| `modules` | imported, a package marker, an entry point (`__main__`, WSGI, migration), or named from a test/script/doc → `VERIFIED-OK`; otherwise `DEAD-CODE`. |
| `jobs` | vocabulary declared in code (`code vocabulary`, the dispatch table, the scheduler module) → `VERIFIED-OK`. |

## Totals (this run)

See `verdict_summary.json` for the machine-readable version, and
`../R3_verification_report.md` for the narrative. Every row of every inventory
carries one of the six verdicts; there are no `UNTOUCHED` rows left.
