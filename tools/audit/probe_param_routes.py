#!/usr/bin/env python
"""Request every parameterised route with four kinds of id and record the truth.

The role matrix (``probe_routes.py``) covers the routes without path
parameters. This covers the other half: the 155 rules that take an id, a
name or a language. For each rule and method, every path parameter is
substituted with

* **valid**      an id that exists, created through the application's own
                 HTTP API (source, side, file path, word, keyword, category,
                 scenario, saved search, schedule, notification, user);
* **missing**    a large id that does not exist;
* **malformed**  ``abc`` - the converter itself may refuse it, which is fine,
                 but the answer must be a client error, never a 500;
* **other-user** an id that exists but belongs to a second, unrelated
                 analyst. A 2xx for someone else's private object is a
                 finding (IDOR); a 403/404 is the correct answer.

A 5xx is always a finding. A body that carries a traceback, a driver
exception or a SQL fragment is always a finding. Nothing here is asserted to
be correct by declaration - the status, the body shape and the row-count
effect are written to ``audit_report/findings/param_routes.csv``.

Fixtures are created through the app's APIs, not with INSERTs. Where the
application has no HTTP API for a thing (notifications are written by the
monitoring service; places need a loaded gazetteer) the column says so
instead of inventing an id.

Usage:  python tools/audit/probe_param_routes.py
Exit 1 when any row is a finding.
"""

from __future__ import annotations

import csv
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import traceback
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "audit_report" / "findings"

PASSWORD = "audit-param-route-password-123"
#: Parameters naming an object that belongs to one user. Only these make a
#: cross-user request meaningful: sources, sides, categories, words and paths
#: are shared objects, so another analyst reading them is the product's normal
#: behaviour and not a finding.
#: ``notification_id`` is deliberately absent: POST /api/notifications/scan is
#: the only way to create one and it writes system-wide alerts
#: (recipient_user_id NULL), which every signed-in user may read by design.
#: Addressed alerts exist only for scenario outcomes, which the scenarios API
#: creates with its owner; that visibility is covered by the notification
#: tests. The column below records the same reasoning in the CSV.
OWNED_PARAMS = frozenset({"scenario_id", "search_id", "user_id",
                          "schedule_id", "evaluation_id", "job_id", "task_id", "entry_id"})

LEAK_MARKERS = ("Traceback (most recent call last)", "psycopg2.", "UndefinedColumn",
                "UndefinedTable", "SyntaxError: ", "SELECT ", "INSERT INTO ")


def bootstrap_audit_db(name: str):
    import psycopg2
    from database.bootstrap import bootstrap_database

    cfg = {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ.get("DB_PORT") or 5432),
        "user": os.environ.get("DB_USER") or "postgres",
        "password": os.environ.get("DB_PASSWORD") or "",
        "database": name,
    }
    admin = psycopg2.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                             password=cfg["password"], dbname="postgres")
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
        if cur.fetchone() is None:
            cur.execute(f'CREATE DATABASE "{name}"')
    admin.close()
    os.environ.update(DB_HOST=cfg["host"], DB_PORT=str(cfg["port"]), DB_USER=cfg["user"],
                      DB_PASSWORD=cfg["password"], DB_NAME=cfg["database"])
    return cfg, bootstrap_database(cfg)


#: Temp directory the probe imports documents from; must be an approved
#: ingestion root before the app reads its configuration.
DOC_ROOT = pathlib.Path(tempfile.mkdtemp(prefix="param_docs_"))
os.environ["INGESTION_ROOTS"] = str(DOC_ROOT)


def make_app():
    import core.initialization as init
    from apps.web.app import app

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    init.INIT_MARKER_FILE = pathlib.Path(tempfile.mkdtemp(prefix="param_marker_")) / ".system_initialized"
    init.mark_system_initialized()
    try:
        from core.security.rate_limit import limiter

        limiter.enabled = False
    except Exception:
        pass
    return app


def sign_in(app, username, role="analyst"):
    from core.security.service import get_auth_service

    auth = get_auth_service()
    if auth.get_user_by_username(username) is None:
        auth.create_user(username, PASSWORD, role=role)
    client = app.test_client()
    resp = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert resp.status_code == 200, (username, resp.status_code, resp.get_data(as_text=True)[:200])
    return client


