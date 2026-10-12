"""Unit tests for Relationship Deduplication and Integrity (Hash + Source + Side).

Verifies that:
1. Relationship identity is strictly defined by (Hash + Source + Side).
2. Identical (Hash + Source + Side) combinations reuse the single context record.
3. Legitimate multiple relationships (same Hash, different Source or Side) produce distinct records.
4. Application (dedup_service, pipeline) and database levels prevent duplicates and behave idempotently.
5. Maintenance / migration logic consolidates any duplicate relationship rows cleanly.
"""

import datetime
import psycopg2
import pytest

from database.services.dedup_service import DeduplicationService
from database.migrations.m0013_relationship_deduplication import upgrade as m0013_upgrade
from database.migrations.m0038_redundant_enforcement_removal import upgrade as m0038_upgrade


def restore_canonical_hash_contexts(conn):
    """Leave the shared session database with the schema the migrations define.

    These tests simulate the pre-m0013 world by dropping the uniqueness of
    ``hash_contexts``, then replay m0013's upgrade to prove that its
    consolidation logic is what removes duplicate relationships. m0013 is a
    historical migration and must keep re-creating its own constraint name
    (``uq_hash_contexts_hash_source_side``); the current schema's name is
    ``uq_hash_contexts_identity`` (m0011), and m0038 removed the duplicate.

    Replaying m0013 alone therefore leaves the session database with the
    canonical uniqueness missing and the retired constraint back in place -
    every later test in the same session sees a schema that no migration
    produces (test_bootstrap_migrations' required-index check and
    test_redundant_enforcement_removal's survivor guard fail on it). So restore
    the current state exactly: state the canonical constraint, then apply
    m0038's removal again.
    """
    m0013_upgrade(conn)
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE hash_contexts DROP CONSTRAINT IF EXISTS uq_hash_contexts_identity")
        cur.execute("ALTER TABLE hash_contexts ADD CONSTRAINT uq_hash_contexts_identity"
                    " UNIQUE (hash_id, source_id, side_id)")
    # Refuses (RuntimeError) if a survivor is missing or shape-drifted; every
    # survivor is present here, so this only removes the duplicate again.
    m0038_upgrade(conn)


@pytest.fixture()
def db_conn(pg_db):
    conn = psycopg2.connect(
        host=pg_db["host"],
        port=pg_db["port"],
        user=pg_db["user"],
        password=pg_db["password"],
        dbname=pg_db["database"],
    )
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture()
def dedup_service(db_conn):
    return DeduplicationService(lambda: db_conn)


def create_test_source_and_sides(conn):
    today = datetime.date.today()
    ts = datetime.datetime.now().timestamp()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO sides (name, importance, date_creation) VALUES (%s, %s, %s) RETURNING id",
            (f"side_1_{ts}", 1.0, today)
        )
        side_1 = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO sides (name, importance, date_creation) VALUES (%s, %s, %s) RETURNING id",
            (f"side_2_{ts}", 1.0, today)
        )
        side_2 = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO sources (name, job, importance, country, date_creation) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (f"source_1_{ts}", "job1", 1.0, "US", today)
        )
        source_1 = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO sources (name, job, importance, country, date_creation) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (f"source_2_{ts}", "job2", 1.0, "US", today)
        )
        source_2 = cur.fetchone()[0]

        conn.commit()
    return source_1, source_2, side_1, side_2


