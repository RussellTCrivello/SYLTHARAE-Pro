"""Reverse-order inverted index for word → file candidate generation."""

version = "0036"
name = "words_hashs_word_hash_index"

SQL_STATEMENTS = [
    (
        "CREATE INDEX IF NOT EXISTS idx_words_hashs_word_hash "
        "ON words_hashs (word_id, hash_id)"
    ),
]


def upgrade(conn) -> None:
    with conn.cursor() as cur:
        for statement in SQL_STATEMENTS:
            cur.execute(statement)


def downgrade(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP INDEX IF EXISTS idx_words_hashs_word_hash")
