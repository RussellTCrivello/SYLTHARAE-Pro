"""Integration: the read-only database integrity audit tool keeps its contracts.

``tools/db/integrity_audit.py`` is the reproducible query set behind
``docs/database/RELATIONSHIP_INTEGRITY.md`` and it gates deployments by exit
status, so its contracts are worth pinning:

* ``--json`` writes a *parseable document* to stdout. It did not: the closing
  ``no findings`` line went to stdout too, so the documented
  ``--json > integrity.json`` produced a file no parser accepts - and a caller
  that treats a parse failure as "nothing to report" sees a clean bill of health
  on a database with findings. The status line belongs on stderr.
* exit 0 when every check is clean on a freshly migrated database, and the
  ``redundant_indexes`` group does **not** change that: the nine shapes there
  are the registered redundancies of
  ``docs/database/DUPLICATION_REGISTER.md`` (DB-1, DB-2), pending a decision.
* exit 1 - with the offending table and column named - when a value is outside
  the vocabulary the code defines.

The registered-shape expectation below is a tripwire and it is now empty: m0038
removed the nine duplicate shapes the register listed (DB-1/DB-2). Any entry
here is a *new* duplicate shape - either the schema grew one, or a migration that
adds an index over columns a constraint already indexes needs to justify itself.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from _seed import connect

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "db" / "integrity_audit.py"

#: Duplicate index shapes the register accepts. Empty since m0038 removed the
#: nine it listed; the set stays as the place to declare any future exception.
REGISTERED_REDUNDANT_SHAPES = set()


@pytest.fixture(scope="module")
def audit_db(pg_settings):
    """A database of its own, freshly migrated, for the audit's contracts.

    Every claim below is about a *fresh* database. The session database is
    shared with the rest of the run - a neighbour legitimately leaves rows
    behind, and a test that replays a migration's downgrade leaves the older
    index set behind - so auditing it would report the neighbours' leftovers as
    the schema's findings. The audit tool reads the ``DB_*`` variables, so this
    fixture hands it a private database instead.
    """
    import os
    import uuid

    from database.bootstrap import bootstrap_database

    cfg = {"host": pg_settings["host"], "port": int(pg_settings["port"]),
           "user": pg_settings["user"], "password": pg_settings["password"],
           "database": f"syltharae_audit_{os.getpid()}_{uuid.uuid4().hex[:6]}"}
    report = bootstrap_database(cfg)
    assert report["database_created"] is True
    try:
        yield cfg
    finally:
        try:
            import psycopg2
            admin = psycopg2.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                                     password=cfg["password"], dbname="postgres")
            admin.autocommit = True
            with admin.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS "{cfg["database"]}" WITH (FORCE)')
            admin.close()
        except Exception:  # the disposable server is taken down with the run
            pass


def _audit(db, *args):
    """Run the tool against ``db``, not against whatever the session built."""
    import os

    env = dict(os.environ, DB_HOST=str(db["host"]), DB_PORT=str(db["port"]),
               DB_USER=str(db["user"]), DB_PASSWORD=str(db["password"]),
               DB_NAME=str(db["database"]))
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, cwd=str(ROOT), env=env)


def test_json_output_is_a_parseable_document(audit_db):
    """`--json > file` must produce valid JSON - status lines go to stderr."""
    result = _audit(audit_db, "--json")
    payload = json.loads(result.stdout)  # the contract: this must not raise
    assert payload["tables"] >= 40
    # The human-readable tail belongs on stderr in machine mode.
    assert "no findings" not in result.stdout
    assert result.stdout.strip().startswith("{")


def test_a_clean_migrated_database_exits_zero(audit_db):
    """An empty, freshly migrated database has no findings."""
    result = _audit(audit_db, "--json")
    payload = json.loads(result.stdout)
    problems = [item
                for group in ("orphans", "duplicate_keys", "vocabularies",
                              "required_in_practice")
                for item in payload[group]
                if item.get("error") or item.get("count")
                or item.get("validated") is False]
    assert problems == []
    assert result.returncode == 0


def test_no_constraint_is_left_unvalidated(audit_db):
    """A ``NOT VALID`` constraint would mean rows nobody checked."""
    payload = json.loads(_audit(audit_db, "--json").stdout)
    assert [o for o in payload["orphans"] if o["validated"] is False] == []


def test_no_duplicate_index_shape_remains(audit_db):
    """m0038 removed the nine; a new duplicate shape fails here."""
    result = _audit(audit_db, "--json")
    payload = json.loads(result.stdout)
    shapes = {(item["table"], item["shape"]) for item in payload["redundant_indexes"]}
    assert shapes == REGISTERED_REDUNDANT_SHAPES, (
        "a duplicate index shape appeared - remove it in a migration or add "
        f"it to docs/database/DUPLICATION_REGISTER.md: {sorted(shapes)}")
    # Informational: they must not, on their own, fail the gate.
    assert result.returncode == 0


def test_an_out_of_vocabulary_value_is_reported_and_fails_the_gate(audit_db):
    """The detector stays meaningful now the schema also enforces it.

    Since m0039 the CHECK rejects such a value outright, so the probe removes the
    constraint for its duration - a database can legitimately be in that state
    (a constraint dropped for maintenance, or added NOT VALID and never
    validated) - inserts the value, and asserts the audit names it and exits 1.
    `finally` deletes the row and re-runs the migration to restore the
    constraint, so the shared test database is left exactly as it was found.
    """
    import importlib

    m0039 = importlib.import_module("database.migrations.m0039_vocabulary_constraints")
    conn = connect(audit_db)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS ck_jobs_status")
            cur.execute("INSERT INTO jobs (job_id, job_type, status)"
                        " VALUES (%s, %s, %s)", ("AUDITBAD", "import", "nope"))
        result = _audit(audit_db, "--json")
        payload = json.loads(result.stdout)
        found = [v for v in payload["vocabularies"]
                 if v.get("table") == "jobs" and v.get("column") == "status"
                 and v.get("count")]
        assert found, "the audit did not notice an out-of-vocabulary job status"
        assert found[0]["count"] == 1
        assert result.returncode == 1
    finally:
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE job_id = %s", ("AUDITBAD",))
        m0039.upgrade(conn)
        conn.commit()
        conn.close()


def test_the_vocabulary_checks_no_longer_find_anything_on_a_clean_database(audit_db):
    """m0039 made the four vocabulary columns impossible to violate."""
    payload = json.loads(_audit(audit_db, "--json").stdout)
    assert [v for v in payload["vocabularies"] if v.get("count")] == []
    assert all(v.get("allowed") for v in payload["vocabularies"])
