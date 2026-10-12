from __future__ import annotations

from Api.services import search_service


def test_fast_mode_uses_sql_limit_offset(monkeypatch):
    class Cursor:
        def __init__(self):
            self.queries = []

        def execute(self, query, params=()):
            self.queries.append((query, params))

        def fetchone(self):
            return (0,)

        def fetchall(self):
            return []

        def close(self):
            pass

    class Connection:
        def __init__(self):
            self.cursor_instance = Cursor()

        def cursor(self):
            return self.cursor_instance

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    connection = Connection()
    monkeypatch.setattr(search_service, "get_connection", lambda: connection)

    search_service.SearchService.advanced_search(
        "alpha beta",
        limit=20,
        offset=40,
        use_bm25=False,
        use_expansion=False,
        use_fuzzy=False,
        analyst_scope="all",
        fast_mode=True,
        include_snippets=False,
        count_mode="exact",
    )

    candidate_sql = next(
        sql for sql, _ in connection.cursor_instance.queries
        if "LIMIT %s OFFSET %s" in sql
    )
    assert "relevance_score" in candidate_sql
    limit_params = next(
        params for sql, params in connection.cursor_instance.queries
        if "LIMIT %s OFFSET %s" in sql
    )[-2:]
    assert limit_params == (20, 40)
