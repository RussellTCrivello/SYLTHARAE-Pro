from core.search.cursor import decode_cursor, encode_cursor, parse_relevance_cursor, relevance_cursor
from core.search.normalize import pagination_query_signature, search_cache_key


def test_cursor_requires_matching_signature():
    sig = search_cache_key(query="report", sort_by="relevance", sort_order="desc")
    token = relevance_cursor(1.5, 42, "desc", query_signature=sig)
    assert parse_relevance_cursor(token, expected_signature=sig) == (1.5, 42, "desc")
    assert parse_relevance_cursor(token, expected_signature="other") is None


def test_pagination_signature_stable_for_route_and_service_inputs():
    """Mint/validate must use the same helper (regression: mixed filter keys → 400)."""
    sig = pagination_query_signature(
        query="This is a test",
        analyst_scope="uncategorized",
        file_statuses=["Read"],
        case_sensitive=True,
        whole_word=True,
        sort_by="relevance",
        sort_order="desc",
    )
    token = relevance_cursor(5.0, 327, "desc", query_signature=sig)
    assert parse_relevance_cursor(token, expected_signature=sig) == (5.0, 327, "desc")


def test_cursor_rejects_wrong_signature():
    sig = search_cache_key(query="a", sort_by="relevance", sort_order="desc")
    token = relevance_cursor(1.0, 1, "desc", query_signature=sig)
    data = decode_cursor(token)
    assert data is not None
    data["sig"] = "tampered"
    bad = encode_cursor(data)
    assert parse_relevance_cursor(bad, expected_signature=sig) is None