class TestRelationshipIdentity:

    def test_identical_hash_source_side_reuses_record(self, db_conn, dedup_service, tmp_path):
        source_1, source_2, side_1, side_2 = create_test_source_and_sides(db_conn)
        content_hash = "a" * 64

        path_row = {
            "file_name": "file1.txt",
            "file_path": str(tmp_path / "file1.txt"),
            "file_size": 123,
            "file_type": "txt",
            "file_date": datetime.date.today(),
            "date_creation": datetime.date.today(),
        }

        # First registration
        res1 = dedup_service.register_content(content_hash, source_1, side_1, path_row)
        c_id1 = res1["context_id"]
        assert c_id1 is not None and c_id1 > 0

        # Repeated registration with identical Hash + Source + Side
        path_row2 = dict(path_row, file_name="file2.txt", file_path=str(tmp_path / "file2.txt"))
        res2 = dedup_service.register_content(content_hash, source_1, side_1, path_row2)
        assert res2["context_id"] == c_id1, "Identical (Hash + Source + Side) MUST return the same context row ID"

        # Check total rows in hash_contexts table for this combination
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM hash_contexts c JOIN hashs h ON h.id = c.hash_id WHERE h.hash = %s AND c.source_id = %s AND c.side_id = %s",
                (content_hash, source_1, side_1)
            )
            count = cur.fetchone()[0]
        assert count == 1, "There MUST be exactly 1 database record for identical (Hash + Source + Side)"

    def test_different_side_creates_distinct_relationship(self, db_conn, dedup_service, tmp_path):
        source_1, source_2, side_1, side_2 = create_test_source_and_sides(db_conn)
        content_hash = "b" * 64

        path_row1 = {
            "file_name": "b1.txt",
            "file_path": str(tmp_path / "b1.txt"),
            "file_size": 123,
            "file_type": "txt",
            "file_date": datetime.date.today(),
            "date_creation": datetime.date.today(),
        }
        path_row2 = dict(path_row1, file_name="b2.txt", file_path=str(tmp_path / "b2.txt"))

        # Relationship 1: Hash-B + Source-1 + Side-1
        res1 = dedup_service.register_content(content_hash, source_1, side_1, path_row1)

        # Relationship 2: Hash-B + Source-1 + Side-2 (different side)
        res2 = dedup_service.register_content(content_hash, source_1, side_2, path_row2)

        assert res2["context_id"] != res1["context_id"], "Different Side MUST create a distinct relationship record"

        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM hash_contexts c JOIN hashs h ON h.id = c.hash_id WHERE h.hash = %s", (content_hash,))
            total_records = cur.fetchone()[0]
        assert total_records == 2, "Hash participating in 2 different sides must produce 2 distinct relationship rows"

    def test_different_source_creates_distinct_relationship(self, db_conn, dedup_service, tmp_path):
        source_1, source_2, side_1, side_2 = create_test_source_and_sides(db_conn)
        content_hash = "c" * 64

        path_row1 = {
            "file_name": "c1.txt",
            "file_path": str(tmp_path / "c1.txt"),
            "file_size": 123,
            "file_type": "txt",
            "file_date": datetime.date.today(),
            "date_creation": datetime.date.today(),
        }
        path_row2 = dict(path_row1, file_name="c2.txt", file_path=str(tmp_path / "c2.txt"))

        # Relationship 1: Hash-C + Source-1 + Side-1
        res1 = dedup_service.register_content(content_hash, source_1, side_1, path_row1)

        # Relationship 2: Hash-C + Source-2 + Side-1 (different source)
        res2 = dedup_service.register_content(content_hash, source_2, side_1, path_row2)

        assert res2["context_id"] != res1["context_id"], "Different Source MUST create a distinct relationship record"

        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM hash_contexts c JOIN hashs h ON h.id = c.hash_id WHERE h.hash = %s", (content_hash,))
            total_records = cur.fetchone()[0]
        assert total_records == 2, "Hash participating in 2 different sources must produce 2 distinct relationship rows"


class TestDeduplicationService:

    def test_check_duplicate_distinguishes_relationships(self, db_conn, dedup_service, tmp_path):
        source_1, source_2, side_1, side_2 = create_test_source_and_sides(db_conn)
        content_hash = "d" * 64

        path_row = {
            "file_name": "file1.txt",
            "file_path": str(tmp_path / "file1.txt"),
            "file_size": 123,
            "file_type": "txt",
            "file_date": datetime.date.today(),
            "date_creation": datetime.date.today(),
        }

        # Register under Source-1 + Side-1
        reg1 = dedup_service.register_content(content_hash, source_1, side_1, path_row)
        path_id1 = reg1["path_id"]

        # Duplicate check for exact same relationship -> live path found!
        existing_path = dedup_service.find_live_path(content_hash, source_1, side_1)
        assert existing_path == path_id1

        # Duplicate check for same Hash + Source-1, BUT Side-2 -> None!
        path_side = dedup_service.find_live_path(content_hash, source_1, side_2)
        assert path_side is None

        # Duplicate check for same Hash + Side-1, BUT Source-2 -> None!
        path_source = dedup_service.find_live_path(content_hash, source_2, side_1)
        assert path_source is None

    def test_deduplicate_hash_relationships_service_cleanup(self, db_conn, dedup_service):
        source_1, source_2, side_1, side_2 = create_test_source_and_sides(db_conn)
        content_hash = "e" * 64

        try:
            with db_conn.cursor() as cur:
                cur.execute("ALTER TABLE hash_contexts DROP CONSTRAINT IF EXISTS uq_hash_contexts_identity")
                cur.execute("ALTER TABLE hash_contexts DROP CONSTRAINT IF EXISTS uq_hash_contexts_hash_source_side")

                cur.execute("INSERT INTO hashs (hash) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id", (content_hash,))
                row = cur.fetchone()
                h_id = row[0] if row else None
                if not h_id:
                    cur.execute("SELECT id FROM hashs WHERE hash = %s", (content_hash,))
                    h_id = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO hash_contexts (hash_id, source_id, side_id) VALUES (%s, %s, %s) RETURNING id",
                    (h_id, source_1, side_1)
                )
                c_id1 = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO hash_contexts (hash_id, source_id, side_id) VALUES (%s, %s, %s) RETURNING id",
                    (h_id, source_1, side_1)
                )
                c_id2 = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO paths (file_name, file_path, file_size, file_type, file_status, file_date, date_creation, context_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    ("test_dup.txt", "/tmp/dup.txt", 100, "txt", "Unread", datetime.date.today(), datetime.date.today(), c_id2)
                )
                p_id = cur.fetchone()[0]
                db_conn.commit()

            # Run deduplicate_hash_relationships
            removed = dedup_service.deduplicate_hash_relationships(dry_run=False)
            assert removed == 1

            # Verify that only 1 relationship row remains
            with db_conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM hash_contexts WHERE hash_id = %s AND source_id = %s AND side_id = %s", (h_id, source_1, side_1))
                assert cur.fetchone()[0] == 1

                cur.execute("SELECT context_id FROM paths WHERE id = %s", (p_id,))
                assert cur.fetchone()[0] == c_id1
        finally:
            db_conn.rollback()
            restore_canonical_hash_contexts(db_conn)
            db_conn.commit()