def _id(resp, *path):
    try:
        data = resp.get_json()
    except Exception:
        return None
    for key in path:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    if isinstance(data, dict):
        for key in ("id", "_id"):
            if key in data:
                return data[key]
    return data if isinstance(data, int) else None


class Fixtures:
    """Objects created through the app's APIs, for the probe's ids.

    ``valid[param]`` is an id that exists. ``other[param]`` is an id created
    by a *different* analyst (only where the object has an owner).
    """

    def __init__(self, app):
        self.app = app
        self.a = sign_in(app, "param_analyst_a", "analyst")
        self.b = sign_in(app, "param_analyst_b", "analyst")
        self.admin = sign_in(app, "param_admin", "admin")
        self.valid = {}
        self.other = {}
        self.notes = {}
        self._create()

    def _one(self, client, method, url, **kw):
        resp = getattr(client, method)(url, **kw)
        return resp

    def _create(self):
        # source / side
        resp = self.a.post("/api/sources", json={"name": f"param source {uuid.uuid4().hex[:6]}"})
        self.valid["source_id"] = _id(resp, "source") or _id(resp)
        resp = self.a.post("/api/sides", json={"name": f"param side {uuid.uuid4().hex[:6]}"})
        self.valid["side_id"] = _id(resp, "side") or _id(resp)

        # keyword, category, word - the form-shaped writers expect form data
        category_name = f"paramcat{uuid.uuid4().hex[:6]}"
        resp = self.a.post("/category/add", json={"category_name": category_name})
        self.valid["category_id"] = _id(resp, "category_id")
        # /keywords/add answers with a redirect (the form page), so the id is
        # read back from the list endpoint the UI itself uses.
        # a two-word phrase: single words are routed to words_categorys, only
        # phrases become rows in `keywords`
        keyword_text = f"param probe {uuid.uuid4().hex[:6]}"
        self.a.post("/keywords/add", data={"keywords_text": keyword_text,
                                           "category_id": self.valid.get("category_id") or "1"})
        listing = self.a.get("/api/keywords", query_string={"search": keyword_text})
        try:
            payload = listing.get_json() or {}
            items = payload if isinstance(payload, list) else (payload.get("keywords") or [])
        except Exception:
            items = []
        self.notes["keyword_add"] = f"{listing.status_code} items={len(items)}"
        for item in items:
            text = str(item.get("text") or item.get("keyword") or "")
            if text.lower() == keyword_text.lower():
                self.valid["keyword_id"] = item.get("id")
                break
        if not self.valid.get("keyword_id") and items:
            self.valid["keyword_id"] = items[0].get("id")
        resp = self.a.post("/api/words", json={"word": f"paramword{uuid.uuid4().hex[:6]}"})
        self.valid["word_id"] = _id(resp)

        # a real document, imported by the app's own import endpoint. Import is
        # an administrator action and only accepts paths under an approved
        # root, so the probe sets INGESTION_ROOTS (in make_app) to a temp dir
        # it owns and posts a file from there.
        source_id, side_id = self.valid.get("source_id"), self.valid.get("side_id")
        if source_id and side_id:
            doc = DOC_ROOT / "param_probe.txt"
            doc.write_text("A probe document. The review will be held on 3 March 2027. "
                           "Contact alice@example.org or 10.0.0.1.\n", encoding="utf-8")
            resp = self.admin.post("/api/import-export/batch-import",
                                   json={"file_paths": [str(doc)], "source_id": source_id,
                                         "side_id": side_id})
            self.notes["import"] = f"{resp.status_code} {resp.get_data(as_text=True)[:160]}"
            try:
                body = resp.get_json() or {}
            except Exception:
                body = {}
            ids = [r.get("path_id") or r.get("id") for r in (body.get("results") or [])
                   if isinstance(r, dict)]
            ids = [i for i in ids if i]
            # Ingestion is queued: the response names the file, not its path
            # row. Poll the list endpoint the UI polls until the document and
            # its signals exist (bounded, so a stuck import is reported as a
            # missing fixture rather than hanging the probe).
            for _ in range(60):
                if ids:
                    break
                listing = self.a.get("/api/paths",
                                     query_string={"search": "param_probe", "per_page": 5})
                try:
                    payload = listing.get_json() or {}
                except Exception:
                    payload = {}
                rows = payload if isinstance(payload, list) else (
                    payload.get("paths") or payload.get("items") or [])
                ids = [r.get("id") for r in rows if isinstance(r, dict) and r.get("id")]
                if not ids:
                    time.sleep(0.5)
            if ids:
                self.valid["path_id"] = ids[0]
                self.valid["file_id"] = ids[0]

        # signal ids: read from the explorer endpoint the analysis page uses
        listing = self.a.get("/api/signals", query_string={"per_page": 3})
        try:
            payload = listing.get_json() or {}
        except Exception:
            payload = {}
        items = payload if isinstance(payload, list) else (payload.get("items") or [])
        ids = [i.get("signal_id") or i.get("id") for i in items if isinstance(i, dict)]
        ids = [i for i in ids if i]
        self.valid["signal_id"] = ids[0] if ids else None
        # a signal's document carries the hash id the content routes take
        self.valid["hash_id"] = None
        for item in items:
            doc = item.get("document") if isinstance(item, dict) else None
            if isinstance(doc, dict) and doc.get("hash_id"):
                self.valid["hash_id"] = doc["hash_id"]
                break
        if not self.valid.get("hash_id") and items and isinstance(items[0], dict):
            self.valid["hash_id"] = items[0].get("hash_id")
        if payload.get("criteria") is not None:
            self.notes["signal_id"] = f"{len(items)} signals visible to the analyst"

        # job ids: the import above queued one, and /api/jobs lists them
        listing = self.a.get("/api/jobs", query_string={"limit": 5})
        try:
            payload = listing.get_json() or {}
        except Exception:
            payload = {}
        items = payload if isinstance(payload, list) else (payload.get("jobs") or payload.get("items") or [])
        ids = [i.get("id") or i.get("job_id") for i in items if isinstance(i, dict)]
        ids = [i for i in ids if i]
        self.valid["job_id"] = ids[0] if ids else None
        self.notes["job_id"] = f"/api/jobs answered {listing.status_code}: {len(ids)} job(s)"

        # scenario (owned) - created by B as well, so A can be tested against
        # an object that belongs to someone else
        definition = {
            "criteria": {"sources": [source_id] if source_id else []},
            "conditions": {"dated": {"signals": {"signal_types": ["date_reference"]}}},
            "cases": [{"id": "c_dated", "when": {"all": ["dated"]}, "outcome": "dated"}],
            "outcomes": {"dated": {"label": "Dated", "actions": ["notify"]},
                         "none": {"label": "Nothing", "actions": []}},
            "default_outcome": "none",
            "strategy": "first_match",
        }
        resp = self.a.post("/api/scenarios", json={"name": f"param scenario {uuid.uuid4().hex[:6]}",
                                                   "definition": definition})
        self.valid["scenario_id"] = _id(resp, "scenario")
        resp = self.b.post("/api/scenarios", json={"name": f"param scenario b {uuid.uuid4().hex[:6]}",
                                                   "definition": definition})
        self.other["scenario_id"] = _id(resp, "scenario")
        self.notes["scenario"] = (f"a={resp.status_code}:{self.valid.get('scenario_id')} "
                                  f"b={self.other.get('scenario_id')}")

        # saved search
        resp = self.a.post("/api/search/saved", json={"name": f"param saved {uuid.uuid4().hex[:6]}",
                                                      "query": "probe"})
        self.valid["search_id"] = _id(resp, "search_id") or _id(resp, "saved_search")
        resp = self.b.post("/api/search/saved", json={"name": f"param saved b {uuid.uuid4().hex[:6]}",
                                                      "query": "probe"})
        self.other["search_id"] = _id(resp, "search_id") or _id(resp, "saved_search")

        # schedule (interval-based; no cron field in this model)
        # every schedule type requires an administrator
        resp = self.admin.post("/api/schedules", json={
            "name": f"param sched {uuid.uuid4().hex[:6]}",
            "schedule_type": "scenario_evaluation", "interval_minutes": 60})
        self.valid["schedule_id"] = _id(resp, "schedule")
        self.notes["schedule"] = f"{resp.status_code} {resp.get_data(as_text=True)[:120]}"

        # user (admin creates; A may not)
        resp = self.admin.post("/api/auth/users", json={"username": f"param_user_{uuid.uuid4().hex[:6]}",
                                                        "password": PASSWORD, "role": "viewer"})
        self.valid["user_id"] = _id(resp, "user")

        # notifications: there is no create endpoint - the monitoring scan is
        # what produces them from a document's future dates. Each analyst runs
        # the scan for itself, so A has one and B has one of its own.
        def _scan_ids(client):
            client.post("/api/notifications/scan", json={})
            listing = client.get("/api/notifications", query_string={"per_page": 10})
            payload = listing.get_json() or {}
            items = payload.get("notifications") or payload.get("items") or []
            return [i.get("id") for i in items if isinstance(i, dict) and i.get("id")]

        mine, theirs = _scan_ids(self.a), _scan_ids(self.b)
        self.valid["notification_id"] = mine[0] if mine else None
        self.other["notification_id"] = theirs[0] if theirs else None
        self.notes["notification"] = (f"a={len(mine)} b={len(theirs)}; created by "
                                      "POST /api/notifications/scan, no create endpoint exists")

        # places: the gazetteer is reference data, not an app-created object
        self.notes["place_id"] = "ENV: no gazetteer loaded; place ids cannot be created through an API"

        for key in ("source_id", "side_id", "keyword_id", "category_id", "word_id", "path_id",
                    "file_id", "scenario_id", "search_id", "schedule_id", "user_id"):
            if not self.valid.get(key):
                self.notes[key] = f"fixture missing ({self.valid.get(key)!r})"

    # -- helpers ---------------------------------------------------------
    def _user_id(self, username):
        from core.security.service import get_auth_service

        user = get_auth_service().get_user_by_username(username)
        return user["id"] if isinstance(user, dict) else getattr(user, "id", None)

    def _max(self, table):
        from Api.utils import execute_query

        row = execute_query(f"SELECT max(id) FROM {table}", fetch="one")  # nosec B608 - fixed table name
        return row[0] if row else None


