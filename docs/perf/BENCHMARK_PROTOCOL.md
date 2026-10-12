# Benchmark protocol (SYLTHARAE search)

## Mode

```text
MEASURE → HYPOTHESIS → BENCHMARK → IMPLEMENT → BENCHMARK → COMPARE
```

## Runtime environment (required)

All perf tools call `tools/perf/bootstrap_runtime.py`, which loads **the same** `.env` and config overlay as `run_web.py` (`core.init._load_dotenv_file`). Do not pass a separate DSN.

Verify connectivity:

```powershell
python tools/perf/bootstrap_runtime.py
```

## Harness

| Tool | Purpose |
|------|---------|
| `tools/perf/search_benchmark_harness.py` | Query suite + JSONL stage breakdown |
| `tools/perf/word_resolution_benchmark.py` | ILIKE vs `word = ANY` |
| `tools/perf/extraction_matrix_testdoc.py` | test-doc extraction matrix |
| `tools/perf/explain_capture.py` | Store `EXPLAIN (ANALYZE, BUFFERS)` |
| `tools/perf/explain_suite.py` | Batch EXPLAIN → `docs/search/explain/` |
| `tools/perf/emit_decisions.py` | Decision JSONL + optional capacity append |
| `tools/perf/compare_baselines.py` | Baseline vs candidate JSONL (CI) |
| `tools/perf/audit_antipatterns.py` | Static anti-pattern report |
| `tools/perf/audit_ilike.py` | ILIKE/LIKE inventory |

## Cold / warm

1. **Cold:** first iteration after process start (label `phase=cold`).
2. **Warm:** repeat same query without restarting Python (`--warm`).

Report P50/P95/P99 from JSONL, not a single sample.

## Hardware

Each JSONL run includes a `meta` record from `benchmark_common.hardware_profile()`.

## Query suite

Fixed corpus: `tools/perf/query_suite.json` (Q01–Q15).

## Separation

- **Ingestion/extraction** benchmarks do not include search latency.
- **Search** benchmarks use indexed DB state only unless labeled end-to-end.
