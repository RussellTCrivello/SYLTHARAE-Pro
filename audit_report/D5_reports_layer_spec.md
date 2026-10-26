# D-5 — a reports run layer, one page to decide on

**Status: not built.** This is the specification requested so the decision can be made
without reading code. Everything asserted here about what exists was read from this
checkout; nothing was invented.

## Why there is a decision at all

Three callers need a module that does not exist:

| caller | needs |
| --- | --- |
| `tests/unit/test_analytics_measures.py` | `core.reporting.datasets.KEYNESS_SIGNIFICANT_G2` and `TERM_KEYNESS_TOTALS_V1.sql` |
| `tests/unit/test_bandit_triage_fixes.py` | `core.reporting.model._ID`, `._HELP_TOPIC` |
| `tools/perf/keyness_perf.py`, `tools/i18n/sync_report_translations.py` | `REGISTRY.report(...)`, `.dataset(...)`, `.translation_keys()`, `.translation_plurals()`, plus `services.reporting.runs.submit_run/execute_run/get_run` |

`git log --all -- core/reporting` and `-- services/reporting/runs.py` are both empty: there
is no earlier implementation to restore. `core/analytics/__init__.py` still documents the
intended shape — "analyses are computed by the report runner from the dataset rows of a
run's single snapshot (`services/reporting/runs.py`) and stored with the run (m0026)" —
and `database/migrations/m0001_baseline.py` records that `report_artifacts`,
`report_baselines`, `report_run_analyses` and `report_run_datasets` were **deliberately
removed** from the frozen schema. So the layer is a rebuild against a schema that no
longer has its tables, which is why it is a decision and not a chore.

## 1. Datasets

A dataset is one reviewed SQL statement with a declared contract, addressed as
`id@version`:

```python
Dataset(
    key="term_keyness_totals@1",
    semantics="exact",                     # exact | top_n | capped
    columns=(Column("target_tokens", "bigint"), ...),
    bind=lambda values, scope: Bound(sql=..., params={...}),
)
```

* Every value is a **bound parameter**. The two existing scope helpers
  (`core/criteria/compiler.AccessScope`) supply the visibility clause, exactly as
  `services/detection/signal_query.py` already does.
* `semantics` is checked against the `InputRole` a `Kind` declares
  (`core/analytics/kinds.py`), so a `capped` listing can never be handed to a kind that
  demands `exact`. That check already exists in `Analysis.compute()` and must not be
  bypassed.
* The datasets to ship first, because the kinds already exist and name them:
  `term_keyness_ranked@1` (top_n), `term_keyness_totals@1` (exact) for `keyness@1|2`;
  `comprehensive_overview@1` (exact) for `composition@1`; `coverage_overview`,
  `coverage_keywords`, `coverage_categories` (capped) for `coverage@1`.
* **The unknown that blocks a facade today**: `term_keyness_totals@1` must expose the
  G2 threshold as SQL text (`>= 15.13`, i.e. `core.analytics.thresholds.LL_P0001`) for
  `test_analytics_measures` to assert against. No keyness statement exists in the
  repository, so writing it means writing product SQL (over `words_hashs` →
  `words` → `hash_contexts` → `paths`), not renaming anything.

## 2. Run lifecycle

```
submit_run(conn, user, report_id, parameters) -> {"id", "status": "queued"}
execute_run(conn, run_id)                     -> {"status": "completed", "analyses": [...]}
get_run(conn, run_id, user)                   -> stored run, scoped to the caller
```

1. **Submit** validates `parameters` through `REGISTRY.report(report_id).normalize_parameters()`
   — same discipline as `services/monitoring/scenario_model` — and computes a
   `criteria_fingerprint` so an identical request is identifiable.
2. **Execute** opens **one** transaction at `REPEATABLE READ`, binds every dataset in it,
   stores each dataset's rows **once**, then computes each analysis from *those stored
   rows only* (never a second query). That is the property the analytics package was
   designed around: an artifact must be readable as evidence of what the run saw.
3. **States**: `queued → running → completed | failed`, plus `cancelled`. A failed run
   stores the error text and no analyses; a run never half-completes.
4. **Access**: `get_run` filters by the caller's scope; an unknown or out-of-scope id is
   a 404, not a 403 (the same rule the rest of the API follows).

## 3. Storage without new tables

The schema is frozen, so the run record has to live in tables that exist. Two candidates,
and one that is not:

* **`jobs` + `job_events` (recommended).** `jobs` already has `job_type`, `status`,
  `options JSONB`, `stats JSONB`, `errors`, `warnings`, `result_summary JSONB`,
  `created_by`, timestamps, cancellation and pause flags, and `job_events` has
  `event_type` (constrained) + `payload JSONB`. A run is a job of type `report_run`; each
  dataset result and each analysis is a `job_event` payload; the summary goes in
  `stats`. Nothing new is created; `GET /api/jobs` starts showing reports for free, which
  is also the honest fix for the M-2 class of problem (process-local work that disappears).
  Cost: `job_events.event_type` has a `CHECK` list — a new event type is a **schema
  change** and needs your approval, or the layer reuses an existing generic event type.
* **`scenario_evaluations` as the pattern, not the table.** It proves the shape
  (`counts JSONB`, `report JSONB`, `criteria_fingerprint`, `definition_fingerprint`,
  `status`, `started_at`/`finished_at`), but it is foreign-keyed to `scenarios`, so a
  report run cannot use it without pretending to be a scenario.
* **Not an option: re-creating `report_run_datasets` / `report_run_analyses`.** Those were
  removed on purpose; re-adding them is a schema change and contradicts the freeze.

## 4. Tests the layer ships with

1. `test_a_dataset_binds_nothing_but_parameters` — the SQL text contains no literal that
   came from `parameters`; the params mapping carries them.
2. `test_a_kind_rejects_a_dataset_of_the_wrong_semantics` — bind a `capped` dataset into
   an `exact` role and assert `AnalysisError`.
3. `test_every_dataset_in_a_run_is_read_in_one_snapshot` — two datasets see the same
   `count(*)` while a concurrent insert commits.
4. `test_a_completed_run_is_readable_without_touching_the_source_tables` — drop the
   analyses' inputs (or use a read-only role) and still render the run from its stored
   rows.
5. `test_a_run_of_another_user_is_a_404` — scope, not role.
6. `test_the_keyness_threshold_is_the_sourced_one` — the same assertion
   `tests/unit/test_analytics_measures.py` already makes, moved onto the real dataset.

## 5. What it costs, and the three options

| option | work | clears |
| --- | --- | --- |
| **A. leave it open** | none | nothing (3 cases stay red, honestly attributed) |
| **B. declaration-only facade** | ~150 lines: registry, dataset ids, the two anchored validators; no SQL | 2 `test_bandit_triage_fixes` cases; adds a module no product code calls |
| **C. build the layer** (this spec) | 5 datasets of real SQL + run engine + tests, ≈1–2 days, plus the `job_events` event-type decision | 3 cases, two audit tools, and a run history the API can show |

**Recommendation: C, split in two.** First the dataset registry with
`term_keyness_totals@1` written and verified against a measured corpus
(`EXPLAIN ANALYZE`, `tools/perf/keyness_perf.py` already loads one), because that is the
only part with a real unknown in it. Then the run lifecycle on `jobs`/`job_events`, once
you have agreed the event-type question. B is cheap but leaves the only assertion that
matters — that the SQL threshold is the sourced constant — still untested.
