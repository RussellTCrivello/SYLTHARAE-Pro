# Duplicate index shapes in the frozen baseline

Produced by `python tools/db/integrity_audit.py --json` against a freshly
migrated database on 2026-10-24 (`redundant_indexes`, 5 rows). Each row is two
indexes over the same table and columns; one of each pair is redundant for
lookups.

They are **registered, not removed**: dropping an index is a schema change
(`database/migrations` is frozen), and the redundant one in each pair is the
one the baseline created first. `tests/integration/test_db_integrity_audit.py`
keeps this list as its expectation, so a *new* duplicate shape still fails the
gate.

| table | shape | indexes |
| --- | --- | --- |
| `categorys` | `USING btree (word_id)` | `categorys_word_id_key`, `idx_categorys_word_id` |
| `hashs` | `USING btree (hash)` | `hashs_hash_key`, `idx_hashs_hash` |
| `punctuation` | `USING btree (punctuation_text)` | `idx_punctuation_text`, `punctuation_punctuation_text_key` |
| `words` | `USING btree (word)` | `idx_words_word`, `words_word_key` |
| `words_hashs` | `USING btree (hash_id, word_id)` | `idx_words_hashs_hash_word`, `words_hashs_pkey` |

What a future migration would do (not done): drop `idx_categorys_word_id`,
`idx_hashs_hash`, `idx_punctuation_text`, `idx_words_word` and
`idx_words_hashs_hash_word`, keeping the constraint-backed index in each pair.
That is a schema change and is listed for the schema owner, not applied here.

This file lives under `docs/`, which is not committed (D-7 asks for a decision
on the generated documentation first). The five shapes it lists are also
recorded in `REGISTERED_REDUNDANT_SHAPES` in the integration test, which is
committed.
