# Capacity report (authoritative performance record)

Update this file from measured JSONL runs only. Do **not** fill cells from intuition.

**Evidence loop:** `search_benchmark_harness.py` → `*_decisions.jsonl` → `emit_decisions.py` (optional append) → this document.

## Hardware profile

| Field | Value |
|-------|-------|
| Host | DESKTOP-886JEBE |
| CPU | Intel64 Family 6 Model 186 (4 cores) |
| RAM | 32 GB |
| OS | Windows 10.0.26300 |
| PostgreSQL | 18.6 |
| Corpus | **990 paths**, **39,355 words**, DB **~40 MB** |
| Schema | m0036_words_hashs_word_hash_index |
| Run | `docs/perf/runs/search_full.jsonl` (2026-10-08) |

## Search latency matrix

| Corpus | Query | Engine | P50 | P95 | P99 | Results | Region | Notes |
|-------:|-------|--------|----:|----:|----:|--------:|--------|-------|
| 990 | common (`report`) warm | PG_INVERTED | 0.57 | 2.2 | 2.2 | 0 | GREEN | fast when term resolves / empty set cheap |
| 990 | zero-result warm | PG_INVERTED | 338 | **393** | 393 | 0 | **RED** | baseline (pre short-circuit) |
| 990 | rare miss warm | PG_INVERTED | 314 | **455** | 455 | 0 | **RED** | baseline (pre short-circuit) |
| 990 | zero-result warm | PG_INVERTED | 0.001 | **0.001** | 0.001 | 0 | **GREEN** | `short_circuit=true` — `search_zero_shortcircuit.jsonl` |
| 990 | rare miss warm | PG_INVERTED | 0.001 | **0.002** | 0.002 | 0 | **GREEN** | mandatory indexed term miss; candidate SQL skipped |
| 990 | OR union warm | PG_LITERAL | 260 | 282 | 282 | 25 | YELLOW | literal engine, ~280ms P95 |
| 990 | multi-AND warm | PG_INVERTED | 0.60 | 0.96 | 0.96 | 0 | GREEN | fast path when word_ids resolve |

**Region:** GREEN = meets interactive target · YELLOW = usable, near capacity · RED = architectural intervention required

## Word resolution (ILIKE vs ANY)

_Source: `docs/perf/runs/word_resolution.jsonl`_

| Terms sampled | ILIKE P95 (ms) | ANY P95 (ms) | Winner | Region |
|--------------:|---------------:|-------------:|--------|--------|
| 1 | 16.3 | 0.75 | **ANY (idx_words_word)** | GREEN |
| 10 | 17.0 | 1.0 | **ANY** | GREEN |
| 100 | 15.7 | 0.82 | **ANY** | GREEN |
| 1000 | 19.5 | 0.96 | **ANY** | GREEN |

EXPLAIN: ILIKE `%report%` → **Seq Scan** on `words` (39318 rows removed); `word = ANY` → **Bitmap Index Scan** on `idx_words_word` (~0.1ms exec).

## Extraction (test-doc)

_Source: `docs/perf/runs/extraction_testdoc.jsonl` — **ingestion only**, not search engine selection._

| Tier | Count | Notes |
|------|------:|-------|
| GREEN | 130 | Predictable text/HTML/CSV-class extractions |
| YELLOW | 464 | Slow or empty output (media, archives, OCR edge cases) |
| RED | 114 | Unsupported reader / encrypted / failed |

P95 extraction latency **~4.5 s** per file on this host (test-doc matrix). **Ingestion workload — separate resource class from search.**

## Dominant bottleneck (latest measured run)

_From `search_full_decisions.jsonl` — highest `dominant_share_pct` with `confidence=measured`._

| Query class | Dominant stage | Share % | Hypothesis | Next test |
|-------------|----------------|--------:|------------|-----------|
| **zero_result / rare miss (fixed @990)** | word_resolution + short-circuit | ~100% | Mandatory term absent from `words` → skip count/candidate | Scale test @100K/1M when corpus available |
| **zero_result / rare miss (baseline)** | candidate_generation | 78–86 | Full candidate SQL before empty known | superseded by indexed-vocabulary short-circuit |
| indexed multi-AND | candidate_generation | 57–62 | Fast word_id path OK when terms exist | Keep; validate on 100K+ corpus |
| OR / boolean literal | candidate_generation | 73–90 | PG_LITERAL path cost | EXPLAIN literal branch only |

## Operating envelope

| Region | Condition | Behavior |
|--------|-----------|----------|
| GREEN | P95 list &lt; 100 ms, zero-result &lt; 50 ms | Normal interactive + deferred snippets |
| YELLOW | P95 100–300 ms | Throttle background / approximate counts |
| RED | Zero-result P95 &gt; 300 ms (measured **393 ms** @ 990 files) | **Next optimization target** — not UI/virtualization |

## Optimization policy

No speculative performance PRs until a row above shows `confidence: measured` and names the dominant stage.

## Measured runs (auto-appended)