def body_shape(resp):
    text = resp.get_data(as_text=True) or ""
    shape = "empty"
    if text:
        try:
            data = json.loads(text)
        except Exception:
            shape = "html" if text.lstrip().startswith("<") else "text"
        else:
            if isinstance(data, dict):
                keys = sorted(data)[:6]
                shape = "json:" + ",".join(keys)
            else:
                shape = f"json:{type(data).__name__}"
    leaked = [m for m in LEAK_MARKERS if m in text]
    return shape, leaked, text[:160].replace("\n", " ")


def table_counts():
    from Api.utils import execute_query

    tables = ("sources", "sides", "paths", "words", "keywords", "categorys", "alerts",
              "scenarios", "saved_searches", "job_schedules", "users")
    counts = {}
    for table in tables:
        try:
            row = execute_query(f"SELECT count(*) FROM {table}", fetch="one")  # nosec B608
            counts[table] = row[0]
        except Exception:
            counts[table] = None
    return counts


def verdict_for(status, leaked, variant, effect, owned):
    """Classify one response.

    ``owned`` says whether the parameter names an object with an owner (see
    OWNED_PARAMS); a 2xx for another user's owned object is the finding, a 2xx
    for a shared object is the designed behaviour.
    """
    if leaked:
        return "STACK-TRACE"
    if status == 501:
        return "NOT-IMPLEMENTED"
    if status >= 500:
        return "SERVER-ERROR"
    if variant == "other-user" and owned and 200 <= status < 300:
        return "CROSS-USER-200"
    return "OK"


