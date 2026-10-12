# ADR-001: Fast word_id resolution for plain-term search

## Problem

Plain-term candidate generation used broad `ILIKE` / `to_tsvector` paths against `words`, which does not scale to tens of millions of vocabulary rows.

## Options

1. Keep ILIKE-heavy EXISTS subqueries.
2. Resolve tokens with `words.word = ANY(%s)` then constrain `words_hashs` by `word_id` (AND semantics).
3. Add a separate trie / external lexicon service.

## Measurements

Benchmark with `tools/perf/search_pipeline_benchmark.py` and `EXPLAIN (ANALYZE, BUFFERS)` captured under `docs/search/explain/` (Wave 1 gate).

## Decision

Use option 2 for case-insensitive plain terms (no boolean/quotes/whole-word) when every token resolves to a `words.id`. Planner sets `use_fast_word_ids`; SQL uses `inverted_index_and_clause`.

## Trade-offs

- Requires normalized `words.word` keys (lowercase storage).
- Prefix / fuzzy recall falls back to the legacy path.
- Multi-token AND is exact on inverted index, not stemmed synonyms.

## Rejected

Option 3 — no measured requirement for extra infrastructure (directive §51).

## Reconsider when

Stemming/synonym expansion must share the fast path, or vocabulary exceeds RAM-cached `words` lookups.
