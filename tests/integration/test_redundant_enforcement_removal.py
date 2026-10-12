"""Integration: m0038 removed duplicated enforcement without losing it (DB-1/DB-2).

The schema carried nine *exact* duplicates: two `btree` indexes over the same
columns in the same order, no predicate, no expression. In every pair at least
one member was backed by a `UNIQUE` constraint, so the duplicate could not
answer a query the survivor cannot - it only cost writes. m0038 drops the
redundant member and keeps the enforcing one:

    dropped                                     kept
    idx_analyst_categories_name                 analyst_categories_name_key (UNIQUE)
    idx_categorys_word_id                       categorys_word_id_key (UNIQUE)
    idx_hashs_hash                              hashs_hash_key (UNIQUE)
    idx_keywords_paths_keyword_id               idx_keywords_hashs_keyword_id
    idx_punctuation_text                        punctuation_punctuation_text_key (UNIQUE)
    idx_words_word                              words_word_key (UNIQUE)
    idx_words_paths_word_id                     idx_words_hashs_word_id
    idx_words_hashs_hash_word                   uq_words_hashs_hash_word (UNIQUE)
    uq_hash_contexts_hash_source_side           uq_hash_contexts_identity (UNIQUE)

This test asserts what matters for the invariant, not that the migration ran:
the unique rules still reject duplicates, the surviving index exists, the
duplicate shapes are gone, and the downgrade restores exactly what was dropped.
"""

from __future__ import annotations

import importlib

import psycopg2
import pytest

from _seed import connect, document, side, source

pytestmark = pytest.mark.integration

m0038 = importlib.import_module(
    "database.migrations.m0038_redundant_enforcement_removal")

DROPPED_INDEXES = (
    "idx_analyst_categories_name",
    "idx_categorys_word_id",
    "idx_hashs_hash",
    "idx_keywords_paths_keyword_id",
    "idx_punctuation_text",
    "idx_words_word",
    "idx_words_paths_word_id",
    "idx_words_hashs_hash_word",
)
DROPPED_CONSTRAINT = "uq_hash_contexts_hash_source_side"

KEPT = (
    "analyst_categories_name_key",
    "categorys_word_id_key",
    "hashs_hash_key",
    "idx_keywords_hashs_keyword_id",
    "punctuation_punctuation_text_key",
    "words_word_key",
    "idx_words_hashs_word_id",
    "uq_words_hashs_hash_word",
    "uq_hash_contexts_identity",
)


def _indexes(cur) -> set:
    cur.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'")
    return {row[0] for row in cur.fetchall()}


def _constraints(cur) -> set:
    cur.execute("SELECT conname FROM pg_constraint c JOIN pg_class t"
                " ON t.oid = c.conrelid JOIN pg_namespace n ON n.oid = t.relnamespace"
                " WHERE n.nspname='public'")
    return {row[0] for row in cur.fetchall()}


def _duplicate_shapes(cur) -> list:
    """The shape grouping tools/db/integrity_audit.py reports (name stripped)."""
    cur.execute("""
        SELECT tablename,
               regexp_replace(indexdef,
                   '^(CREATE( UNIQUE)? INDEX )\\S+ ON public\\.\\S+ ', '') AS shape,
               string_agg(indexname, ', ' ORDER BY indexname)
        FROM pg_indexes WHERE schemaname = 'public'
        GROUP BY tablename,
                 regexp_replace(indexdef,
                     '^(CREATE( UNIQUE)? INDEX )\\S+ ON public\\.\\S+ ', '')
        HAVING count(*) > 1
        ORDER BY tablename, shape""")
    return cur.fetchall()


@pytest.fixture()
def conn(pg_db):
    connection = connect(pg_db)
    yield connection
    connection.close()


def test_the_duplicate_objects_are_gone_and_the_survivors_remain(conn):
    with conn.cursor() as cur:
        indexes = _indexes(cur)
        constraints = _constraints(cur)
    for name in DROPPED_INDEXES:
        assert name not in indexes, f"{name} was supposed to be removed by m0038"
    assert DROPPED_CONSTRAINT not in constraints
    for name in KEPT:
        assert name in indexes or name in constraints, f"{name} went missing"


def test_no_duplicate_index_shapes_remain(conn):
    """The condition the audit reports as `redundant_indexes` must be empty."""
    with conn.cursor() as cur:
        assert _duplicate_shapes(cur) == []


def test_the_unique_rules_still_reject_duplicates(conn):
    """Dropping the duplicate must not drop the invariant it duplicated."""
    with conn, conn.cursor() as cur:
        source_id = source(cur)
        side_id = side(cur)
        _, hash_id, _ = document(cur, source_id=source_id, side_id=side_id,
                                 text="duplicate probe")
    conn.commit()  # the corpus must survive the per-probe rollbacks below

    with conn.cursor() as cur:
        # hashs(hash) - the survivor is hashs_hash_key
        cur.execute("SELECT hash FROM hashs WHERE id = %s", (hash_id,))
        digest = cur.fetchone()[0]
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute("INSERT INTO hashs (hash) VALUES (%s)", (digest,))
        conn.rollback()

        # hash_contexts(hash_id, source_id, side_id) - uq_hash_contexts_identity
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute(
                "INSERT INTO hash_contexts (hash_id, source_id, side_id)"
                " VALUES (%s, %s, %s)", (hash_id, source_id, side_id))
        conn.rollback()

        # words(word) and punctuation(punctuation_text)
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute("INSERT INTO words (word) VALUES ('dup-probe')")
            cur.execute("INSERT INTO words (word) VALUES ('dup-probe')")
        conn.rollback()
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute("INSERT INTO punctuation (punctuation_text) VALUES ('~')")
            cur.execute("INSERT INTO punctuation (punctuation_text) VALUES ('~')")
        conn.rollback()

        # analyst_categories(name)
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute("INSERT INTO analyst_categories (name) VALUES ('dup-cat')")
            cur.execute("INSERT INTO analyst_categories (name) VALUES ('dup-cat')")
        conn.rollback()


def test_the_migration_refuses_to_drop_when_the_survivor_is_gone(conn):
    """The guard is the point: a drifted schema must fail, not lose the rule.

    Removing the survivor inside a transaction makes the migration refuse; the
    rollback leaves the session's schema exactly as it was.
    """
    with conn.cursor() as cur:
        cur.execute("DROP INDEX idx_words_hashs_word_id")
        with pytest.raises(RuntimeError, match="idx_words_hashs_word_id"):
            m0038.upgrade(conn)
    conn.rollback()
    with conn.cursor() as cur:
        assert "idx_words_hashs_word_id" in _indexes(cur)


def test_the_downgrade_restores_and_the_upgrade_removes_again(conn):
    """The downgrade recreates exactly what was dropped; the upgrade re-drops.

    Run in one transaction and rolled back so the session's schema is untouched:
    the point is that both directions are valid against the migrated schema.
    """
    with conn.cursor() as cur:
        m0038.downgrade(conn)
        indexes = _indexes(cur)
        constraints = _constraints(cur)
        assert set(DROPPED_INDEXES) <= indexes
        assert DROPPED_CONSTRAINT in constraints
        assert len(_duplicate_shapes(cur)) == 9

        m0038.upgrade(conn)
        indexes = _indexes(cur)
        constraints = _constraints(cur)
        assert not (set(DROPPED_INDEXES) & indexes)
        assert DROPPED_CONSTRAINT not in constraints
        assert _duplicate_shapes(cur) == []
    conn.rollback()
