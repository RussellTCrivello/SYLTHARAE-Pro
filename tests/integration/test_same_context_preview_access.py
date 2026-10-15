"""``GET /api/files/same-context-duplicates`` (the preview of repeats to remove).

The preview named files and ids across the whole corpus, and any signed-in user
could read it, including viewers. It is now limited to the roles that may
remove repeats (admin, analyst), like the removal route itself.
"""

from __future__ import annotations

import pytest

from _seed import connect, document, side, source, word_counts  # noqa: F401
from tests.integration.test_reports_api import _login_new  # noqa: F401

pytestmark = pytest.mark.integration

URL = "/api/files/same-context-duplicates"


@pytest.fixture()
def repeated_file(pg_db):
    """Two identical records in one source and side: a real repeat to preview."""
    import uuid

    marker = f"repeat-{uuid.uuid4().hex[:8]}"
    conn = connect(pg_db)
    with conn, conn.cursor() as cur:
        s1, d1 = source(cur), side(cur)
        # A repeat is the same name, content and details in one source and side:
        # the second record reuses the first record's content hash.
        _, hash_id, _ = document(cur, source_id=s1, side_id=d1, text=f"{marker} body",
                                 file_name=f"{marker}.txt")
        document(cur, source_id=s1, side_id=d1, text=f"{marker} body",
                 file_name=f"{marker}.txt", hash_id=hash_id)
    conn.close()
    return marker


def test_anonymous_requests_are_refused(app, repeated_file):
    resp = app.test_client().get(URL)
    assert resp.status_code == 401


def test_a_viewer_cannot_see_the_repeats(app, client_factory, repeated_file):
    viewer = client_factory("viewer")
    resp = viewer.get(URL)
    assert resp.status_code == 403, resp.get_data(as_text=True)[:200]
    body = resp.get_data(as_text=True)
    assert repeated_file not in body


@pytest.mark.parametrize("role", ["analyst", "admin"])
def test_roles_that_can_remove_repeats_see_the_preview(app, client_factory, repeated_file, role):
    client = client_factory(role)
    resp = client.get(URL)
    assert resp.status_code == 200, resp.get_data(as_text=True)[:200]
    body = resp.get_json()
    assert body["success"] is True and body["to_remove"] >= 1
    assert any(repeated_file in g["file_name"] for g in body["sample"])
