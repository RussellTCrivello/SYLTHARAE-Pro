"""Covering index for hash-scoped word lookups during search."""

version = "0035"
name = "search_inverted_index_cover"

SQL_STATEMENTS = [
    (
        "CREATE INDEX IF NOT EXISTS idx_words_hashs_hash_word "
        "ON words_hashs (hash_id, word_id)"
    ),
]


def upgrade(conn) -> None:
    with conn.cursor() as cur:
        for statement in SQL_STATEMENTS:
            cur.execute(statement)


def downgrade(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP INDEX IF EXISTS idx_words_hashs_hash_word")
