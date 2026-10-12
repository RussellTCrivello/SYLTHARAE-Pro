# Evidence → diagnosis → optimization loop

## Policy

**No speculative performance PRs** until `docs/perf/runs/search_full_decisions.jsonl` names a dominant stage with `confidence: measured` on the target corpus.

## Commands (after `python tools/perf/bootstrap_runtime.py` shows `"connected": true`)

```powershell
python tools/perf/search_benchmark_harness.py --cold --warm --iterations 10 --out docs/perf/runs/search_full.jsonl
python tools/perf/word_resolution_benchmark.py --term-counts 1,10,100,1000 --out docs/perf/runs/word_resolution.jsonl
python tools/perf/explain_suite.py
python tools/perf/explain_advanced_search.py
python tools/perf/emit_decisions.py docs/perf/runs/search_full.jsonl
```

### Zero-result short-circuit (bounded slice)

```powershell
python tools/perf/explain_advanced_search.py
python tools/perf/search_benchmark_harness.py --cold --warm --iterations 10 --out docs/perf/runs/search_zero_shortcircuit.jsonl
python tools/perf/compare_baselines.py docs/perf/runs/search_full.jsonl docs/perf/runs/search_zero_shortcircuit.jsonl
```

Baseline `search_full.jsonl` stays immutable; post-fix evidence lives in `search_zero_shortcircuit.jsonl`.

**Slice closed:** `docs/perf/slices/SLICE_indexed_vocabulary_short_circuit.md` — do not modify the short-circuit without a new measured regression.

### PG_LITERAL diagnosis (next slice — measurement only)

```powershell
python tools/perf/emit_literal_path_decisions.py docs/perf/runs/search_full.jsonl
python tools/perf/explain_literal_search.py
```

| Artifact | Role |
|----------|------|
| `docs/perf/runs/pg_literal_path_decisions.jsonl` | Q07/Q08/Q10 decision records (`confidence: measured`, `recommended_next_test: explain_literal_candidate_sql`) |
| `docs/search/explain/manifest_literal_latest.json` | Production count + candidate EXPLAIN for OR / phrase / regex |

No PG_LITERAL implementation until EXPLAIN identifies the dominant expensive operation and one bounded hypothesis is approved.

**Slice closed:** `docs/perf/slices/SLICE_q07_or_candidate_fanout.md` — flat OR literal compilation (do not extend in this slice).

**Next:** select one new hypothesis from remaining Q07 cost or Q08/Q10 diagnosis — do not stack optimizations.

Each harness run writes `*_decisions.jsonl` with `dominant_stage`, `hypothesis`, and `recommended_next_test`.

## Decision tree

```text
search_full.jsonl → dominant_stage?
  candidate_generation → EXPLAIN + word_resolution (already run?) → targeted SQL fix → re-benchmark
  count              → timed vs exact harness
  snippet            → snippet phase benchmark (rg on/off)
  UI                 → client-perf.js TTFR/TTFC
```

## Artifacts

| Artifact | Role |
|----------|------|
| `docs/perf/CAPACITY_REPORT.md` | Human authority |
| `docs/perf/runs/*.jsonl` | Machine evidence |
| `docs/search/explain/*.txt` | Planner proof |
