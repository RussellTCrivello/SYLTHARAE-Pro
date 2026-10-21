"""
Notification display formatting - single source of truth for how a
Notification becomes the title/message shown in the UI.
"""

from datetime import date
from core.monitoring.notification_service import Notification, NotificationType


def format_title_message(notification: Notification, _=None) -> tuple[str, str]:
    """Return (title, message) for a notification in the caller's language.

    The optional ``_`` argument is ``flask_babel.gettext`` when called from
    a request context; if absent the raw English strings are used.
    """
    t = notification.type
    meta = notification.metadata or {}

    if t == NotificationType.SIMILAR_FILES:
        file_names = meta.get('file_names', [])
        count = meta.get('duplicate_count', len(file_names))
        names = file_names[:5]
        if len(file_names) > 5:
            names.append(f"... and {len(file_names) - 5} more")
        # Use file_name from metadata (notification no longer has file_name field)
        primary_file = meta.get('file_name') or (file_names[0] if file_names else 'Unknown')
        
        # Check if this is a similarity notification (has similar_count but no duplicate_count)
        if 'similar_count' in meta and 'duplicate_count' not in meta:
            title = f"Similar Files Detected: {primary_file}"
            msg = f"Found {meta['similar_count']} similar file(s) with similarity ≥ {int(meta.get('similarity_threshold', 0.8) * 100)}%"
        else:
            title = f"Duplicate Files Detected: {primary_file}"
            if file_names:
                msg = f"Found {count} duplicate file(s) with the same hash. Files: {', '.join(names)}"
            else:
                msg = f"Found {count} duplicate file(s) with the same hash"
        return title, msg

    if t == NotificationType.FUTURE_DATE:
        event_date = notification.event_date
        date_str = event_date.isoformat() if event_date else "unknown date"
        # Use file_name from metadata (notification no longer has file_name field)
        primary_file = meta.get('file_name') or meta.get('file_names', [''])[0] or 'this file'
        title = f"Future Date Detected: {date_str}"
        msg = f"Date {date_str} found in {primary_file}"
        # Add live countdown
        if event_date:
            from datetime import date as _date
            today = _date.today()
            if event_date >= today:
                days = (event_date - today).days
                if days == 0:
                    msg += " (today)"
                elif days == 1:
                    msg += " (tomorrow)"
                else:
                    msg += f" ({days} days away)"
        return title, msg

    if t == NotificationType.FUTURE_EVENT:
        # Use file_name from metadata (notification no longer has file_name field)
        primary_file = meta.get('file_name') or meta.get('file_names', [''])[0] or 'Unknown'
        title = f"Future Event: {primary_file}"
        msg = meta.get('message', 'A future event was detected.')
        return title, msg

    if t == NotificationType.PROCESSING_COMPLETE:
        title = "Processing Complete"
        msg = meta.get('message', 'File processing has completed.')
        return title, msg

    if t == NotificationType.BATCH_COMPLETE:
        title = "Batch Processing Complete"
        msg = meta.get('message', 'Batch processing has completed.')
        return title, msg

    if t == NotificationType.ERROR:
        title = "Error"
        msg = meta.get('message', 'An error occurred.')
        return title, msg

    if t == NotificationType.WARNING:
        title = "Warning"
        msg = meta.get('message', 'A warning was issued.')
        return title, msg

    if t == NotificationType.INFO:
        title = "Information"
        msg = meta.get('message', 'An informational message.')
        return title, msg

    if t == NotificationType.SCENARIO_OUTCOME:
        title = meta.get('title', 'Scenario Outcome')
        msg = meta.get('message', 'A scenario produced a new outcome.')
        return title, msg

    if t == NotificationType.SCENARIO_STATUS:
        title = meta.get('title', 'Scenario Status')
        msg = meta.get('message', 'A scenario status changed.')
        return title, msg

    # Fallback for any future types
    return notification.title, notification.message


def display_payload(notification: Notification, _=None) -> dict:
    """The complete JSON payload the UI expects for a notification."""
    title, message = format_title_message(notification, _)
    return {
        'id': notification.id,
        'type': notification.type.value,
        'priority': notification.priority.value,
        'title': title,
        'message': message,
        'file_id': notification.file_id,
        'file_name': notification.metadata.get('file_name'),
        'file_path': notification.metadata.get('file_path'),
        'event_date': notification.event_date.isoformat() if notification.event_date else None,
        'metadata': notification.metadata,
        'created_at': notification.created_at.isoformat() if notification.created_at else None,
        'read': notification.read,
        'dismissed': notification.dismissed,
        'recipient_user_id': notification.recipient_user_id,
        'scenario_id': notification.scenario_id,
        'scenario_evaluation_id': notification.scenario_evaluation_id,
        'addressed': notification.recipient_user_id is not None,
    }