| Corpus | Query | Engine | P50 | P95 | P99 | Results | Dominant | Share% | Confidence |
|-------:|-------|--------|----:|----:|----:|--------:|----------|-------:|------------|
| 990 | very_common_term | PG_INVERTED | 0.513 | 0.848 | 0.848 | 0 | candidate_generation | 60.3 | measured |
| 990 | very_common_term | PG_INVERTED | 0.522 | 0.738 | 0.738 | 0 | candidate_generation | 61.1 | measured |
| 990 | common_business_term | PG_INVERTED | 0.505 | 0.724 | 0.724 | 0 | candidate_generation | 69.1 | measured |
| 990 | common_business_term | PG_INVERTED | 0.573 | 2.215 | 2.215 | 0 | candidate_generation | 23.8 | measured |
| 990 | rare_term | PG_INVERTED | 387.772 | 702.69 | 702.69 | 0 | candidate_generation | 47.0 | measured |
| 990 | rare_term | PG_INVERTED | 314.403 | 455.377 | 455.377 | 0 | candidate_generation | 68.1 | measured |
| 990 | zero_result | PG_INVERTED | 335.686 | 453.059 | 453.059 | 0 | candidate_generation | 78.2 | measured |
| 990 | zero_result | PG_INVERTED | 338.198 | 393.174 | 393.174 | 0 | candidate_generation | 86.0 | measured |
| 990 | two_term_and | PG_LITERAL | 126.105 | 181.58 | 181.58 | 1 | candidate_generation | 90.0 | measured |
| 990 | two_term_and | PG_LITERAL | 160.121 | 276.931 | 276.931 | 1 | candidate_generation | 65.9 | measured |
| 990 | multi_term_and | PG_INVERTED | 0.821 | 1.317 | 1.317 | 0 | candidate_generation | 62.0 | measured |
| 990 | multi_term_and | PG_INVERTED | 0.599 | 0.958 | 0.958 | 0 | candidate_generation | 57.2 | measured |
| 990 | or_union | PG_LITERAL | 289.825 | 377.844 | 377.844 | 25 | candidate_generation | 72.7 | measured |
| 990 | or_union | PG_LITERAL | 259.979 | 282.154 | 282.154 | 25 | candidate_generation | 89.8 | measured |
| 990 | phrase | PG_LITERAL | 57.939 | 72.891 | 72.891 | 0 | candidate_generation | 89.0 | measured |
| 990 | phrase | PG_LITERAL | 59.721 | 72.367 | 72.367 | 0 | candidate_generation | 100.0 | measured |
| 990 | case_sensitive | PG_LITERAL | 26.993 | 30.705 | 30.705 | 15 | candidate_generation | 100.0 | measured |
| 990 | case_sensitive | PG_LITERAL | 26.903 | 38.054 | 38.054 | 15 | candidate_generation | 70.1 | measured |
| 990 | regex | PG_INVERTED | 525.656 | 745.507 | 745.507 | 0 | candidate_generation | 70.5 | measured |
| 990 | regex | PG_INVERTED | 503.893 | 578.693 | 578.693 | 0 | candidate_generation | 80.3 | measured |
| 990 | pcre2 | PG_INVERTED | 50.89 | 61.673 | 61.673 | 0 | candidate_generation | 77.7 | measured |
| 990 | pcre2 | PG_INVERTED | 49.332 | 57.193 | 57.193 | 0 | candidate_generation | 85.9 | measured |
| 990 | filename_metadata | PG_INVERTED | 0.545 | 2.155 | 2.155 | 0 | candidate_generation | 23.7 | measured |
| 990 | filename_metadata | PG_INVERTED | 0.537 | 1.63 | 1.63 | 0 | candidate_generation | 28.7 | measured |
| 990 | metadata_plus_content | PG_INVERTED | 0.514 | 1.337 | 1.337 | 0 | candidate_generation | 37.8 | measured |
| 990 | metadata_plus_content | PG_INVERTED | 0.508 | 1.641 | 1.641 | 0 | candidate_generation | 30.7 | measured |
| 990 | huge_result_set | PG_METADATA | 2.347 | 5.368 | 5.368 | 50 | candidate_generation | 40.1 | measured |
| 990 | huge_result_set | PG_METADATA | 2.259 | 3.183 | 3.183 | 50 | candidate_generation | 61.6 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.564 | 1.701 | 1.701 | 0 | candidate_generation | 99.5 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.737 | 2.519 | 2.519 | 0 | candidate_generation | 13.9 | measured |
| 990 | deep_pagination | PG_INVERTED | 2.212 | 2.212 | 2.212 | None | candidate_generation | 99.5 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.617 | 0.617 | 0.617 | None | candidate_generation | 99.2 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.715 | 0.715 | 0.715 | None | candidate_generation | 98.7 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.423 | 0.423 | 0.423 | None | candidate_generation | 98.8 | measured |

## Measured runs (auto-appended)

