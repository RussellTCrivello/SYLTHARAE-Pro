"""Live Full Entry Report: the dedicated printable dossier, without a stored run.

Uses the registered ``entry_content`` datasets (same SQL, same access scope,
same row and character limits) so a preview and a later artifact of the
same criteria describe the same files. The HTML is the dedicated template
(``core.reporting.entry_template``), with interactive print chrome.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Sequence

from core.criteria.access import scope_for
from core.reporting import REGISTRY
from core.reporting.datasets import ENTRY_CONTENT_CHAR_LIMIT
from core.reporting.entry_template import render_entry_dossier
from core.reporting.i18n import available_languages, reader_for
from core.reporting.model import ReportParameterError
from core.reporting.registry import ReportNotFound
from services.reporting.runs import ReportRunError, jsonable

MAX_PREVIEW_IDS = 100


def normalize_ids(raw: Sequence[Any]) -> List[int]:
    seen = set()
    out: List[int] = []
    for item in raw:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        out.append(value)
        if len(out) >= MAX_PREVIEW_IDS:
            break
    return out


def parse_id_query(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    return normalize_ids(part.strip() for part in str(raw).split(","))


def _dataset_block(dataset, cur, bound) -> Dict[str, Any]:
    cur.execute(bound.sql, bound.params)
    names = [d[0] for d in cur.description]
    declared = [c.name for c in dataset.columns]
    if names != declared:
        raise ReportRunError(
            "DATASET_SHAPE",
            f"{dataset.key} returned columns {names}, declared {declared}",
            500,
        )
    fetched = cur.fetchmany(bound.fetch_limit)
    overflow = len(fetched) > dataset.row_limit
    rows = []
    for raw in fetched[:dataset.row_limit]:
        row = {column.name: jsonable(raw[column.name]) for column in dataset.columns}
        rows.append(row)
    return {
        "dataset_key": dataset.key,
        "dataset_fingerprint": dataset.fingerprint(),
        "query_fingerprint": None,
        "semantics": dataset.semantics,
        "row_limit": dataset.row_limit,
        "row_count": len(rows),
        "truncated": overflow,
        "columns": [dict(c.semantic(), label=c.label) for c in dataset.columns],
        "rows": rows,
    }


def preview_document(conn, *, user, path_ids: Sequence[Any],
                     language: str = "en") -> Dict[str, Any]:
    """Build a preview run document for the dedicated template."""
    ids = normalize_ids(path_ids)
    if not ids:
        raise ReportRunError("VALIDATION_FAILED",
                             "at least one file id is required", 400)
    try:
        definition = REGISTRY.report("entry_content")
        entries = REGISTRY.dataset("entry_content.entries@1")
        count = REGISTRY.dataset("entry_content.count@1")
        topic = REGISTRY.help_topic(definition.help_topic)
    except ReportNotFound as exc:
        raise ReportRunError("NOT_FOUND", str(exc), 404) from exc
    try:
        parameters = definition.normalize_parameters({
            "criteria": {"path_ids": ids, "analyst_scope": "all", "unit": "path"},
        })
    except ReportParameterError as exc:
        raise ReportRunError("VALIDATION_FAILED", str(exc), 400) from exc
    scope = scope_for(user)
    bound_entries = entries.bind(parameters, scope)
    bound_count = count.bind(parameters, scope)
    import psycopg2.extras

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        entry_block = _dataset_block(entries, cur, bound_entries)
        count_block = _dataset_block(count, cur, bound_count)
    conn.rollback()
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "preview": True,
        "report": {
            "id": definition.report_id,
            "version": definition.version,
            "title": definition.title,
            "unit": definition.unit,
            "description": definition.description,
            "help_summary": topic.summary if topic else None,
            "layout": definition.layout,
        },
        "run": {
            "report_key": definition.key,
            "id": None,
            "report_id": definition.report_id,
            "report_version": definition.version,
            "preview": True,
            "requester_username": getattr(user, "username", None),
            "requester_role": getattr(user, "role", None),
            "requested_at": now,
        },
        "datasets": [entry_block, count_block],
        "analyses": [],
        "language": language,
        "char_limit": ENTRY_CONTENT_CHAR_LIMIT,
    }


def render_preview(conn, *, user, path_ids: Sequence[Any], language: str = "en",
                   auto_print: bool = False) -> bytes:
    langs = available_languages()
    if language not in langs:
        language = "en" if "en" in langs else sorted(langs)[0]
    document = preview_document(conn, user=user, path_ids=path_ids, language=language)
    content, _notes = render_entry_dossier(
        document, reader_for(language), interactive=True, auto_print=auto_print)
    return content
