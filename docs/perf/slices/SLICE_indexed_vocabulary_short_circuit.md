# Slice: indexed-vocabulary zero-result short-circuit

**Status:** CLOSED (validated on 990-path corpus, 2026-10-08)

## Hypothesis

Missing mandatory indexed vocabulary term → expensive candidate-generation SQL despite provably empty result.

## Evidence chain

| Step | Artifact |
|------|----------|
| Measure | `docs/perf/runs/search_full.jsonl` |
| Diagnose | Q03/Q04 dominant stage `candidate_generation` (~78–86%) |
| EXPLAIN (indexed) | `docs/search/explain/manifest_latest.json`, `explain_advanced_search.py` |
| Implement | `core/search/short_circuit.py`, `Api/services/search_service.py` |
| Regression | `tests/unit/test_search_zero_shortcircuit.py` |
| Re-benchmark | `docs/perf/runs/search_zero_shortcircuit.jsonl` |
| Compare | `compare_baselines.py` vs immutable baseline |

## Validated outcome (warm P95)

| Query | Before | After | candidate_ms |
|-------|-------:|------:|-------------:|
| Q03 rare miss | 455 ms | ~0.002 ms | 0 |
| Q04 zero-result | 393 ms | ~0.001 ms | 0 |

Resolved indexed searches (e.g. Q02, Q06) unchanged within benchmark noise.

## Architectural result

```text
missing indexed vocabulary term
  → word resolution (word = ANY)
  → provably empty (AND / boolean rules)
  → STOP (no db_count, no db_candidates)
```

## Do not revisit

No further changes to this short-circuit unless a **measured** regression or correctness bug appears.

## Next investigation (separate slice)

**PG_LITERAL diagnosis** — Q07 boolean OR, Q08 phrase, Q10 regex. Measurement and EXPLAIN only until one bounded hypothesis is approved.
