"""Integration: the workbook sync must never touch a curated translation.

``term_names`` holding the Arabic, Hebrew, Persian and Croatian names of a term
is the one place in the schema where a human's work is not derivable from
anything else - and it hangs off ``words.id`` with ``ON DELETE CASCADE``. The
sync creates, links, unlinks and (with the flag) prunes ``words`` rows, so the
question this module answers is whether that path can eat a curated name.

Read-only for the reader of the report: the tests only ever read ``term_names``
to assert what survived.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import openpyxl
import psycopg2
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.importing.validators import workbook_rules as rules  # noqa: E402
from services.importing import taxonomy_sync as sync  # noqa: E402

pytestmark = pytest.mark.integration


def token() -> str:
    return uuid.uuid4().hex[:8]


def build(path: Path, sheets: dict) -> Path:
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, content in sheets.items():
        sheet = book.create_sheet(name)
        sheet.cell(row=1, column=1, value=rules.TERM_HEADER)
        sheet.cell(row=1, column=2, value=rules.KEYWORD_HEADER)
        for row, term in enumerate(content.get("terms", []), start=2):
            sheet.cell(row=row, column=1, value=term)
    book.save(path)
    return path


@pytest.fixture(scope="module")
def names_db(pg_db):
    from database.bootstrap import bootstrap_database

    name = f"{pg_db['database']}_term_names_sync"
    admin = psycopg2.connect(host=pg_db["host"], port=pg_db["port"], user=pg_db["user"],
                             password=pg_db["password"], dbname="postgres")
    admin.autocommit = True
    try:
        with admin.cursor() as cur:
            cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                        " WHERE datname = %s AND pid <> pg_backend_pid()", (name,))
            cur.execute(f'DROP DATABASE IF EXISTS "{name}"')
            cur.execute(f'CREATE DATABASE "{name}"')
    finally:
        admin.close()
    cfg = {key: pg_db[key] for key in ("host", "port", "user", "password")}
    cfg["database"] = name
    bootstrap_database(cfg)
    return cfg


@pytest.fixture()
def conn(names_db):
    connection = psycopg2.connect(host=names_db["host"], port=names_db["port"],
                                  user=names_db["user"], password=names_db["password"],
                                  dbname=names_db["database"])
    with connection.cursor() as cur:
        cur.execute("TRUNCATE words, categorys, keywords, words_categorys"
                    " RESTART IDENTITY CASCADE")
    connection.commit()
    yield connection
    connection.close()


def word_id(conn, text):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM words WHERE word = %s", (text,))
        row = cur.fetchone()
        return row[0] if row else None


def add_name(conn, text, language, name, name_type="preferred"):
    """Curate one translation the way the API does, keyed on the word row."""
    from core.i18n.term_key import term_key

    wid = word_id(conn, text)
    assert wid is not None, f"{text!r} is not stored"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO term_names (word_id, name, match_key, language, name_type,"
            " script, source) VALUES (%s, %s, %s, %s, %s, %s, 'curated')",
            (wid, name, term_key(name), language, name_type,
             "Arab" if language in ("ar", "fa") else
             "Hebr" if language == "he" else "Latn"))
    conn.commit()
    return wid


def names_for(conn, text):
    wid = word_id(conn, text)
    if wid is None:
        return None                      # the word itself is gone
    with conn.cursor() as cur:
        cur.execute("SELECT language, name FROM term_names WHERE word_id = %s"
                    " ORDER BY language", (wid,))
        return cur.fetchall()


def test_an_apply_that_relinks_a_term_keeps_its_curated_names(conn, tmp_path):
    suffix = token()
    category, term = f"Zeta Curated {suffix}", f"Alpha{suffix}"
    sync.sync_workbook(conn, str(build(tmp_path / "one.xlsx",
                                       {category: {"terms": [term]}})), apply=True)
    add_name(conn, term, "ar", "ألفا")
    add_name(conn, category, "ar", "زد")

    # The workbook still lists the category but drops the term, then adds it back.
    sync.sync_workbook(conn, str(build(tmp_path / "two.xlsx",
                                       {category: {"terms": []}})), apply=True)
    assert names_for(conn, term) == [("ar", "ألفا")], (
        "unlinking a term from a category deleted its curated names")

    sync.sync_workbook(conn, str(build(tmp_path / "three.xlsx",
                                       {category: {"terms": [term]}})), apply=True)
    assert names_for(conn, term) == [("ar", "ألفا")]
    assert names_for(conn, category) == [("ar", "زد")]


def test_pruning_an_orphan_word_keeps_its_curated_names(conn, tmp_path, monkeypatch):
    """The pruning path is the dangerous one: ``words`` is the parent row.

    ``term_names`` is ``ON DELETE CASCADE``, so deleting a word deletes every
    name curated for it. A word a curator has named is therefore not an orphan
    to the sync, whatever the vocabulary says.
    """
    monkeypatch.setenv("SYLTHARAE_TAXONOMY_SHRINK_MAX", "1")
    suffix = token()
    category, kept, curatable = (f"Zeta Prune {suffix}", f"Alpha{suffix}",
                                 f"Beta{suffix}")
    sync.sync_workbook(conn, str(build(tmp_path / "one.xlsx",
                                       {category: {"terms": [kept, curatable]}})),
                       apply=True)
    add_name(conn, curatable, "he", "בתא")

    # The workbook keeps the category and one term; the other word becomes an
    # orphan. A plan is computed before it is written, so the word is only an
    # orphan on the *next* run - which is the run that could delete it, and the
    # reason this test applies the same workbook twice.
    narrowed = build(tmp_path / "two.xlsx", {category: {"terms": [kept]}})
    sync.sync_workbook(conn, str(narrowed), apply=True)
    outcome = sync.sync_workbook(conn, str(narrowed), apply=True, prune_words=True)

    assert word_id(conn, curatable) is not None, (
        "prune_words deleted a word a curator had named, so its names cascaded away")
    assert names_for(conn, curatable) == [("he", "בתא")]
    assert outcome["written"].get("words_kept_for_names", 0) >= 1, (
        "the run did not report that it kept a word for its names")


def test_pruning_deletes_a_word_that_nothing_names_and_nothing_uses(conn, tmp_path,
                                                                   monkeypatch):
    """The guard must not turn pruning off: an unnamed orphan still goes."""
    monkeypatch.setenv("SYLTHARAE_TAXONOMY_SHRINK_MAX", "1")
    suffix = token()
    category = f"Zeta Bare {suffix}"
    doomed = f"Gamma{suffix}"
    sync.sync_workbook(conn, str(build(tmp_path / "one.xlsx",
                                       {category: {"terms": [doomed]}})), apply=True)
    # A worksheet with no terms is a rule violation, so the term is replaced
    # rather than removed: ``doomed`` is unlinked, and becomes an orphan on the
    # run after that.
    narrowed = build(tmp_path / "two.xlsx", {category: {"terms": [f"Zeta{suffix}"]}})
    sync.sync_workbook(conn, str(narrowed), apply=True)
    outcome = sync.sync_workbook(conn, str(narrowed), apply=True, prune_words=True)
    assert outcome["ok"] is True, outcome.get("errors")
    assert word_id(conn, doomed) is None
    assert outcome["written"]["words_pruned"] >= 1


def test_an_apply_never_writes_to_term_names(conn, tmp_path):
    """The sync has no translation of its own, and must not invent one."""
    suffix = token()
    category, term = f"Zeta Quiet {suffix}", f"Delta{suffix}"
    sync.sync_workbook(conn, str(build(tmp_path / "one.xlsx",
                                       {category: {"terms": [term]}})), apply=True)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM term_names")
        before = cur.fetchone()[0]
    sync.sync_workbook(conn, str(build(tmp_path / "two.xlsx",
                                       {category: {"terms": [term, f"Epsilon{suffix}"]}})),
                       apply=True)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM term_names")
        assert cur.fetchone()[0] == before
