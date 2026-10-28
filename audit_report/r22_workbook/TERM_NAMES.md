# The multilingual link: what a sync may and may not touch (E)

Read-only investigation. **No code was added to write `term_names`, and the
workbook does not gain a name column this round.**

## What is true today (measured)

| claim | evidence | how it was measured |
|---|---|---|
| a sync apply never writes `term_names` | `tests/integration/test_term_names_survive_sync_pg.py::test_an_apply_never_writes_to_term_names` | row count before/after an apply that adds a term |
| relinking a term keeps its curated names | `test_an_apply_that_relinks_a_term_keeps_its_curated_names` | an Arabic name on the term and on the category survives an unlink and a relink |
| `prune_words` used to delete curated names | `test_pruning_an_orphan_word_keeps_its_curated_names` (fails at the previous commit) | `term_names.word_id` is `ON DELETE CASCADE`, so `DELETE FROM words` took the names with it |
| pruning still removes unnamed orphans | `test_pruning_deletes_a_word_that_nothing_names_and_nothing_uses` | the guard is specific, not a disable |

### The defect this found

`apply_plan(..., prune_words=True)` deleted any word no phrase and no category
referenced. `term_names` hangs off `words.id` with `ON DELETE CASCADE`, so an
orphan word a curator had named in Arabic or Hebrew lost its names silently - the
one kind of data in the schema that no workbook can regenerate. The sync now
skips a word that has names and reports it as `words_kept_for_names`, so the run
says what it kept.

### A second defect, found on the way

A run whose only work was pruning reported `"nothing to do"` and pruned nothing,
because `Plan.changes` counts creations, links, unlinks and phrase edits but not
removals. `sync_workbook` now treats pending pruning as work.

## Should the workbook carry a column per language?

**Decision: not yet, and not without a schema-level decision first.** The
reasons are measurable rather than aesthetic:

1. **Excel has no way to say "empty means delete".** A blank cell is what a
   curator leaves when they have not got round to a language. If a blank cell
   meant "remove the name", every sync would delete translations it never saw;
   if it meant "keep", the workbook could never remove one. That is the same
   ambiguity the shrink guard exists for, applied to a column where no guard can
   distinguish "untranslated" from "deliberately cleared".
2. **The names are per language *and* per name type.** `term_names` has
   `language`, `name_type` (`preferred`, `alternate`, `transliteration`),
   `script`, `match_key` and `source`. A single column per language can carry one
   name type; the other two would need columns or a second sheet, and `match_key`
   must be computed by the application, never typed by a human
   (`core.i18n.term_key`).
3. **The curated set is currently authored in the interface**, where each write
   is audited (`term_names:<word_id>:<language>`) and validated in one place
   (`services/i18n/term_names.py`). A workbook import would bypass the audit
   unless it went through the same service - which is the shape the taxonomy sync
   already has, so it is a work item, not an objection.
4. **Arabic and Hebrew need a native-speaker review** (one of the six standing
   challenges). A workbook column invites bulk paste, and a bulk paste is exactly
   what an unreviewed machine translation looks like.

If the owner wants it later, the shape that fits this repository is:

* one sheet per language (`_Names AR`, `_Names HE`, ...), same rule as categories:
  worksheet name = language, rows = `term` + `name` + `name_type`;
* apply through `services/i18n/term_names.py`, so validation, `match_key` and the
  audit row are the same as the interface's;
* a **names shrink guard** with the same shape as
  `SYLTHARAE_TAXONOMY_SHRINK_MAX`: a sync that would remove more than a fraction
  of the curated names is refused;
* never a blank cell as a deletion: an explicit `DELETE` marker, so that "not yet
  translated" and "remove this" are different cells.

None of this is implemented. It is written down so the next round can decide
rather than rediscover.
