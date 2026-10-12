# Search performance architecture (SYLTHARAE)

This document is the living performance contract for search. It complements the
two-stage list + snippet hydration already in production and defines how we
measure, budget, and extend the pipeline toward multi-million-file scale.

## A. Architecture diagram

```text
Browser (Advanced Search UI)
  │  AbortController, debounce, skeleton rows, deferred snippets
  ▼
GET /api/search  (?fast_mode=true, include_snippets=false)
  │  X-Request-ID / X-Search-Correlation-ID
  ▼
Query planner (core/search/planner.py)
  │  complexity class + engine route
  ▼
PostgreSQL candidate generation
  │  inverted index (words_hashs), metadata filters, SQL relevance
  │  LIMIT/OFFSET (page 1) or keyset cursor (`pagination.cursor`, relevance desc)
  ▼
Metadata response (Level 0 retrieval)
  │
  ├─► optional timed COUNT (count_mode=timed|exact|skip)
  │
POST /api/search/snippets  (Level 1–2 retrieval)
  │  bounded contents_raw window (not full document)
  │  ripgrep JSON line discovery on in-memory/temp corpus
  ▼
Snippet highlight + match badges → DOM patch
```

Background (not on interactive path): ingestion → token index, contents_raw,
BM25-precompute (optional future), cache warming.

## B. Performance budgets (interactive)

| Stage | P50 target | P95 target | P99 target |
|-------|------------|------------|------------|
| Initial result list | 100 ms | 300 ms | 750 ms |
| Snippet hydration (page) | — | 750 ms | 1500 ms |
| Single DB query warn | — | 50 ms | 100 ms |

Budgets are enforced via `core/search/perf.py` spans returned in API
`meta.timings` and `Server-Timing` headers.

## C. Instrumentation

Each `/api/search` request creates a `SearchTrace` with:

- `correlation_id` (from `X-Request-ID` or generated)
- spans: `advanced_search`, `db_count`, `db_candidates`, `io_text_windows`, …

Use the correlation ID in logs to tie browser → API → SQL.

**Baseline tool:** `python tools/perf/search_benchmark_harness.py` (structured JSONL; see `docs/perf/BENCHMARK_PROTOCOL.md`)

Legacy single-metric script: `python tools/perf/search_pipeline_benchmark.py`

**Regression:** extend CI to fail when list median regresses >15% vs stored baseline
(Phase 8 — not yet wired to CI).

## D. Search routing (planner)

| Class | Typical query | Primary engine | Snippets |
|-------|---------------|----------------|----------|
| METADATA | filters only | PostgreSQL | deferred |
| INDEXED_TERM | plain terms | PG inverted index | rg on bounded raw text |
| PG_LITERAL | quotes, boolean, case | PostgreSQL literals | rg bounded |
| REGEX_PCRE | regex features | slow SQL / rg | rg (-P only if required) |
| HYBRID | metadata + terms | PG filter → candidates | rg on windows |

**Ripgrep vs PostgreSQL:** ripgrep is **not** a replacement for the inverted
index at millions of files. It accelerates **bounded snippet extraction** on
already-selected path IDs against `contents_raw` windows. Full-corpus `rg` over
original files is benchmarked separately (`tools/perf/search_engine_compare.py`
— add dataset before trusting numbers).

## E. Retrieval levels

| Level | What loads | Used for |
|-------|------------|----------|
| 0 | path metadata, score | list API |
| 1 | first N KB of contents_raw | snippet hydration |
| 2 | match windows + rg | highlighted context |
| 3 | full extracted text | file detail / explicit user action |

Implementation: `core/search/retrieval.py`.

## F. Count strategies

| mode | behaviour |
|------|-----------|
| `exact` | full COUNT |
| `timed` | COUNT with `statement_timeout` (default 250 ms) |
| `skip` | no COUNT; pagination without total |

API exposes `pagination.total_is_approximate` when timed count fails.

## G. Index strategy

| Index | Purpose |
|-------|---------|
| `idx_words_hashs_hash_id` | file → words |
| `idx_words_hashs_hash_word` | hash-scoped term lookup (m0035) |
| `idx_words_hashs_word_hash` | word → files (m0036) |

Run `EXPLAIN (ANALYZE, BUFFERS)` on candidate + count queries per release;
store outputs under `docs/search/explain/` (manual step until automated).

## H. Phased implementation plan

### Phase 1 — Immediate wins (in progress)

- [x] Two-stage list + snippets
- [x] SQL pagination + no BM25 on hot path
- [x] Bounded text windows + parallel snippet load
- [x] Timed/skipped counts
- [x] Request tracing + planner metadata
- [ ] Keyset pagination for deep pages
- [ ] Frontend virtualization (TanStack Virtual) when per_page > 50

### Phase 2 — Database / indexes

- [x] Composite inverted indexes (both orders)
- [ ] EXPLAIN corpus checked into repo
- [ ] Word-id resolution for terms (avoid ILIKE on `words.word` at scale)
- [ ] Statistics / autovacuum review on `words_hashs`, `paths`

### Phase 3 — Search engine evaluation

- [ ] Benchmark matrix: PG vs inverted vs rg vs hybrid (measured, not assumed)
- [ ] Optional on-disk search cache of normalized text (storage cost analysis)

### Phase 4 — API concurrency

- [ ] Server-side search cancellation → terminate rg subprocesses
- [ ] Snippet worker pool sized from settings + load

### Phase 5 — Frontend

- [x] Skeleton snippets, abort stale searches
- [ ] Virtualized lists, dedupe snippet fetches

### Phase 6 — Caching

- [ ] Normalized query cache keys (`core/search/normalize.py`) → metadata cache
- [ ] Snippet cache keyed by (cache_key, file_ids)

### Phase 7 — Stress testing

- [ ] Concurrent search harness (1–100 users)
- [ ] Adversarial query suite

### Phase 8 — Regression CI

- [ ] `search_pipeline_benchmark.py` baselines in repo

## I. Bottleneck report (template — fill with measurements)

Run benchmark on your hardware and rank:

1. _TBD_ — db_count
2. _TBD_ — db_candidates
3. _TBD_ — io_text_windows
4. _TBD_ — ripgrep batch
5. _TBD_ — JSON serialization
6. _TBD_ — browser render

## J. Decision matrix (populate with benchmarks)

See directive §24 — do **not** treat cells as true until
`tools/perf/search_engine_compare.py` results are recorded for your dataset.

## K. Principles (non-negotiable)

1. Database filters and ranks candidates; Python does not scan thousands of docs for page 1.
2. Full text loads only at Level 3 or bounded windows at Level 1–2.
3. Snippets are deferred and parallel-bounded.
4. Exact totals must not block interactive search (`timed` / `skip`).
5. Obsolete browser requests are aborted; server-side cancellation is next.
6. No new infrastructure (Redis, Elasticsearch, etc.) without measured win on this app.