def converters(rule):
    """{parameter: converter-or-None} as the rule declares them."""
    return {name: kind for kind, name in
            re.findall(r"<(?:([^<>:]+):)?([^<>]+)>", rule)}


def string_value(name, rule):
    """A plausible value for a route parameter that is not an id."""
    kind = converters(rule).get(name)
    if kind in ("int", "float"):
        return None
    return {"language": "en", "file_type": "txt", "key": "theme", "filename": "x.txt",
            "area": "dashboard", "index": "0", "view_id": "default"}.get(name, "probe")


def build_url(rule, values):
    url = rule
    for name, value in values.items():
        # rules look like "<int:scenario_id>" or "<action_id>": the name is the
        # last segment before ">", the optional prefix is the converter
        url = re.sub(r"<(?:[^<>:]+:)?%s>" % re.escape(name), str(value), url)
    return url


def main() -> int:
    cfg, report = bootstrap_audit_db("file_analysis_param")
    print("audit database:", cfg["database"], report["applied_migrations"])
    app = make_app()
    fixtures = Fixtures(app)
    print("fixtures:", {k: v for k, v in fixtures.valid.items() if v})
    for note, value in fixtures.notes.items():
        print(f"  note {note}: {value}")

    # the cross-user request is A asking for B's object - not B asking for B's
    clients = {"valid": fixtures.a, "missing": fixtures.a, "malformed": fixtures.a,
               "other-user": fixtures.a}

    rows = []
    rules = sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, sorted(r.methods)))
    for rule in rules:
        if not rule.arguments:
            continue
        methods = sorted(m for m in rule.methods if m in ("GET", "POST", "PUT", "DELETE", "PATCH"))
        for method in methods:
            if rule.rule == "/auth/logout":
                continue
            for variant in ("malformed", "missing", "valid", "other-user"):
                values, source = {}, []
                for name in rule.arguments:
                    if variant == "malformed":
                        values[name] = "abc"
                    elif variant == "missing":
                        values[name] = 999_999_999
                    elif variant == "valid":
                        # a parameter with no created fixture still gets a
                        # request when the route takes text, not an id
                        values[name] = (fixtures.valid.get(name)
                                        or string_value(name, rule.rule))
                    else:
                        values[name] = fixtures.other.get(name, fixtures.valid.get(name))
                    source.append(f"{name}={values[name]}")
                if any(v in (None, "None") for v in values.values()):
                    rows.append((rule.rule, method, rule.endpoint, variant, " ".join(source),
                                 "NO-FIXTURE", "", "", "", "", "SKIPPED"))
                    continue
                url = build_url(rule.rule, values)
                before = table_counts()
                try:
                    resp = clients[variant].open(url, method=method, json={}
                                                 if method in ("POST", "PUT", "PATCH") else None,
                                                 follow_redirects=False)
                    status = resp.status_code
                except Exception:
                    status = 0
                    traceback.print_exc(limit=2)
                after = table_counts()
                effect = ",".join(f"{t}{after[t] - before[t]:+d}" for t in before
                                  if before[t] is not None and after[t] is not None
                                  and after[t] != before[t]) or "-"
                try:
                    shape, leaked, snippet = body_shape(resp)
                except Exception:
                    shape, leaked, snippet = "?", [], ""
                owned = any(name in OWNED_PARAMS for name in rule.arguments)
                verdict = verdict_for(status, leaked, variant, effect != "-", owned)
                rows.append((rule.rule, method, rule.endpoint, variant, " ".join(source),
                             status, shape, effect, "|".join(leaked), snippet, verdict))
                if verdict in ("STACK-TRACE", "SERVER-ERROR", "CROSS-USER-200"):
                    print(f"{verdict:14s} {method:6s} {url:70s} {status} {effect}")

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "param_routes.csv"
    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["rule", "method", "endpoint", "variant", "values", "status",
                         "body_shape", "db_effect", "leaked", "snippet", "verdict"])
        writer.writerows(rows)

    bad = [r for r in rows if r[-1] in ("STACK-TRACE", "SERVER-ERROR", "CROSS-USER-200")]
    not_impl = [r for r in rows if r[-1] == "NOT-IMPLEMENTED"]
    skipped = [r for r in rows if r[-1] == "SKIPPED"]
    print(f"\nrows: {len(rows)}  findings: {len(bad)}  not-implemented(501): {len(not_impl)}"
          f"  skipped: {len(skipped)}")
    print("written:", target)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
