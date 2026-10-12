# Slice: PG_LITERAL diagnosis (in progress)

**Status:** PARTIAL — Q07 implemented in separate slice; Q08/Q10 still diagnosis-only

## Scope

| Query | Class | Baseline warm P95 | Engine (planner) |
|-------|-------|------------------:|------------------|
| Q07 | boolean_or | 282 ms | PG_LITERAL |
| Q08 | phrase | 72 ms | PG_LITERAL |
| Q10 | regex | 579 ms | PG_INVERTED (slow plain path; regex heuristic skips indexed short-circuit) |

Decision records: `docs/perf/runs/pg_literal_path_decisions.jsonl`

## Commands

```powershell
python tools/perf/emit_literal_path_decisions.py docs/perf/runs/search_full.jsonl
python tools/perf/explain_literal_search.py
```

EXPLAIN manifest: `docs/search/explain/manifest_literal_latest.json`

## Initial EXPLAIN signals (@990 paths, production SQL)

Review full plans under `docs/search/explain/*Q07*`, `*Q08*`, `*Q10*`.

| Query | Stage | Exec time (ms) | Dominant plan signals (first pass) |
|-------|-------|---------------:|-------------------------------------|
| Q07 | candidate | ~215 | Nested loop + hash join; repeated **Seq Scan on `contents_raw`** per OR branch; **Seq Scan on `words`** (~12 ms each) |
| Q07 | count | ~149 | Same literal predicate shape, lower row width |
| Q08 | (see manifest) | (see manifest) | Phrase literal across metadata + content EXISTS |
| Q10 | candidate | ~397 | **Nested loop** dominated; seq scan pattern on candidate path (regex not short-circuited) |

**Not yet concluded:** whether the next bounded change is word-table access, content EXISTS, boolean OR shape, or join order — requires one approved hypothesis per query class.

## Gate before implementation

1. Pick **one** query class (likely Q07 or Q10 by cost).
2. Write a single-sentence hypothesis tied to a specific plan node.
3. Define the acceptance benchmark (same harness, same corpus).
4. Implement one bounded change.
5. Re-run `search_benchmark_harness.py` + `compare_baselines.py`.
