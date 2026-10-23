"""
Priority derivation for notifications.

A notification's priority is derived from its evidence, never chosen by hand.
This module contains the single function that maps a signal (temporal or
place) and a reference date to a priority level.
"""

from datetime import date, timedelta
from core.monitoring.notification_service import NotificationPriority


# Rule version for audit trail - matches the SQL function's expected constant.
PRIORITY_RULE_VERSION = "priority-1"

# A date within this many days is "imminent".
IMMINENT_DAYS = 7


def imminent_sql(date_from_col: str, date_to_col: str) -> str:
    """SQL fragment: true when the signal's date range intersects the
    next IMMINENT_DAYS window from the reference date (passed as a
    parameter in the surrounding query)."""
    return (
        f"({date_from_col} IS NOT NULL AND {date_from_col} <= %s + INTERVAL '{IMMINENT_DAYS} days' "
        f"AND {date_to_col} >= %s)"
    )


def priority_from_signal(signal: dict, reference_date: date) -> NotificationPriority:
    """Derive priority from a temporal signal and a reference date.

    The signal dict contains at least ``signal_type``, ``date_from``,
    ``date_to`` (both ``date`` or ISO strings), ``confidence``
    (``high``/``medium``/``low``/None), and optionally ``text_orientation``.

    Priority rules (core.monitoring.priority):
    1. CRITICAL: confidence='high' AND date is imminent (within IMMINENT_DAYS)
    2. HIGH: confidence='high' OR (confidence='medium' AND date is imminent)
    3. MEDIUM: confidence='medium' OR (confidence='low' AND date is imminent)
    4. LOW: everything else (including no date, no confidence)
    """
    # Parse dates if they're strings
    date_from = signal.get('date_from')
    date_to = signal.get('date_to')
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)
    if isinstance(date_to, str):
        date_to = date.fromisoformat(date_to)

    confidence = signal.get('confidence')

    # Imminent window
    imminent_end = reference_date + timedelta(days=IMMINENT_DAYS)
    is_imminent = (date_from is not None and date_from <= imminent_end
                   and date_to is not None and date_to >= reference_date)

    if confidence == 'high' and is_imminent:
        return NotificationPriority.CRITICAL
    if confidence == 'high':
        return NotificationPriority.HIGH
    if confidence == 'medium' and is_imminent:
        return NotificationPriority.HIGH
    if confidence == 'medium':
        return NotificationPriority.MEDIUM
    if confidence == 'low' and is_imminent:
        return NotificationPriority.MEDIUM
    return NotificationPriority.LOW


def priority_from_summary(summary: dict, reference_date: date) -> tuple[NotificationPriority, str]:
    """Derive priority from a group summary (used by scenario/rule delivery).

    ``summary`` has keys: ``highest_confidence`` (high/medium/low/None),
    ``high_and_imminent`` (bool), ``earliest_event_date`` (date/None).

    Returns (priority, basis) where basis is a short string for the manifest.
    """
    highest = summary.get('highest_confidence')
    high_imminent = summary.get('high_and_imminent', False)

    if highest == 'high' and high_imminent:
        return NotificationPriority.CRITICAL, "high confidence + imminent"
    if highest == 'high':
        return NotificationPriority.HIGH, "high confidence"
    if highest == 'medium' and high_imminent:
        return NotificationPriority.HIGH, "medium confidence + imminent"
    if highest == 'medium':
        return NotificationPriority.MEDIUM, "medium confidence"
    if highest == 'low' and high_imminent:
        return NotificationPriority.MEDIUM, "low confidence + imminent"
    return NotificationPriority.LOW, "low confidence or no date"