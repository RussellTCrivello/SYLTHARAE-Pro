"""Live-DB check: Q07 flat OR returns stable result shape (run when DB available)."""

from __future__ import annotations

import pytest

from tools.perf.bootstrap_runtime import bootstrap_runtime, db_connection_probe


@pytest.fixture(scope="module", autouse=True)
def _runtime():
    bootstrap_runtime()


@pytest.mark.integration
def test_q07_or_returns_expected_hit_count():
    probe = db_connection_probe()
    if not probe.get("connected"):
        pytest.skip(probe.get("error") or "database unavailable")

    from Api.services.search_service import SearchService

    results, _total = SearchService.advanced_search(
        "report OR invoice OR contract OR memo",
        limit=25,
        use_bm25=False,
        use_expansion=False,
        analyst_scope="all",
        fast_mode=True,
        include_snippets=False,
        count_mode="skip",
    )
    assert SearchService._last_literal_compile == "flat_or"
    assert len(results) == 25
    ids = [int(r["id"]) for r in results]
    assert len(ids) == len(set(ids))