class TestMigration0013:

    def test_m0013_upgrade_cleans_up_duplicates(self, db_conn):
        source_1, source_2, side_1, side_2 = create_test_source_and_sides(db_conn)
        content_hash = "f" * 64

        try:
            with db_conn.cursor() as cur:
                cur.execute("ALTER TABLE hash_contexts DROP CONSTRAINT IF EXISTS uq_hash_contexts_identity")
                cur.execute("ALTER TABLE hash_contexts DROP CONSTRAINT IF EXISTS uq_hash_contexts_hash_source_side")

                cur.execute("INSERT INTO hashs (hash) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id", (content_hash,))
                row = cur.fetchone()
                h_id = row[0] if row else None
                if not h_id:
                    cur.execute("SELECT id FROM hashs WHERE hash = %s", (content_hash,))
                    h_id = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO hash_contexts (hash_id, source_id, side_id) VALUES (%s, %s, %s) RETURNING id",
                    (h_id, source_1, side_1)
                )
                c_id1 = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO hash_contexts (hash_id, source_id, side_id) VALUES (%s, %s, %s) RETURNING id",
                    (h_id, source_1, side_1)
                )
                c_id2 = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO paths (file_name, file_path, file_size, file_type, file_status, file_date, date_creation, context_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    ("m13.txt", "/tmp/m13.txt", 50, "txt", "Unread", datetime.date.today(), datetime.date.today(), c_id2)
                )
                p_id = cur.fetchone()[0]
                db_conn.commit()

            # Execute migration upgrade
            m0013_upgrade(db_conn)

            # Verify clean state
            with db_conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM hash_contexts WHERE hash_id = %s AND source_id = %s AND side_id = %s", (h_id, source_1, side_1))
                assert cur.fetchone()[0] == 1

                cur.execute("SELECT context_id FROM paths WHERE id = %s", (p_id,))
                assert cur.fetchone()[0] == c_id1
        finally:
            db_conn.rollback()
            restore_canonical_hash_contexts(db_conn)
            db_conn.commit()

def test_the_cleanup_restores_the_canonical_constraint(db_conn):
    """Pin the coupling that made two later integration tests fail.

    Dropping the uniqueness, replaying m0013 and *not* replaying m0038's
    removal leaves `uq_hash_contexts_identity` missing and the retired
    `uq_hash_contexts_hash_source_side` back in place - a schema no migration
    produces, which is what `test_bootstrap_migrations` and
    `test_redundant_enforcement_removal` were failing on when they ran after
    this module in the same session. Both names are checked: a missing
    canonical constraint and a resurrected retired one are different mistakes
    with the same root cause.
    """
    with db_conn.cursor() as cur:
        cur.execute("ALTER TABLE hash_contexts DROP CONSTRAINT IF EXISTS uq_hash_contexts_identity")
        cur.execute("ALTER TABLE hash_contexts DROP CONSTRAINT IF EXISTS uq_hash_contexts_hash_source_side")
        assert _hash_contexts_unique_names(cur) == set()
    restore_canonical_hash_contexts(db_conn)
    db_conn.commit()
    with db_conn.cursor() as cur:
        assert _hash_contexts_unique_names(cur) == {"uq_hash_contexts_identity"}


def _hash_contexts_unique_names(cur):
    cur.execute(
        "SELECT c.conname FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid"
        " WHERE t.relname = 'hash_contexts' AND c.contype = 'u'")
    return {row[0] for row in cur.fetchall()}
