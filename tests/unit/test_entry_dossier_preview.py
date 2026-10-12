"""Live Full Entry Report helpers (no database)."""

from services.reporting.entry_dossier import normalize_ids, parse_id_query


def test_parse_id_query_dedupes_and_drops_junk():
    assert parse_id_query("3, 3, -1, x, 8, 0") == [3, 8]
    assert parse_id_query("") == []
    assert parse_id_query(None) == []


def test_normalize_ids_caps_at_the_listing_limit():
    ids = normalize_ids(range(1, 250))
    assert ids == list(range(1, 101))
    assert normalize_ids(["12", 12, "nope"]) == [12]
