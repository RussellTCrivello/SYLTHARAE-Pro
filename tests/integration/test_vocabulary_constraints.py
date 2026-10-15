"""Integration: m0039 enforces the vocabularies the application writes (DB-7/DB-8).

The columns below hold values from a fixed set defined in code, and the schema
did not enforce any of them: an out-of-vocabulary value was stored silently and
then never matched a filter, so the record vanished from the view meant to show
it. m0039 adds a CHECK per column, generated from the module that defines the
vocabulary.

These tests assert the enforcement and, just as importantly, that the constraint
cannot drift from the code: the allowed values are read back out of
`pg_get_constraintdef` and compared with the enums.
"""

from __future__ import annotations

import importlib
import re

import psycopg2
import pytest

from _seed import connect

pytestmark = pytest.mark.integration

m0039 = importlib.import_module("database.migrations.m0039_vocabulary_constraints")

CONSTRAINTS = {
    ("alerts", "type"): "ck_alerts_type",
    ("alerts", "priority"): "ck_alerts_priority",
    ("jobs", "status"): "ck_jobs_status",
    ("job_events", "event_type"): "ck_job_events_event_type",
}


@pytest.fixture()
def conn(pg_db):
    connection = connect(pg_db)
    yield connection
    connection.close()


def _definition(cur, table, constraint):
    cur.execute(
        "SELECT pg_get_constraintdef(c.oid), c.convalidated"
        " FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid"
        " WHERE t.relname = %s AND c.conname = %s", (table, constraint))
    row = cur.fetchone()
    assert row, f"{constraint} is missing from {table}"
    return row[0], row[1]


def _literals(definition: str):
    return set(re.findall(r"'([^']*)'", definition))


def test_every_vocabulary_constraint_exists_and_is_validated(conn):
    with conn.cursor() as cur:
        for (table, _column), constraint in CONSTRAINTS.items():
            definition, validated = _definition(cur, table, constraint)
            assert "CHECK" in definition
            assert validated is True, f"{constraint} was added NOT VALID and never validated"


def test_the_constraints_match_the_code_vocabulary_exactly(conn):
    """The constraint's allowed set is the module's set - no drift either way."""
    from core.monitoring.notification_service import (NotificationPriority,
                                                      NotificationType)
    from services.jobs import job_state

    expected = {
        ("alerts", "type"): {member.value for member in NotificationType},
        ("alerts", "priority"): {member.value for member in NotificationPriority},
        ("jobs", "status"): set(job_state.ALL_STATES),
        ("job_events", "event_type"): set(job_state.EVENT_TYPES),
    }
    with conn.cursor() as cur:
        for (table, _column), values in expected.items():
                definition, _validated = _definition(cur, table, CONSTRAINTS[(table, _column)])
                assert _literals(definition) == values, (
                    f"{CONSTRAINTS[(table, _column)]} allows"
                    f" {sorted(_literals(definition))}, the code defines"
                    f" {sorted(values)}")


def test_an_out_of_vocabulary_value_is_rejected_by_the_schema(conn):
    with conn.cursor() as cur:
        cases = [
            ("INSERT INTO alerts (type, priority, title, message)"
             " VALUES ('not-a-type', 'low', 't', 'm')", "ck_alerts_type"),
            ("INSERT INTO alerts (type, priority, title, message)"
             " VALUES ('info', 'urgent', 't', 'm')", "ck_alerts_priority"),
            ("INSERT INTO jobs (job_id, job_type, status)"
             " VALUES ('VOCBADJOB', 'import', 'not-a-status')", "ck_jobs_status"),
        ]
        for sql, constraint in cases:
            with pytest.raises(psycopg2.errors.CheckViolation) as caught:
                cur.execute(sql)
            assert caught.value.diag.constraint_name == constraint
            conn.rollback()

        # job_events needs a parent job that satisfies its own vocabulary.
        cur.execute("INSERT INTO jobs (job_id, job_type, status)"
                    " VALUES ('VOCJOB', 'import', 'QUEUED')")
        with pytest.raises(psycopg2.errors.CheckViolation) as caught:
            cur.execute("INSERT INTO job_events (job_id, event_type)"
                        " VALUES ('VOCJOB', 'not-an-event')")
        assert caught.value.diag.constraint_name == "ck_job_events_event_type"
        conn.rollback()


def test_every_value_the_code_defines_is_accepted(conn):
    """A vocabulary constraint must not reject the application's own values."""
    from core.monitoring.notification_service import (NotificationPriority,
                                                      NotificationType)
    from services.jobs import job_state

    with conn.cursor() as cur:
        for index, member in enumerate(NotificationType):
            cur.execute("INSERT INTO alerts (type, priority, title, message)"
                        " VALUES (%s, %s, %s, %s)",
                        (member.value, NotificationPriority.LOW.value,
                         f"probe-{index}", "m"))
        for index, state in enumerate(job_state.ALL_STATES):
            cur.execute("INSERT INTO jobs (job_id, job_type, status)"
                        " VALUES (%s, 'import', %s)", (f"VOC{index}", state))
            for event in job_state.EVENT_TYPES:
                cur.execute("INSERT INTO job_events (job_id, event_type)"
                            " VALUES (%s, %s)", (f"VOC{index}", event))
    conn.rollback()


def test_the_migration_refuses_drifted_data_instead_of_failing_obscurely(conn):
    """Pre-flight: a violating value must stop the migration, change nothing.

    Runs in one transaction: the constraint is dropped and a violating row is
    inserted to simulate a database that drifted, the migration is asked to run
    with a repair, and the refusal must name the offending value. The rollback
    restores the schema and removes the row.
    """
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE jobs DROP CONSTRAINT ck_jobs_status")
        cur.execute("INSERT INTO jobs (job_id, job_type, status)"
                    " VALUES ('VOCDRIFT', 'import', 'not-a-status')")
        with pytest.raises(RuntimeError, match="not-a-status"):
            m0039.upgrade(conn)
    conn.rollback()
    with conn.cursor() as cur:
        definition, validated = _definition(cur, "jobs", "ck_jobs_status")
        assert validated is True
