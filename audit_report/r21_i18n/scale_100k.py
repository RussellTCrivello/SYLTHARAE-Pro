"""100k-word scale measurement for the six term predicates (round 21, A3).

Everything runs inside one transaction that is rolled back, so the scratch
database is left exactly as it was; the script asserts that at the end.
"""
import csv
import json
import pathlib
import sys

import psycopg2

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from services.i18n.term_labels import ID_SET_CAP  # noqa: E402
from core.i18n.term_key import term_key  # noqa: E402
from tools.i18n.audit_terms import _PLAN_SQL, _index_names  # noqa: E402

N = 100_000
cfg = json.load(open("/tmp/taxonomy_cfg.json"))["cfg"]
conn = psycopg2.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                        password=cfg["password"], dbname=cfg["database"])
conn.autocommit = False


def counts():
    with conn.cursor() as cur:
        out = {}
        for t in ("words", "term_names", "categorys", "words_categorys", "keywords"):
            cur.execute(f"SELECT count(*) FROM {t}")
            out[t] = cur.fetchone()[0]
    return out


def rows(conn):
    """Plan rows, without the rollback that audit_terms.plans() does."""
    cap_ids = [r[0] for r in fetch(conn, "SELECT id FROM words ORDER BY id LIMIT %s",
                                   (ID_SET_CAP,))]
    with conn.cursor() as cur:
        cur.execute("SELECT word FROM words WHERE word = %s", ("Computer networks",))
        row = cur.fetchone()
    term = row[0] if row else fetch(conn, "SELECT word FROM words ORDER BY id LIMIT 1")[0][0]
    out = []
    for name, template in _PLAN_SQL.items():
        if name == "resolver-lookup":
            for kind, params in (("text-only", ([term_key(term)],)),
                                 ("expanded", ([term_key(term), term_key(term) + "s"],))):
                out.append(_explain(conn, name, kind, template, params, len(params[0]), term))
            continue
        for kind, sql, params in (
                ("text-only", template.format(predicate="w.word ILIKE %s"), (f"%{term}%",)),
                ("expanded",
                 template.format(predicate="(w.word ILIKE %s OR w.id = ANY(%s))"),
                 (f"%{term}%", list(cap_ids)))):
            out.append(_explain(conn, name, kind, sql, params, len(cap_ids), term))
    return out


def fetch(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _explain(conn, site, kind, sql, params, id_set, term):
    with conn.cursor() as cur:
        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params)
        plan = cur.fetchone()[0]
    data = plan[0]
    return {"site": site, "variant": kind,
            "execution_ms": round(data.get("Execution Time", 0), 3),
            "planning_ms": round(data.get("Planning Time", 0), 3),
            "plan_rows": data["Plan"].get("Actual Rows"),
            "node": data["Plan"].get("Node Type"),
            "index_used": _index_names(data["Plan"]),
            "id_set": id_set, "term": term,
            "shared_hit": data["Plan"].get("Shared Hit Blocks"),
            "shared_read": data["Plan"].get("Shared Read Blocks")}


before = counts()
try:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO words (word)
            SELECT 'scale-term-' || lpad(g::text, 6, '0') FROM generate_series(1, %s) g
        """, (N,))
        cur.execute("""
            INSERT INTO term_names (word_id, name, match_key, language, name_type, script, source)
            SELECT w.id, w.word, lower(w.word), 'en', 'preferred', 'Latn', 'backfill'
            FROM words w WHERE w.word LIKE 'scale-term-%%'
        """)
        cur.execute("""
            INSERT INTO categorys (word_id)
            SELECT w.id FROM words w WHERE w.word LIKE 'scale-term-%%'
        """)
        cur.execute("""
            INSERT INTO words_categorys (word_id, category_id)
            SELECT c.word_id, c.id FROM categorys c
            JOIN words w ON w.id = c.word_id WHERE w.word LIKE 'scale-term-%%'
        """)
        cur.execute("""
            INSERT INTO keywords (keyword, category_id)
            SELECT convert_to(c.id::text, 'UTF8'), c.id FROM categorys c
            JOIN words w ON w.id = c.word_id WHERE w.word LIKE 'scale-term-%%'
        """)
    after_insert = counts()
    with conn.cursor() as cur:
        cur.execute("ANALYZE words"); cur.execute("ANALYZE term_names")
        cur.execute("ANALYZE categorys"); cur.execute("ANALYZE words_categorys")
        cur.execute("ANALYZE keywords")
    measured = rows(conn)
finally:
    conn.rollback()

after = counts()
json.dump({"before": before, "after_insert": after_insert, "after_rollback": after,
           "rows": measured, "id_set_cap": ID_SET_CAP, "inserted": N},
          open("/tmp/scale100k.json", "w"), indent=2)
w = csv.DictWriter(open("/tmp/scale100k.csv", "w", newline=""), fieldnames=list(measured[0]), extrasaction="ignore")
w.writeheader(); w.writerows(measured)
print("before     ", before)
print("after insert", after_insert)
print("after rollback", after)
print("unchanged:", before == after)
for r in measured:
    print(f"{r['site']:15s} {r['variant']:10s} {r['execution_ms']:8.3f} ms  "
          f"rows={r['plan_rows']} node={r['node']} idx={r['index_used']}")
conn.close()
