"""Widen ``content_signals.resolution`` for the identifiers detector.

``core/detection/identifiers_intel.py`` (email, phone, IPv4, IPv6, URL) declares
``RESOLUTIONS = ("literal",)`` and ``services/detection/detectors.py`` registers
it as the third detector - ``Api/routes/signals.py`` documents the three
detectors and ``detection_admin`` reads its status from that registry. The
check constraint added by m0019 was never widened for it, so every identifier
signal failed to store::

    CheckViolation: new row for relation "content_signals" violates check
    constraint "ck_content_signals_resolution"

The detector's run was then recorded as failed and nothing was persisted, so
the feature could not store a single email, phone, IP or URL.

The other constraints still hold for the new value: 'literal' carries no date
range (``ck_content_signals_resolved_has_range`` requires one only for
absolute/approximate/document_relative) and is not 'identified', so the
place-mention rule is untouched.
"""

version = "0037"
name = "identifier_signal_resolution"

#: Every value the detectors can emit today: temporal, place, identifier.
_ALLOWED = ("absolute", "approximate", "document_relative", "ambiguous",
            "unresolved", "identified", "literal")

#: What m0019 left behind - the set to restore on downgrade.
_PREVIOUS = ("absolute", "approximate", "document_relative", "ambiguous",
             "unresolved", "identified")


def _replace_constraint(cur, values) -> None:
    cur.execute("ALTER TABLE content_signals"
                " DROP CONSTRAINT IF EXISTS ck_content_signals_resolution")
    allowed = ", ".join("'" + value + "'" for value in values)
    cur.execute("ALTER TABLE content_signals ADD CONSTRAINT ck_content_signals_resolution"
                f" CHECK (resolution IN ({allowed}))")


def upgrade(conn) -> None:
    with conn.cursor() as cur:
        _replace_constraint(cur, _ALLOWED)


def downgrade(conn) -> None:
    """Restore the m0019 constraint, dropping what it cannot hold.

    Same convention as m0019's own downgrade: a signal the narrower schema
    cannot describe is removed rather than left to break the constraint, and
    the runs that produced it go with it.
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM content_signals WHERE resolution = 'literal'")
        cur.execute("DELETE FROM content_signal_runs WHERE detector = 'identifiers'")
        _replace_constraint(cur, _PREVIOUS)
