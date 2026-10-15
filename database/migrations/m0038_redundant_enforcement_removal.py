"""Remove redundant duplicate enforcement mechanisms (DB-1, DB-2).

Nine *exact* duplicates: in every pair both objects are `btree` indexes over the
same column list in the same order, with no predicate, no expression and the
default operator class - so the second one cannot answer a single query the
first cannot, and it is maintained on every write. They are accumulated over
time: m0001 created plain indexes next to `UNIQUE` constraints, m0002 recreated
a `words_hashs` index under its pre-m0011 name (`idx_words_paths_word_id`),
m0009 added `idx_analyst_categories_name` beside the inline `UNIQUE`, m0011 and
m0013 each created the same `hash_contexts` uniqueness under two names, and
m0035 re-created an index the `uq_words_hashs_hash_word` constraint already
provided.

The invariant is preserved in every case: the surviving object enforces the
same uniqueness or provides the same access path.

    dropped                                    kept (identical shape)
    ---------------------------------------------------------------------
    idx_analyst_categories_name                analyst_categories_name_key (UNIQUE)
    idx_categorys_word_id                      categorys_word_id_key (UNIQUE)
    idx_hashs_hash                             hashs_hash_key (UNIQUE)
    idx_keywords_paths_keyword_id              idx_keywords_hashs_keyword_id
    idx_punctuation_text                       punctuation_punctuation_text_key (UNIQUE)
    idx_words_word                             words_word_key (UNIQUE)
    idx_words_paths_word_id                    idx_words_hashs_word_id
    idx_words_hashs_hash_word                  uq_words_hashs_hash_word (UNIQUE)
    uq_hash_contexts_hash_source_side (DB-1)   uq_hash_contexts_identity (UNIQUE)

Why `uq_hash_contexts_hash_source_side` is the one dropped rather than the
`UNIQUE` it is identical to: `uq_hash_contexts_identity` is the name the content
identity migration itself uses, it is the name `tests/integration/
test_bootstrap_migrations.py` asserts, and no code anywhere names a constraint
in `ON CONFLICT ON CONSTRAINT` (searched), so the surviving name is the one the
project treats as canonical. `paths.context_id` references `hash_contexts(id)`
(its primary key), not this constraint, so nothing depends on the dropped name.

`idx_words_hashs_word_hash` (m0036, `(word_id, hash_id)`) is deliberately *not*
touched: its column order is the reverse of the unique constraint, so it serves
word-scoped lookups the constraint's index cannot.

Before dropping anything this migration proves the survivors exist and still
have the same shape; a schema that has drifted fails loudly here instead of
quietly losing an access path.

Nothing here touches data: no row is read, written or deleted, and every
dropped object is recreated by ``downgrade`` with its original definition.
"""

version = "0038"
name = "redundant_enforcement_removal"

#: (kind, dropped, survivor, table) - kind is "index" or "constraint".
_REDUNDANT = (
    ("index", "idx_analyst_categories_name", "analyst_categories_name_key", "analyst_categories"),
    ("index", "idx_categorys_word_id", "categorys_word_id_key", "categorys"),
    ("index", "idx_hashs_hash", "hashs_hash_key", "hashs"),
    ("index", "idx_keywords_paths_keyword_id", "idx_keywords_hashs_keyword_id", "keywords_hashs"),
    ("index", "idx_punctuation_text", "punctuation_punctuation_text_key", "punctuation"),
    ("index", "idx_words_word", "words_word_key", "words"),
    ("index", "idx_words_paths_word_id", "idx_words_hashs_word_id", "words_hashs"),
    ("index", "idx_words_hashs_hash_word", "uq_words_hashs_hash_word", "words_hashs"),
    ("constraint", "uq_hash_contexts_hash_source_side", "uq_hash_contexts_identity", "hash_contexts"),
)

