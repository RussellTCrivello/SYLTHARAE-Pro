"""Can the category-list / tree-search plan regression be removed? (100k rows)"""
import json, pathlib, sys, psycopg2
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from services.i18n.term_labels import ID_SET_CAP
from core.i18n.term_key import term_key
from tools.i18n.audit_terms import _index_names

N = 100_000
cfg = json.load(open("/tmp/taxonomy_cfg.json"))["cfg"]
conn = psycopg2.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                        password=cfg["password"], dbname=cfg["database"])
conn.autocommit = False
TERM = "Computer networks"

VARIANTS = {
 "list/current-or": (
   "SELECT c.id, w.word FROM categorys c JOIN words w ON c.word_id = w.id "
   "WHERE (w.word ILIKE %s OR w.id = ANY(%s)) ORDER BY w.word LIMIT 200"),
 "list/union-ids": (
   "WITH hits AS (SELECT id FROM words WHERE id = ANY(%s) "
   "UNION SELECT id FROM words WHERE word ILIKE %s) "
   "SELECT c.id, w.word FROM categorys c JOIN words w ON c.word_id = w.id "
   "JOIN hits h ON h.id = w.id ORDER BY w.word LIMIT 200"),
 "list/text-only": (
   "SELECT c.id, w.word FROM categorys c JOIN words w ON c.word_id = w.id "
   "WHERE w.word ILIKE %s ORDER BY w.word LIMIT 200"),
 "tree/current-or": (
   "SELECT c.id FROM categorys c JOIN words w ON w.id = c.word_id "
   "WHERE (w.word ILIKE %s OR w.id = ANY(%s)) ORDER BY lower(w.word), c.id LIMIT 501"),
 "tree/union-ids": (
   "WITH hits AS (SELECT id FROM words WHERE id = ANY(%s) "
   "UNION SELECT id FROM words WHERE word ILIKE %s) "
   "SELECT c.id FROM categorys c JOIN words w ON w.id = c.word_id "
   "JOIN hits h ON h.id = w.id ORDER BY lower(w.word), c.id LIMIT 501"),
 "tree/text-only": (
   "SELECT c.id FROM categorys c JOIN words w ON w.id = c.word_id "
   "WHERE w.word ILIKE %s ORDER BY lower(w.word), c.id LIMIT 501"),
}

def params(key):
    if key.endswith("text-only"):
        return None
    if key.endswith("union-ids"):
        return "union"
    return "current"

def run(sql, kind, cap_ids):
    if kind is None:
        p = (f"%{TERM}%",)
    elif kind == "union":
        p = (list(cap_ids), f"%{TERM}%")
    else:
        p = (f"%{TERM}%", list(cap_ids))
    with conn.cursor() as cur:
        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, p)
        plan = cur.fetchone()[0][0]
    return {"exec_ms": round(plan.get("Execution Time", 0), 3),
            "rows": plan["Plan"].get("Actual Rows"),
            "index": _index_names(plan["Plan"]),
            "node": plan["Plan"].get("Node Type")}

try:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO words (word) SELECT 'scale-term-' || lpad(g::text,6,'0') FROM generate_series(1,%s) g", (N,))
        cur.execute("INSERT INTO term_names (word_id,name,match_key,language,name_type,script,source) SELECT id, word, lower(word),'en','preferred','Latn','backfill' FROM words WHERE word LIKE 'scale-term-%%'")
        cur.execute("INSERT INTO categorys (word_id) SELECT id FROM words WHERE word LIKE 'scale-term-%%'")
        cur.execute("ANALYZE words"); cur.execute("ANALYZE categorys")
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM words ORDER BY id LIMIT %s", (ID_SET_CAP,))
        cap_ids = [r[0] for r in cur.fetchall()]
    results = {}
    for key, sql in VARIANTS.items():
        results[key] = run(sql, params(key), cap_ids)
    # NOTE: a trigram index would make ILIKE '%term%' indexable, but this
    # sandbox's PostgreSQL has no pg_trgm contrib module, so that branch is
    # ENV-BLOCKED and not measured (see REPORT.md).
finally:
    conn.rollback()
print(json.dumps(results, indent=2))
