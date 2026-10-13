"""Repeats inside one (source, side) are removed; nothing else is.

A repetition is the same content recorded more than once in one source and one
side. The earliest occurrence stays, the others go. The same content in another
side or another source is a different context and must survive, and the shared
content and its contexts must survive the cleanup.
"""

from __future__ import annotations

from tests.integration._seed import connect, document, side, source


def _ids_for_hash(cur, hash_id):
    cur.execute(
        "SELECT p.id FROM paths p JOIN hash_contexts c ON c.id = p.context_id"
        " WHERE c.hash_id = %s ORDER BY p.id", (hash_id,))
    return [row[0] for row in cur.fetchall()]


def test_same_source_and_side_repeats_are_removed_keeping_the_earliest(pg_db):
    from database.services.dedup_service import DeduplicationService

    conn = connect(pg_db)
    with conn.cursor() as cur:
        a, b = source(cur), source(cur)
        s1, s2 = side(cur), side(cur)
        body = "same repeated body for the same-context cleanup"
        p1, h, c_a_s1 = document(cur, source_id=a, side_id=s1, text=body, file_name="x.txt")
        p2, _, _ = document(cur, source_id=a, side_id=s1, text=body,
                            file_name="x copy.txt", hash_id=h)
        p3, _, _ = document(cur, source_id=a, side_id=s1, text=body,
                            file_name="x copy 2.txt", hash_id=h)
        p4, _, c_a_s2 = document(cur, source_id=a, side_id=s2, text=body, hash_id=h)
        p5, _, c_b_s1 = document(cur, source_id=b, side_id=s1, text=body, hash_id=h)
    conn.commit()

    service = DeduplicationService(lambda: conn)
    groups = [g for g in service.same_context_duplicates() if g["context_id"] == c_a_s1]
    assert len(groups) == 1
    assert groups[0]["keep_id"] == p1
    assert groups[0]["remove_ids"] == [p2, p3]

    other_contexts = {g["context_id"] for g in service.same_context_duplicates()}
    assert c_a_s2 not in other_contexts, "another side is a different context"
    assert c_b_s1 not in other_contexts, "another source is a different context"

    result = service.remove_same_context_duplicates()
    assert result["removed"] >= 2

    with conn.cursor() as cur:
        assert _ids_for_hash(cur, h) == [p1, p4, p5], "only the repeats in (a, side 1) go"
        cur.execute("SELECT COUNT(*) FROM hash_contexts WHERE hash_id = %s", (h,))
        assert cur.fetchone()[0] == 3, "every context of the shared content survives"
        cur.execute("SELECT COUNT(*) FROM hashs WHERE id = %s", (h,))
        assert cur.fetchone()[0] == 1, "the shared content itself must survive"
        cur.execute("SELECT COUNT(*) FROM contents WHERE hash_id = %s", (h,))
        assert cur.fetchone()[0] == 1, "extracted text must survive"
    conn.close()


def test_a_single_occurrence_is_never_a_repeat(pg_db):
    from database.services.dedup_service import DeduplicationService

    conn = connect(pg_db)
    with conn.cursor() as cur:
        a, s1 = source(cur), side(cur)
        p1, h, c = document(cur, source_id=a, side_id=s1, text="a lonely single record")
    conn.commit()

    service = DeduplicationService(lambda: conn)
    assert c not in {g["context_id"] for g in service.same_context_duplicates()}
    service.remove_same_context_duplicates()
    with conn.cursor() as cur:
        assert _ids_for_hash(cur, h) == [p1]
    conn.close()
