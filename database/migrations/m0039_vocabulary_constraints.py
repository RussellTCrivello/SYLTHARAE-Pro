"""Enforce the vocabularies the application writes (DB-7, DB-8).

Four columns hold values that come from a fixed set defined in code, and the
schema did not enforce any of them:

    alerts.type          core/monitoring/notification_service.py::NotificationType
    alerts.priority      core/monitoring/notification_service.py::NotificationPriority
    jobs.status          services/jobs/job_state.py::ALL_STATES
    job_events.event_type services/jobs/job_state.py::EVENT_TYPES

A value outside the set is accepted silently and then never matches a filter, so
the record disappears from the view that is supposed to show it: a notification
whose type is misspelled is invisible in the notification list, a job whose
status is unknown is never picked up by the terminal-state sweep. That is a
whole-record failure mode, and it is exactly the class of defect a CHECK
constraint exists to prevent.

The allowed values are read from those modules at migration time rather than
copied here, so the constraint cannot drift from the code that writes the
column. `EVENT_TYPES` in particular had to be corrected first in
`services/jobs/job_state.py`: it was missing PROGRESS, JOB_PAUSED and FAILED,
which the job manager does write - a CHECK built on the old tuple would have
rejected the application's own events
(`tests/unit/test_job_event_vocabulary.py` now derives the emitted set from the
writer call sites so the two cannot drift again).

**Pre-flight.** Before adding any constraint this migration counts the rows that
would violate it and, if there are any, raises with the offending values listed.
A deployment with drifted data therefore stops here with a readable message
instead of a bare CheckViolation, and nothing is altered. The check and the
`NOT VALID` + `VALIDATE` pair run inside the migration's own transaction, so a
refusal leaves the database exactly as it was.
"""

version = "0039"
name = "vocabulary_constraints"

#: (table, column, constraint, module, attribute) - the vocabulary source is the
#: module that defines it, never a copy of the values.
_CHECKS = (
    ("alerts", "type", "ck_alerts_type",
     "core.monitoring.notification_service", "NotificationType"),
    ("alerts", "priority", "ck_alerts_priority",
     "core.monitoring.notification_service", "NotificationPriority"),
    ("jobs", "status", "ck_jobs_status",
     "services.jobs.job_state", "ALL_STATES"),
    ("job_events", "event_type", "ck_job_events_event_type",
     "services.jobs.job_state", "EVENT_TYPES"),
)

#: How many offending values to name in the refusal message.
_REPORT_LIMIT = 10


def _allowed_values(module_name: str, attribute: str):
    """The vocabulary: an Enum's values, or a plain tuple of strings."""
    module = __import__(module_name, fromlist=[attribute])
    members = getattr(module, attribute)
    if hasattr(members, "__members__"):        # e.g. NotificationType
        return tuple(member.value for member in members)
    return tuple(str(value) for value in members)


def _violations(cur, table: str, column: str, allowed) -> tuple:
    """Distinct stored values outside ``allowed`` (a sample for the message)."""
    placeholders = ", ".join(["%s"] * len(allowed))
    cur.execute(
        f'SELECT "{column}", count(*) FROM "{table}"'
        f' WHERE "{column}" IS NOT NULL AND "{column}" NOT IN ({placeholders})'
        f' GROUP BY "{column}" ORDER BY 2 DESC LIMIT %s',
        (*allowed, _REPORT_LIMIT))
    return cur.fetchall()


def _existing_rows(cur, table: str) -> int:
    cur.execute(f'SELECT count(*) FROM "{table}"')
    return cur.fetchone()[0]


def upgrade(conn) -> None:
    with conn.cursor() as cur:
        for table, column, constraint, module_name, attribute in _CHECKS:
            allowed = _allowed_values(module_name, attribute)
            if not allowed:
                raise RuntimeError(
                    f"{module_name}.{attribute} resolved to no values; refusing"
                    f" to constrain {table}.{column} on an empty vocabulary")

            offenders = _violations(cur, table, column, allowed)
            if offenders:
                listed = ", ".join(f"{value!r} x{count}" for value, count in offenders)
                raise RuntimeError(
                    f"{table}.{column} contains {len(offenders)} value(s) outside"
                    f" {module_name}.{attribute}: {listed}. Reconcile those rows"
                    f" (they are invisible to the application filters) and run"
                    f" this migration again; nothing was changed.")

            # NOT VALID + VALIDATE: adding the constraint does not scan the
            # table, validating does not block writes, and both statements run
            # inside this migration's transaction.
            values = ", ".join("'" + str(value).replace("'", "''") + "'"
                               for value in allowed)
            cur.execute(
                f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{constraint}"')
            cur.execute(
                f'ALTER TABLE "{table}" ADD CONSTRAINT "{constraint}"'
                f' CHECK ("{column}" IN ({values})) NOT VALID')
            cur.execute(f'ALTER TABLE "{table}" VALIDATE CONSTRAINT "{constraint}"')
            rows = _existing_rows(cur, table)
            print(f"  {table}.{column}: {len(allowed)} allowed values,"
                  f" {rows} row(s) validated by {constraint}")


def downgrade(conn) -> None:
    with conn.cursor() as cur:
        for table, _column, constraint, _module, _attribute in _CHECKS:
            cur.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{constraint}"')