#: The definitions to restore on downgrade, exactly as the originating
#: migrations created them (m0001, m0002, m0009, m0011, m0013, m0035).
_RESTORE = {
    "idx_analyst_categories_name":
        "CREATE INDEX IF NOT EXISTS idx_analyst_categories_name"
        " ON analyst_categories (name)",
    "idx_categorys_word_id":
        "CREATE INDEX IF NOT EXISTS idx_categorys_word_id ON categorys (word_id)",
    "idx_hashs_hash":
        "CREATE INDEX IF NOT EXISTS idx_hashs_hash ON hashs (hash)",
    "idx_keywords_paths_keyword_id":
        "CREATE INDEX IF NOT EXISTS idx_keywords_paths_keyword_id"
        " ON keywords_hashs (keyword_id)",
    "idx_punctuation_text":
        "CREATE INDEX IF NOT EXISTS idx_punctuation_text"
        " ON punctuation (punctuation_text)",
    "idx_words_word":
        "CREATE INDEX IF NOT EXISTS idx_words_word ON words (word)",
    "idx_words_paths_word_id":
        "CREATE INDEX IF NOT EXISTS idx_words_paths_word_id ON words_hashs (word_id)",
    "idx_words_hashs_hash_word":
        "CREATE INDEX IF NOT EXISTS idx_words_hashs_hash_word ON words_hashs (hash_id, word_id)",
    "uq_hash_contexts_hash_source_side":
        "ALTER TABLE hash_contexts ADD CONSTRAINT uq_hash_contexts_hash_source_side"
        " UNIQUE (hash_id, source_id, side_id)",
}

#: The shape of each survivor, normalized the way `tools/db/integrity_audit.py`
#: compares indexes (index name, table qualifier and UNIQUE token removed).
_EXPECTED_SHAPES = {
    "analyst_categories_name_key": "analyst_categories USING btree (name)",
    "categorys_word_id_key": "categorys USING btree (word_id)",
    "hashs_hash_key": "hashs USING btree (hash)",
    "idx_keywords_hashs_keyword_id": "keywords_hashs USING btree (keyword_id)",
    "punctuation_punctuation_text_key":
        "punctuation USING btree (punctuation_text)",
    "words_word_key": "words USING btree (word)",
    "idx_words_hashs_word_id": "words_hashs USING btree (word_id)",
    "uq_words_hashs_hash_word": "words_hashs USING btree (hash_id, word_id)",
    "uq_hash_contexts_identity": "hash_contexts USING btree (hash_id, source_id, side_id)",
}


def _objects(cur) -> dict:
    """Every constraint and index in `public`, keyed by name -> shape."""
    cur.execute("""
        SELECT conname,
               relname || ' USING btree (' ||
               (SELECT string_agg(a.attname, ', ' ORDER BY k.ord)
                  FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord)
                  JOIN pg_attribute a ON a.attrelid = con.conrelid
                                     AND a.attnum = k.attnum) || ')'
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = rel.relnamespace
        WHERE n.nspname = 'public'
          AND con.contype IN ('p', 'u')
    """)
    objects = {row[0]: row[1] for row in cur.fetchall()}
    cur.execute("""
        SELECT indexname, tablename || ' ' || regexp_replace(indexdef,
                   '^(CREATE( UNIQUE)? INDEX )\\S+ ON public\\.\\S+ ', '')
        FROM pg_indexes WHERE schemaname = 'public'
    """)
    for name, shape in cur.fetchall():
        objects.setdefault(name, shape)
    return objects


def _drop(cur, kind: str, name: str) -> None:
    if kind == "index":
        cur.execute(f'DROP INDEX IF EXISTS "{name}"')
    else:
        cur.execute(f'ALTER TABLE hash_contexts DROP CONSTRAINT IF EXISTS "{name}"')


def upgrade(conn) -> None:
    with conn.cursor() as cur:
        present = _objects(cur)

        # Refuse to drop anything whose survivor is missing or no longer the
        # same shape: on a drifted schema the drop would remove the only
        # enforcement of the invariant.
        for _kind, dropped, survivor, table in _REDUNDANT:
            actual = present.get(survivor)
            expected = _EXPECTED_SHAPES[survivor]
            if actual is None:
                raise RuntimeError(
                    f"{survivor} is missing, so dropping {dropped} would remove"
                    f" the only enforcement on {table}; refusing")
            if actual != expected:
                raise RuntimeError(
                    f"{survivor} has shape {actual!r}, expected {expected!r};"
                    f" refusing to drop {dropped} until that is reviewed")

        for kind, dropped, _survivor, _table in _REDUNDANT:
            _drop(cur, kind, dropped)


def downgrade(conn) -> None:
    with conn.cursor() as cur:
        for statement in _RESTORE.values():
            cur.execute(statement)
