"""``POST /api/reports/runs`` with large file selections.

A selection above the criteria limit returned HTTP 400 with an English
technical message. The analytical-report page now refuses such a selection
before it sends a request. These tests pin the server limit and keep the
page's constant equal to it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.test_reports_api import _login_new, _post, corpus, sync_jobs  # noqa: F401

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


def test_the_page_limit_matches_the_server_limit():
    from core.criteria.model import MAX_IDS_PER_DIMENSION

    script = (ROOT / "static/js/modules/file-operations/fmas-analytical-report.js").read_text(encoding="utf-8")
    assert f"const MAX_REPORT_FILES = {MAX_IDS_PER_DIMENSION};" in script


def test_a_selection_over_the_limit_is_refused_with_the_limit_named(app, corpus, sync_jobs):
    from core.criteria.model import MAX_IDS_PER_DIMENSION

    analyst, _ = _login_new(app, "analyst")
    too_many = list(range(1, MAX_IDS_PER_DIMENSION + 2))
    resp = _post(analyst, "/api/reports/runs", {
        "report_id": "entry_content",
        "parameters": {"criteria": {"path_ids": too_many, "analyst_scope": "all", "unit": "path"}},
    })
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert f"at most {MAX_IDS_PER_DIMENSION} ids" in body["error"]["message"]


def test_a_selection_at_the_limit_is_accepted(app, corpus, sync_jobs):
    from core.criteria.model import MAX_IDS_PER_DIMENSION

    analyst, _ = _login_new(app, "analyst")
    resp = _post(analyst, "/api/reports/runs", {
        "report_id": "entry_content",
        "parameters": {"criteria": {"path_ids": list(range(1, MAX_IDS_PER_DIMENSION + 1)),
                                    "analyst_scope": "all", "unit": "path"}},
    })
    assert resp.status_code == 200, resp.get_data(as_text=True)[:300]
