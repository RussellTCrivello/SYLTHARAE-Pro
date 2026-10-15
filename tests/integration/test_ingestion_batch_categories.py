"""Integration: the ingestion batch report's category section reads live tables.

``_query_categories`` used to read ``words_paths wp`` with ``wp.path_id`` - a
table renamed to ``words_hashs`` (keyed by hash, not path) in m0011. The query
raised on every report, ``_safe_query`` logged "Batch report query failed:
categories" and the report rendered an empty "Categories assigned" section for
every batch. A rename that was not propagated is exactly the kind of drift that
only a query against the real schema catches, so this test seeds the real
tables and reads the report the way a batch report does.

Seeded shape (all plain SQL through the same tables ingestion writes):

    paths -> hash_contexts -> words_hashs -> words_categorys -> categorys -> words
    (a member word belongs to a category whose name is its own word)
"""

from __future__ import annotations

import psycopg2.extras
import pytest

from _seed import connect, document, side, source, word_counts
from services.reporting.ingestion_batch import _query_categories, document_from_parts

pytestmark = pytest.mark.integration

MEMBER_WORD = "quarterly-report-marker"


def _dict_cursor(conn):
    """The cursor factory the report itself uses (``_load_batch_rows``)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


@pytest.fixture()
def categorised_corpus(pg_db):
    """One document whose member word is assigned to one named category."""
    conn = connect(pg_db)
    with conn, conn.cursor() as cur:
        source_id = source(cur)
        side_id = side(cur)
        path_id, hash_id, _context_id = document(
            cur, source_id=source_id, side_id=side_id,
            text=f"{MEMBER_WORD} appears here.", file_name="batch-report.txt")
        word_counts(cur, hash_id, {MEMBER_WORD: 4})
        cur.execute("INSERT INTO words (word) VALUES (%s)"
                    " ON CONFLICT (word) DO UPDATE SET word = EXCLUDED.word RETURNING id",
                    ("Batch Topic",))
        category_name_word = cur.fetchone()[0]
        cur.execute("INSERT INTO categorys (word_id) VALUES (%s)"
                    " ON CONFLICT (word_id) DO UPDATE SET word_id = EXCLUDED.word_id RETURNING id",
                    (category_name_word,))
        category_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM words WHERE word = %s", (MEMBER_WORD,))
        member_word_id = cur.fetchone()[0]
        cur.execute("INSERT INTO words_categorys (word_id, category_id) VALUES (%s, %s)"
                    " ON CONFLICT (word_id, category_id) DO NOTHING",
                    (member_word_id, category_id))
    yield conn, path_id
    conn.close()


def test_categories_query_returns_the_assigned_category(categorised_corpus):
    conn, path_id = categorised_corpus
    with _dict_cursor(conn) as cur:
        rows = _query_categories(cur, [path_id])
    assert rows, ("the category query returned nothing; it is reading a table name"
                  " the schema no longer has")
    row = next(r for r in rows if r["name"] == "Batch Topic")
    assert row["file_count"] == 1
    assert row["occurrence_count"] == 4


def test_the_report_document_carries_the_category(categorised_corpus):
    """The whole path the batch report takes, not just the query."""
    conn, path_id = categorised_corpus
    document_json = document_from_parts(
        identity={"source": "s", "side": "x", "job_id": "j"},
        counts={"files_total": 1, "files_processed": 1, "files_failed": 0,
                "files_skipped": 0, "file_types": 1},
        path_ids=[path_id],
        conn=conn,
    )
    names = [row["name"] for row in document_json["categories"]]
    assert "Batch Topic" in names, document_json["categories"]


def test_places_come_through_the_view_not_the_legacy_table(categorised_corpus):
    """One read path for place mentions: the ``path_geo_mentions`` view.

    The view unions signal-derived places with the preserved m0015 rows (for
    content no places run has covered). Reading ``path_geo_mentions_m0015``
    directly - which the report used to do - is a second access path that also
    surfaces legacy rows the view deliberately hides once a places run exists.
    Seeded through the legacy table, so this fails if the query stops using the
    view.
    """
    from services.reporting.ingestion_batch import _query_places

    conn, path_id = categorised_corpus
    with conn, conn.cursor() as cur:
        # The hash is the content identity: paths reach it through their context.
        cur.execute("SELECT hc.hash_id FROM paths p JOIN hash_contexts hc"
                    " ON hc.id = p.context_id WHERE p.id = %s", (path_id,))
        hash_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO path_geo_mentions_m0015 (hash_id, place_name, country,"
            " latitude, longitude, mention_count) VALUES (%s, 'Legacy Place', 'NL',"
            " 52.37, 4.89, 3)", (hash_id,))
    with _dict_cursor(conn) as cur:
        rows = _query_places(cur, [path_id])
    match = next((r for r in rows if r["place"] == "Legacy Place"), None)
    assert match is not None, rows
    assert match["file_count"] == 1
    assert match["mentions"] == 3
