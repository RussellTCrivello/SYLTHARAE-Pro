# Slice: Q07 boolean OR candidate fan-out

**Status:** CLOSED (validated @990 paths, 2026-10-08)

## Q07 semantics (correctness baseline)

- `A OR B` → paths where **any** term matches **any** searchable field (filename, type, source/side name, `contents_raw`, token table when case-insensitive).
- `A OR B OR C OR D` → union of per-term matches; each path appears **once** in the result list (distinct path / hash dedup unchanged).
- `A OR missing` / `missing OR B` → still evaluates branches that can match (indexed short-circuit only when **all** OR branches are vocabulary-empty).
- Ranking, pagination, counts, filters, permissions: unchanged; flat compile affects **WHERE** predicate shape only.

## Problem

Q07 (`report OR invoice OR contract OR memo`) spent ~282 ms P95 (warm) with dominant `candidate_generation`. EXPLAIN showed **four** independent `contents_raw` sequential scans (one per OR branch) and **four** `words` seq scans per candidate query.

## Evidence

| Artifact | Role |
|----------|------|
| `docs/perf/runs/q07_or_before.jsonl` | Frozen from `search_full.jsonl` (immutable baseline) |
| `docs/search/explain/20261008T071612Z_production_Q07_boolean_or_candidate_generation.txt` | Pre-change plan (4× `contents_raw`) |
| `docs/perf/runs/q07_or_after.jsonl` | Post-change benchmark |
| `docs/search/explain/manifest_q07_or_after.json` | Post-change EXPLAIN |

### Scan counts (candidate_generation)

| Metric | Before | After |
|--------|-------:|------:|
| `contents_raw` scan nodes | 4 | **1** |
| `words` scan nodes (incl. relevance) | 8 | **5** |

## Hypothesis (confirmed)

> Pure boolean OR duplicated per-branch `EXISTS` on `contents_raw` and `words`; flattening OR terms into shared EXISTS blocks preserves OR semantics while scanning each table once per path row.

## Implementation (bounded)

1. `core/search/boolean_or_flat.py` — `flat_or_literal_sql()` for pure disjunctions (≥2 terms), default case-insensitive literal mode.
2. `Api/services/search_service.py` — route pure OR to flat compiler; `_last_literal_compile` = `flat_or` | `nested_literal`.
3. **Bind-order fix:** candidate SQL places `relevance_expr` placeholders before WHERE → `relevance_params + where_params (+ keyset)` (correctness for all relevance-sorted searches).

**Not changed:** indexed short-circuit, AND/NOT/phrase/case/whole-word paths, Q10 regex.

## Correctness

- OR semantics: document matches if **any** term matches **any** literal field (same predicate vocabulary as nested compile).
- Duplicate elimination: unchanged (`SELECT DISTINCT` / hash dedup paths).
- Tests: `tests/unit/test_search_q07_or_flat.py`, `tests/integration/test_q07_or_result_equivalence.py` (25 hits, unique IDs).

## Performance (warm)

| Metric | Before P95 | After P95 | Δ |
|--------|----------:|----------:|--:|
| Total | 282 ms | **210 ms** | **−25.6%** |
| candidate_ms | ~253 | ~189 | ↓ |

Acceptance: meaningful Q07 improvement + `contents_raw` loops ↓ without indexed-path regression (`q07_neighbor_regression.jsonl`).

## Remaining bottleneck

Candidate time still ~190–210 ms P95 on Q07 — nested loops on paths × metadata EXISTS fan-out. **Next slice:** separate EXPLAIN-driven hypothesis (not part of this change).

## Commands

```powershell
python tools/perf/search_benchmark_harness.py --cold --warm --iterations 10 --query-id Q07 --out docs/perf/runs/q07_or_after.jsonl
python tools/perf/compare_baselines.py docs/perf/runs/q07_or_before.jsonl docs/perf/runs/q07_or_after.jsonl
python tools/perf/explain_literal_search.py --query-id Q07 --manifest docs/search/explain/manifest_q07_or_after.json
python tools/perf/count_explain_scans.py docs/search/explain/<plan>.txt
```
