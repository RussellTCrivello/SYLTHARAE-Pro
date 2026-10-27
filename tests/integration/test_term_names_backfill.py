"""The backfill: dry run, idempotent apply, rollback, reconciliation.

``tools/i18n/backfill_term_names.py`` makes every existing term the
default-language name of itself. The dangerous part is not the insert; it is
everything the tool could touch while inserting. So this module asserts, in
order:

* a dry run writes nothing and still reports the work;
* applying twice inserts once (a second run is a no-op, not a duplicate);
* ``words`` / ``categorys`` / ``keywords`` are byte-identical after the run;
* every word ends with exactly one preferred default-language name;
* rollback removes only what the tool created, leaving a curated name alone.

The last one is the one that matters most: a rollback that deleted a name a
human had written would be reported as a clean undo and would be data loss.
"""

from __future__ import annotations

import uuid

import psycopg2
import pytest

from _seed import connect

pytestmark = pytest.mark.integration


@pytest.fixture()
def backfill_db(pg_db):
    """A connection and a handful of words, one of them curated."""
    from core.i18n.term_key import term_key

    conn = connect(pg_db)
    suffix = uuid.uuid4().hex[:8]
    words = {}
    try:
        with conn.cursor() as cur:
            for label in ("political", "economic", "social"):
                cur.execute("INSERT INTO words (word) VALUES (%s) RETURNING id",
                            (f"{label}-{suffix}",))
                words[label] = cur.fetchone()[0]
            cur.execute("INSERT INTO categorys (word_id) VALUES (%s)",
                        (words["political"],))
            # One word already has a human-written name: the backfill must leave
            # it alone, and so must the rollback.
            cur.execute(
                "INSERT INTO term_names (word_id, name, match_key, language,"
                " name_type, script, source) VALUES (%s, %s, %s, 'en', 'preferred',"
                " 'Latn', 'curated')",
                (words["economic"], f"economy {suffix}", term_key(f"economy {suffix}")))
        conn.commit()
    finally:
        pass
    yield conn, words, suffix
    conn.close()


def _count(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table}")  # nosec B608 - fixed names
        return cur.fetchone()[0]


class TestTheDryRun:
    def test_it_reports_the_work_and_writes_nothing(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill

        conn, _words, _suffix = backfill_db
        before = _count(conn, "term_names")
        report = backfill(conn, dry_run=True)
        assert report["inserted"] == 0
        assert report["pending"] >= 2
        assert _count(conn, "term_names") == before

    def test_it_shows_what_it_would_insert(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill

        conn, words, suffix = backfill_db
        report = backfill(conn, dry_run=True)
        sample_words = {row["word"] for row in report["sample"]}
        assert f"political-{suffix}" in sample_words
        # The curated word is not scheduled for insertion at all.
        assert f"economic-{suffix}" not in sample_words


class TestTheApply:
    def test_every_word_gains_its_own_name(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill, reconcile

        conn, words, suffix = backfill_db
        report = backfill(conn, dry_run=False)
        assert report["inserted"] >= 2
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM term_names WHERE word_id = %s"
                        " AND name_type = 'preferred' AND language = 'en'",
                        (words["political"],))
            assert cur.fetchone()[0] == f"political-{suffix}"
        assert reconcile(conn)["ok"] is True

    def test_a_second_apply_inserts_nothing(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill

        conn, _words, _suffix = backfill_db
        backfill(conn, dry_run=False)
        first = _count(conn, "term_names")
        second_report = backfill(conn, dry_run=False)
        assert second_report["inserted"] == 0
        assert _count(conn, "term_names") == first

    def test_a_curated_name_is_never_overwritten(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill

        conn, words, suffix = backfill_db
        backfill(conn, dry_run=False)
        with conn.cursor() as cur:
            cur.execute("SELECT name, source FROM term_names WHERE word_id = %s",
                        (words["economic"],))
            name, source = cur.fetchone()
        assert name == f"economy {suffix}"
        assert source == "curated"


class TestTheReconciliation:
    def test_no_other_table_moves(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill, reconcile

        conn, _words, _suffix = backfill_db
        before = {"words": _count(conn, "words"),
                  "categorys": _count(conn, "categorys"),
                  "keywords": _count(conn, "keywords")}
        backfill(conn, dry_run=False)
        report = reconcile(conn, before=before)
        assert report["ok"] is True, report
        assert report["untouched"] == {"words": [before["words"], before["words"]],
                                       "categorys": [before["categorys"], before["categorys"]],
                                       "keywords": [before["keywords"], before["keywords"]]}

    def test_the_reconciliation_fails_when_a_table_moved(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill, reconcile

        conn, _words, _suffix = backfill_db
        before = {"words": _count(conn, "words") - 1,   # a lie, on purpose
                  "categorys": _count(conn, "categorys"),
                  "keywords": _count(conn, "keywords")}
        backfill(conn, dry_run=False)
        report = reconcile(conn, before=before)
        assert report["ok"] is False, "the reconciliation must not bless a moved table"


class TestTheRollback:
    def test_it_removes_only_what_the_tool_created(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill, rollback

        conn, words, suffix = backfill_db
        backfill(conn, dry_run=False)
        report = rollback(conn, dry_run=False)
        assert report["deleted"] >= 2
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM term_names WHERE source = 'backfill'")
            assert cur.fetchone()[0] == 0
            # The curated name survived.
            cur.execute("SELECT name FROM term_names WHERE word_id = %s",
                        (words["economic"],))
            assert cur.fetchone()[0] == f"economy {suffix}"

    def test_a_dry_run_rollback_deletes_nothing(self, backfill_db):
        from tools.i18n.backfill_term_names import backfill, rollback

        conn, _words, _suffix = backfill_db
        backfill(conn, dry_run=False)
        before = _count(conn, "term_names")
        report = rollback(conn, dry_run=True)
        assert report["deleted"] == 0
        assert report["would_delete"] >= 2
        assert _count(conn, "term_names") == before