| Corpus | Query | Engine | P50 | P95 | P99 | Results | Dominant | Share% | Confidence |
|-------:|-------|--------|----:|----:|----:|--------:|----------|-------:|------------|
| 990 | very_common_term | PG_INVERTED | 0.476 | 1.118 | 1.118 | 0 | candidate_generation | 36.1 | measured |
| 990 | very_common_term | PG_INVERTED | 0.457 | 0.622 | 0.622 | 0 | candidate_generation | 67.7 | measured |
| 990 | common_business_term | PG_INVERTED | 0.539 | 1.062 | 1.062 | 0 | candidate_generation | 99.7 | measured |
| 990 | common_business_term | PG_INVERTED | 0.591 | 1.091 | 1.091 | 0 | candidate_generation | 83.9 | measured |
| 990 | rare_term | PG_INVERTED | 0.001 | 0.002 | 0.002 | 0 | candidate_generation | 0.0 | measured |
| 990 | rare_term | PG_INVERTED | 0.001 | 0.002 | 0.002 | 0 | candidate_generation | 0.0 | measured |
| 990 | zero_result | PG_INVERTED | 0.001 | 0.001 | 0.001 | 0 | candidate_generation | 0.0 | measured |
| 990 | zero_result | PG_INVERTED | 0.001 | 0.001 | 0.001 | 0 | candidate_generation | 0.0 | measured |
| 990 | two_term_and | PG_LITERAL | 111.341 | 134.196 | 134.196 | 1 | candidate_generation | 83.0 | measured |
| 990 | two_term_and | PG_LITERAL | 113.33 | 117.916 | 117.916 | 1 | candidate_generation | 95.3 | measured |
| 990 | multi_term_and | PG_INVERTED | 0.58 | 2.144 | 2.144 | 0 | candidate_generation | 26.3 | measured |
| 990 | multi_term_and | PG_INVERTED | 0.674 | 0.839 | 0.839 | 0 | candidate_generation | 80.0 | measured |
| 990 | or_union | PG_LITERAL | 226.34 | 232.141 | 232.141 | 25 | candidate_generation | 94.5 | measured |
| 990 | or_union | PG_LITERAL | 217.751 | 337.068 | 337.068 | 25 | candidate_generation | 97.9 | measured |
| 990 | phrase | PG_LITERAL | 49.097 | 72.508 | 72.508 | 0 | candidate_generation | 100.0 | measured |
| 990 | phrase | PG_LITERAL | 53.233 | 191.897 | 191.897 | 0 | candidate_generation | 25.3 | measured |
| 990 | case_sensitive | PG_LITERAL | 22.712 | 48.996 | 48.996 | 15 | candidate_generation | 49.0 | measured |
| 990 | case_sensitive | PG_LITERAL | 28.353 | 34.098 | 34.098 | 15 | candidate_generation | 69.7 | measured |
| 990 | regex | PG_INVERTED | 461.614 | 484.672 | 484.672 | 0 | candidate_generation | 96.3 | measured |
| 990 | regex | PG_INVERTED | 452.983 | 521.583 | 521.583 | 0 | candidate_generation | 83.7 | measured |
| 990 | pcre2 | PG_INVERTED | 46.049 | 56.844 | 56.844 | 0 | candidate_generation | 83.4 | measured |
| 990 | pcre2 | PG_INVERTED | 49.005 | 60.833 | 60.833 | 0 | candidate_generation | 78.7 | measured |
| 990 | filename_metadata | PG_INVERTED | 0.455 | 1.044 | 1.044 | 0 | candidate_generation | 61.1 | measured |
| 990 | filename_metadata | PG_INVERTED | 0.471 | 2.541 | 2.541 | 0 | candidate_generation | 18.4 | measured |
| 990 | metadata_plus_content | PG_INVERTED | 0.461 | 1.736 | 1.736 | 0 | candidate_generation | 26.4 | measured |
| 990 | metadata_plus_content | PG_INVERTED | 0.567 | 3.339 | 3.339 | 0 | candidate_generation | 33.6 | measured |
| 990 | huge_result_set | PG_METADATA | 2.753 | 3.091 | 3.091 | 50 | candidate_generation | 74.5 | measured |
| 990 | huge_result_set | PG_METADATA | 2.583 | 5.177 | 5.177 | 50 | candidate_generation | 44.5 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.49 | 2.834 | 2.834 | 0 | candidate_generation | 17.1 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.489 | 1.883 | 1.883 | 0 | candidate_generation | 38.5 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.4 | 0.4 | 0.4 | None | candidate_generation | 99.0 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.58 | 0.58 | 0.58 | None | candidate_generation | 99.5 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.659 | 0.659 | 0.659 | None | candidate_generation | 99.2 | measured |
| 990 | deep_pagination | PG_INVERTED | 0.419 | 0.419 | 0.419 | None | candidate_generation | 99.3 | measured |

## Measured runs (auto-appended)

| Corpus | Query | Engine | P50 | P95 | P99 | Results | Dominant | Share% | Confidence |
|-------:|-------|--------|----:|----:|----:|--------:|----------|-------:|------------|
| 990 | or_union | PG_LITERAL | 212.62 | 329.029 | 329.029 | 25 | candidate_generation | 67.0 | measured |
| 990 | or_union | PG_LITERAL | 194.832 | 209.912 | 209.912 | 25 | candidate_generation | 89.9 | measured |
