"""Build the per-ingestion-batch report from a finished run or job.

The report is scoped to one intake: the source and side that classified it,
the outcome counts the engine recorded, and the files that were stored in
that run (path ids collected during ingest, or recovered from a watermark
plus source/side). Categories, analyst labels, keywords, signals and places
are read from those files only.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

import psycopg2.extras

from core.reporting.ingestion_template import format_text, render_ingestion_batch
from pipeline.progress_ledger import classify_result

FILE_LIST_CAP = 2000
PATH_ID_CAP = 20000
TERM_CAP = 2000

#: processing_status on paths → the four outcome columns the report shows.
STATUS_TO_OUTCOME = {
    "processed": "processed",
    "partially_processed": "processed",
    "failed": "failed",
    "skipped": "skipped",
    "unsupported": "skipped",
    "discovered": "other",
    "queued": "other",
    "processing": "other",
    "retrying": "other",
}


def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_ids(raw: Sequence[Any], *, cap: int = PATH_ID_CAP) -> List[int]:
    seen = set()
    out: List[int] = []
    for item in raw:
        value = _int(item)
        if value is None or value <= 0 or value in seen:
            continue
        seen.add(value)
        out.append(value)
        if len(out) >= cap:
            break
    return out


def collect_path_ids(results: Optional[Sequence[Any]]) -> List[int]:
    ids: List[int] = []
    for item in results or ():
        if not isinstance(item, dict):
            continue
        ids.append(item.get("database_path_id") or item.get("path_id"))
    return normalize_ids(ids)


def collect_type_outcomes(results: Optional[Sequence[Any]]) -> Dict[str, Dict[str, int]]:
    by_type: Dict[str, Dict[str, int]] = {}
    for item in results or ():
        if not isinstance(item, dict):
            continue
        file_type = _result_type(item)
        outcome = classify_result(item)
        bucket = by_type.setdefault(file_type, defaultdict(int))
        bucket[outcome] += 1
        bucket["total"] += 1
    return {name: dict(counts) for name, counts in by_type.items()}


def _result_type(result: Dict[str, Any]) -> str:
    meta = result.get("Metadata") or result.get("metadata") or {}
    path = (
        meta.get("path")
        or result.get("file_path")
        or result.get("path")
        or result.get("file_name")
        or ""
    )
    ext = Path(str(path)).suffix.lower().lstrip(".")
    if ext:
        return ext
    declared = result.get("file_type") or meta.get("file_type")
    if declared:
        return str(declared).lower().lstrip(".")
    return "unknown"


def _open_connection():
    try:
        from Api.utils.utils import get_connection

        return get_connection(), True
    except Exception:
        from database import get_postgres_connection

        return get_postgres_connection(), False


def _close_connection(conn, borrowed: bool) -> None:
    if conn is None:
        return
    try:
        if borrowed:
            from Api.utils.utils import return_connection

            return_connection(conn)
        else:
            conn.close()
    except Exception:
        pass


def path_watermark(conn=None) -> Optional[int]:
    own = conn is None
    borrowed = False
    if own:
        try:
            conn, borrowed = _open_connection()
        except Exception:
            return None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(id), 0) FROM paths")
            row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return None
    finally:
        if own:
            _close_connection(conn, borrowed)


def _ids_after_watermark(cur, watermark: int, source: str, side: str) -> List[int]:
    cur.execute(
        """
        SELECT p.id
        FROM paths p
        JOIN hash_contexts hc ON hc.id = p.context_id
        JOIN sources s ON s.id = hc.source_id
        JOIN sides d ON d.id = hc.side_id
        WHERE p.id > %s AND s.name = %s AND d.name = %s
        ORDER BY p.id
        LIMIT %s
        """,
        (int(watermark), source, side, PATH_ID_CAP),
    )
    return [int(row[0]) for row in cur.fetchall()]


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _like_prefix(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _path_match_sql(path: Optional[str]) -> Tuple[str, List[Any]]:
    raw = str(path or "").strip()
    if not raw:
        return "", []
    variants = []
    for item in (raw, raw.replace("\\", "/"), raw.replace("/", "\\")):
        if item and item not in variants:
            variants.append(item)
        trimmed = item.rstrip("\\/")
        if trimmed and trimmed not in variants:
            variants.append(trimmed)
    clauses = []
    params: List[Any] = []
    for item in variants:
        clauses.append("p.file_path = %s")
        params.append(item)
        clauses.append("p.file_path LIKE %s ESCAPE '\\'")
        params.append(_like_prefix(item))
    return " AND (" + " OR ".join(clauses) + ")", params


def _ids_in_window(
    cur,
    source: str,
    side: str,
    started: Any,
    finished: Any,
    path: Optional[str] = None,
    *,
    require_timestamp: bool = True,
) -> List[int]:
    start = _parse_dt(started)
    end = _parse_dt(finished)
    if start is None and end is None:
        return []
    if start is None:
        start = end
    if end is None:
        end = datetime.now(timezone.utc)
    lo = start - timedelta(minutes=2)
    hi = end + timedelta(minutes=5)
    extra_sql, extra_params = _path_match_sql(path)
    if require_timestamp:
        where_time = (
            "p.status_updated_at IS NOT NULL "
            "AND p.status_updated_at >= %s AND p.status_updated_at <= %s"
        )
        params: List[Any] = [source, side, lo, hi]
    else:
        where_time = "p.date_creation >= %s AND p.date_creation <= %s"
        params = [source, side, lo.date(), hi.date()]
    cur.execute(
        f"""
        SELECT p.id
        FROM paths p
        JOIN hash_contexts hc ON hc.id = p.context_id
        JOIN sources s ON s.id = hc.source_id
        JOIN sides d ON d.id = hc.side_id
        WHERE s.name = %s AND d.name = %s
          AND ({where_time})
          {extra_sql}
        ORDER BY p.id
        LIMIT %s
        """,
        (*params, *extra_params, PATH_ID_CAP),
    )
    return [int(row[0]) for row in cur.fetchall()]


def _ids_by_path_prefix(cur, source: str, side: str, path: str) -> List[int]:
    extra_sql, extra_params = _path_match_sql(path)
    if not extra_sql:
        return []
    cur.execute(
        f"""
        SELECT p.id
        FROM paths p
        JOIN hash_contexts hc ON hc.id = p.context_id
        JOIN sources s ON s.id = hc.source_id
        JOIN sides d ON d.id = hc.side_id
        WHERE s.name = %s AND d.name = %s
          {extra_sql}
        ORDER BY p.id
        LIMIT %s
        """,
        (source, side, *extra_params, PATH_ID_CAP),
    )
    return [int(row[0]) for row in cur.fetchall()]


def recover_path_ids(
    cur,
    *,
    source: Optional[str],
    side: Optional[str],
    watermark: Any = None,
    started: Any = None,
    finished: Any = None,
    path: Optional[str] = None,
) -> Tuple[List[int], str]:
    """Bind a historical job to the paths it stored.

    Order: watermark (new jobs), then the job time window, then the calendar
    date plus intake path, then the intake path under this source and side.
    """
    source = (source or "").strip()
    side = (side or "").strip()
    if watermark is not None and source and side:
        try:
            mark = int(watermark)
        except (TypeError, ValueError):
            mark = None
        if mark is not None:
            found = _ids_after_watermark(cur, mark, source, side)
            if found:
                return found, "watermark"
    if source and side and (started or finished):
        found = _ids_in_window(
            cur, source, side, started, finished, path, require_timestamp=True)
        if found:
            return found, "time_window"
        found = _ids_in_window(
            cur, source, side, started, finished, path, require_timestamp=False)
        if found:
            return found, "date_and_path"
    if source and side and path:
        found = _ids_by_path_prefix(cur, source, side, str(path))
        if found:
            return found, "path_prefix"
    return [], "none"


def attach_batch_identity(result, request) -> Dict[str, Any]:
    """Stamp path ids and per-type outcomes onto the result for later reports."""
    path_ids = collect_path_ids(getattr(result, "results", None))
    type_outcomes = collect_type_outcomes(getattr(result, "results", None))
    watermark = getattr(result, "path_watermark", None)
    source = getattr(request, "source", "") or ""
    side = getattr(request, "side", "") or ""
    if watermark is not None and source and side:
        conn = None
        borrowed = False
        try:
            conn, borrowed = _open_connection()
            with conn.cursor() as cur:
                recovered = _ids_after_watermark(cur, int(watermark), source, side)
            conn.rollback()
            path_ids = normalize_ids(list(path_ids) + recovered)
        except Exception:
            pass
        finally:
            _close_connection(conn, borrowed)
    payload = {
        "path_ids": path_ids,
        "path_watermark": watermark,
        "type_outcomes": type_outcomes,
        "source": source,
        "side": side,
        "path": getattr(request, "path", None),
    }
    payload["recovery"] = "stored" if path_ids else "none"
    if hasattr(result, "batch_report"):
        result.batch_report = payload
    stats = getattr(result, "stats", None)
    if isinstance(stats, dict):
        stats["batch_path_ids"] = path_ids
        stats["batch_type_outcomes"] = type_outcomes
        stats["batch_path_watermark"] = watermark
    return payload


def document_from_parts(
    *,
    identity: Dict[str, Any],
    counts: Dict[str, Any],
    type_outcomes: Optional[Dict[str, Dict[str, int]]] = None,
    path_ids: Optional[Sequence[Any]] = None,
    errors: Optional[Sequence[str]] = None,
    warnings: Optional[Sequence[str]] = None,
    notes: Optional[Sequence[str]] = None,
    conn=None,
) -> Dict[str, Any]:
    ids = normalize_ids(path_ids or ())
    db = _load_batch_rows(conn, ids) if ids else {}
    types = _merge_types(type_outcomes or {}, db.get("types") or [])
    counts = dict(counts)
    if types:
        counts["file_types"] = len(types)
    else:
        counts.setdefault("file_types", 0)
    counts["files_in_report"] = db.get("file_count", len(ids))
    files = db.get("files") or []
    counts["files_listed"] = len(files)
    identity = dict(identity)
    notes = list(notes or ())
    recovery = identity.get("recovery")
    if recovery == "none" and not ids:
        notes.append(
            "File binding: counts are available; individual files could not be bound"
        )
    return {
        "title": "Ingestion Batch Report",
        "identity": identity,
        "counts": counts,
        "types": types,
        "statuses": db.get("statuses") or [],
        "categories": db.get("categories") or [],
        "category_labels": db.get("category_labels") or [],
        "keywords": db.get("keywords") or [],
        "signals": db.get("signals") or [],
        "places": db.get("places") or [],
        "files": files,
        "errors": list(errors or ())[:200],
        "warnings": list(warnings or ())[:200],
        "notes": notes,
    }


def counts_from_stats(stats: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    stats = stats or {}
    return {
        "files_total": stats.get("files_total") or stats.get("files_discovered")
        or stats.get("total_files"),
        "files_processed": stats.get("files_processed") or stats.get("files_done"),
        "files_succeeded": stats.get("files_succeeded") or stats.get("files_completed"),
        "files_stored": stats.get("files_stored"),
        "files_failed": stats.get("files_failed"),
        "files_skipped": stats.get("files_skipped"),
        "files_duplicates": stats.get("files_duplicates") or stats.get("duplicates"),
        "files_unsupported": stats.get("files_unsupported"),
        "files_retryable": stats.get("files_retryable"),
        "files_locked": stats.get("files_locked"),
        "files_cancelled": stats.get("files_cancelled"),
        "files_nested": stats.get("files_nested"),
        "containers_opened": stats.get("containers_opened"),
        "bytes_processed": stats.get("bytes_processed"),
    }


def document_from_result(result, request) -> Dict[str, Any]:
    batch = getattr(result, "batch_report", None) or attach_batch_identity(result, request)
    identity = {
        "source": getattr(request, "source", None) or batch.get("source"),
        "side": getattr(request, "side", None) or batch.get("side"),
        "path": getattr(request, "path", None) or batch.get("path"),
        "started_at": getattr(result, "started_at", None),
        "finished_at": getattr(result, "finished_at", None),
        "job_id": getattr(result, "job_id", None),
    }
    return document_from_parts(
        identity=identity,
        counts=counts_from_stats(getattr(result, "stats", None)),
        type_outcomes=batch.get("type_outcomes"),
        path_ids=batch.get("path_ids"),
        errors=getattr(result, "errors", None),
        warnings=getattr(result, "warnings", None),
    )


def document_from_job(job: Dict[str, Any], conn=None, *,
                      persist: bool = True) -> Dict[str, Any]:
    options = job.get("options") or {}
    summary = job.get("result_summary") or {}
    stats = job.get("stats") or {}
    batch = dict(summary.get("batch_report") or {})
    if not batch:
        batch = {
            "path_ids": stats.get("batch_path_ids") or [],
            "type_outcomes": stats.get("batch_type_outcomes") or {},
            "path_watermark": stats.get("batch_path_watermark"),
            "source": options.get("source") or job.get("source"),
            "side": options.get("side"),
            "path": options.get("path"),
        }
    source = batch.get("source") or options.get("source") or job.get("source")
    side = batch.get("side") or options.get("side")
    intake_path = batch.get("path") or options.get("path")
    path_ids = normalize_ids(batch.get("path_ids") or ())
    recovery = "stored" if path_ids else "none"
    need_db = True
    own = conn is None and need_db
    borrowed = False
    if own:
        try:
            conn, borrowed = _open_connection()
        except Exception:
            conn, borrowed, own = None, False, False
    try:
        if conn is not None and not path_ids:
            try:
                with conn.cursor() as cur:
                    path_ids, recovery = recover_path_ids(
                        cur,
                        source=source,
                        side=side,
                        watermark=batch.get("path_watermark"),
                        started=job.get("started_at"),
                        finished=job.get("completed_at"),
                        path=intake_path,
                    )
                conn.rollback()
            except Exception:
                path_ids, recovery = [], "none"
                try:
                    conn.rollback()
                except Exception:
                    pass
        try:
            document = document_from_parts(
                identity={
                    "source": source,
                    "side": side,
                    "path": intake_path,
                    "job_id": job.get("job_id"),
                    "started_at": _iso(job.get("started_at")),
                    "finished_at": _iso(job.get("completed_at")),
                    "created_by": job.get("created_by"),
                    "recovery": recovery,
                    "html_path": batch.get("html_path"),
                },
                counts=counts_from_stats(stats) if stats else counts_from_stats(summary),
                type_outcomes=batch.get("type_outcomes") or {},
                path_ids=path_ids,
                errors=job.get("errors"),
                warnings=job.get("warnings"),
                conn=conn,
            )
        except Exception:
            logger.exception(
                "Batch report database sections failed for job %s; "
                "rendering counts without bound files",
                job.get("job_id"),
            )
            document = document_from_parts(
                identity={
                    "source": source,
                    "side": side,
                    "path": intake_path,
                    "job_id": job.get("job_id"),
                    "started_at": _iso(job.get("started_at")),
                    "finished_at": _iso(job.get("completed_at")),
                    "created_by": job.get("created_by"),
                    "recovery": recovery,
                    "html_path": batch.get("html_path"),
                },
                counts=counts_from_stats(stats) if stats else counts_from_stats(summary),
                type_outcomes=batch.get("type_outcomes") or {},
                path_ids=[],
                errors=job.get("errors"),
                warnings=job.get("warnings"),
            )
    finally:
        if own:
            try:
                conn.rollback()
            except Exception:
                pass
            _close_connection(conn, borrowed)
    if persist and job.get("job_id") and (
            (recovery != "stored" and path_ids) or not batch.get("html_path")):
        persist_job_batch_report(
            str(job["job_id"]),
            {
                "path_ids": path_ids,
                "path_watermark": batch.get("path_watermark"),
                "type_outcomes": batch.get("type_outcomes") or {},
                "source": source,
                "side": side,
                "path": intake_path,
                "recovery": recovery,
                "html_path": batch.get("html_path"),
            },
            document=document,
        )
    return document


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _blob_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _load_batch_rows(conn, path_ids: Sequence[int]) -> Dict[str, Any]:
    if not path_ids:
        return {}
    own = conn is None
    borrowed = False
    if own:
        conn, borrowed = _open_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            files = _safe_query(cur, "files", _query_files, path_ids, [])
            types = _safe_query(cur, "types", _query_types, path_ids, [])
            statuses = _safe_query(cur, "statuses", _query_statuses, path_ids, [])
            categories = _safe_query(cur, "categories", _query_categories, path_ids, [])
            labels = _safe_query(cur, "labels", _query_labels, path_ids, [])
            keywords = _safe_query(cur, "keywords", _query_keywords, path_ids, [])
            signals = _safe_query(cur, "signals", _query_signals, path_ids, [])
            places = _safe_query(cur, "places", _query_places, path_ids, [])
        if own:
            conn.rollback()
        return {
            "files": files,
            "file_count": len(files) if len(files) < FILE_LIST_CAP else _count_files(conn, path_ids),
            "types": types,
            "statuses": statuses,
            "categories": categories,
            "category_labels": labels,
            "keywords": keywords,
            "signals": signals,
            "places": places,
        }
    finally:
        if own:
            _close_connection(conn, borrowed)


def _safe_query(cur, name: str, fn, path_ids: Sequence[int], default):
    try:
        return fn(cur, path_ids)
    except Exception:
        logger.exception("Batch report query failed: %s", name)
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return default


def _count_files(conn, path_ids: Sequence[int]) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM paths WHERE id = ANY(%s)", (list(path_ids),))
        row = cur.fetchone()
    return int(row[0]) if row else 0


def _query_files(cur, path_ids: Sequence[int]) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT p.id AS path_id, p.file_name, p.file_path, p.file_type, p.file_size,
               p.file_status, p.processing_status, p.file_date, p.date_creation
        FROM paths p
        WHERE p.id = ANY(%s)
        ORDER BY p.file_name, p.id
        LIMIT %s
        """,
        (list(path_ids), FILE_LIST_CAP),
    )
    return [dict(row) for row in cur.fetchall()]


def _outcomes_from_status_rows(rows: Sequence[Any]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, int]] = {}
    for row in rows:
        if isinstance(row, dict):
            name = row.get("file_type")
            status = row.get("processing_status")
            count = row.get("n") or row.get("count") or 0
        else:
            name, status, count = row[0], row[1], row[2]
        key = str(name or "unknown").lower().lstrip(".")
        bucket = merged.setdefault(key, {
            "file_type": key, "total": 0, "processed": 0, "failed": 0,
            "skipped": 0, "other": 0,
        })
        outcome = STATUS_TO_OUTCOME.get(str(status or "").lower(), "other")
        n = int(count or 0)
        bucket[outcome] += n
        bucket["total"] += n
    return list(merged.values())


def _query_types(cur, path_ids: Sequence[int]) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT LOWER(COALESCE(NULLIF(p.file_type, ''), 'unknown')) AS file_type,
               p.processing_status,
               COUNT(*) AS n
        FROM paths p
        WHERE p.id = ANY(%s)
        GROUP BY 1, 2
        """,
        (list(path_ids),),
    )
    return _outcomes_from_status_rows(cur.fetchall())


def _query_statuses(cur, path_ids: Sequence[int]) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT COALESCE(NULLIF(p.processing_status, ''), 'unknown') AS status,
               COUNT(*) AS count
        FROM paths p
        WHERE p.id = ANY(%s)
        GROUP BY 1
        ORDER BY count DESC, status
        """,
        (list(path_ids),),
    )
    return [dict(row) for row in cur.fetchall()]


def _query_categories(cur, path_ids: Sequence[int]) -> List[Dict[str, Any]]:
    # `words_paths` was renamed to `words_hashs` in m0011, when content-derived
    # data became keyed by the canonical content (hash) instead of the path:
    # the old query referenced a table that no longer exists, so every batch
    # report logged "Batch report query failed: categories" and rendered an
    # empty categories section. The join now walks paths -> hash_contexts ->
    # words_hashs, the same shape `_query_keywords` below has used since.
    cur.execute(
        """
        SELECT w.word AS name,
               COUNT(DISTINCT p.id) AS file_count,
               COALESCE(SUM(wp.word_count), 0) AS occurrence_count
        FROM paths p
        JOIN hash_contexts hc ON hc.id = p.context_id
        JOIN words_hashs wp ON wp.hash_id = hc.hash_id
        JOIN words_categorys wc ON wc.word_id = wp.word_id
        JOIN categorys c ON c.id = wc.category_id
        JOIN words w ON w.id = c.word_id
        WHERE p.id = ANY(%s)
        GROUP BY w.word
        ORDER BY file_count DESC, w.word
        LIMIT %s
        """,
        (list(path_ids), TERM_CAP),
    )
    return [dict(row) for row in cur.fetchall()]


def _query_labels(cur, path_ids: Sequence[int]) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT ac.name, ac.description,
               COUNT(DISTINCT afc.path_id) AS file_count
        FROM analyst_file_categories afc
        JOIN analyst_categories ac ON ac.id = afc.category_id
        WHERE afc.path_id = ANY(%s)
        GROUP BY ac.id, ac.name, ac.description
        ORDER BY file_count DESC, ac.name
        LIMIT %s
        """,
        (list(path_ids), TERM_CAP),
    )
    return [dict(row) for row in cur.fetchall()]


def _query_keywords(cur, path_ids: Sequence[int]) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT k.keyword, cat.word AS category,
               COUNT(DISTINCT p.id) AS file_count,
               COALESCE(SUM(kh.word_count), 0) AS hits
        FROM paths p
        JOIN hash_contexts hc ON hc.id = p.context_id
        JOIN keywords_hashs kh ON kh.hash_id = hc.hash_id
        JOIN keywords k ON k.id = kh.keyword_id
        LEFT JOIN categorys c ON c.id = k.category_id
        LEFT JOIN words cat ON cat.id = c.word_id
        WHERE p.id = ANY(%s)
        GROUP BY k.id, k.keyword, cat.word
        ORDER BY file_count DESC, hits DESC
        LIMIT %s
        """,
        (list(path_ids), TERM_CAP),
    )
    rows = []
    for row in cur.fetchall():
        item = dict(row)
        item["keyword"] = _blob_text(item.get("keyword"))
        rows.append(item)
    return rows


def _query_signals(cur, path_ids: Sequence[int]) -> List[Dict[str, Any]]:
    try:
        cur.execute(
            """
            SELECT cs.detector, cs.signal_type, cs.resolution, COUNT(*) AS count
            FROM paths p
            JOIN hash_contexts hc ON hc.id = p.context_id
            JOIN content_signals cs ON cs.hash_id = hc.hash_id
            WHERE p.id = ANY(%s)
            GROUP BY cs.detector, cs.signal_type, cs.resolution
            ORDER BY count DESC, cs.detector, cs.signal_type
            LIMIT %s
            """,
            (list(path_ids), TERM_CAP),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []


def _query_places(cur, path_ids: Sequence[int]) -> List[Dict[str, Any]]:
    try:
        cur.execute(
            """
            SELECT cs.value AS place,
                   COUNT(DISTINCT p.id) AS file_count,
                   COUNT(*) AS mentions
            FROM paths p
            JOIN hash_contexts hc ON hc.id = p.context_id
            JOIN content_signals cs ON cs.hash_id = hc.hash_id
            WHERE p.id = ANY(%s)
              AND cs.detector = 'places'
              AND cs.signal_type IN ('place', 'geo', 'location', 'place_mention')
            GROUP BY cs.value
            ORDER BY mentions DESC, cs.value
            LIMIT %s
            """,
            (list(path_ids), TERM_CAP),
        )
        rows = [dict(row) for row in cur.fetchall()]
        if rows:
            return rows
    except Exception:
        pass
    try:
        # One read path for place mentions: the ``path_geo_mentions`` view,
        # which already unions the signal-derived places with the preserved
        # m0015 rows (only for content no places run has covered). Reading the
        # legacy table by name would be a second access path to the same
        # entity - and would surface rows the view deliberately hides once a
        # places run exists.
        cur.execute(
            """
            SELECT gm.place_name AS place,
                   COUNT(DISTINCT p.id) AS file_count,
                   COALESCE(SUM(gm.mention_count), 0) AS mentions
            FROM paths p
            JOIN hash_contexts hc ON hc.id = p.context_id
            JOIN path_geo_mentions gm ON gm.hash_id = hc.hash_id
            WHERE p.id = ANY(%s)
            GROUP BY gm.place_name
            ORDER BY mentions DESC, gm.place_name
            LIMIT %s
            """,
            (list(path_ids), TERM_CAP),
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []


def _merge_types(
    outcomes: Dict[str, Dict[str, int]],
    stored: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, int]] = {}
    for name, counts in (outcomes or {}).items():
        key = str(name or "unknown").lower().lstrip(".")
        bucket = merged.setdefault(key, {
            "file_type": key, "total": 0, "processed": 0, "failed": 0,
            "skipped": 0, "other": 0,
        })
        processed = int(counts.get("completed") or counts.get("processed") or 0)
        failed = int(counts.get("failed") or 0)
        skipped = int(counts.get("skipped") or 0)
        other = 0
        for outcome, value in counts.items():
            if outcome in ("total", "completed", "processed", "failed", "skipped"):
                continue
            other += int(value or 0)
        bucket["processed"] += processed
        bucket["failed"] += failed
        bucket["skipped"] += skipped
        bucket["other"] += other
        bucket["total"] += int(counts.get("total") or (processed + failed + skipped + other))
    for row in stored:
        key = str(row.get("file_type") or "unknown").lower().lstrip(".")
        stored_row = {
            "file_type": key,
            "total": int(row.get("total") or 0),
            "processed": int(row.get("processed") or 0),
            "failed": int(row.get("failed") or 0),
            "skipped": int(row.get("skipped") or 0),
            "other": int(row.get("other") or 0),
        }
        if stored_row["total"] == 0:
            stored_row["total"] = (
                stored_row["processed"] + stored_row["failed"]
                + stored_row["skipped"] + stored_row["other"]
            )
        if key not in merged:
            merged[key] = stored_row
            continue
        bucket = merged[key]
        if bucket["total"] == 0 and stored_row["total"]:
            merged[key] = stored_row
            continue
        stored_total = stored_row["total"]
        if bucket["processed"] < stored_total and not (
                bucket["failed"] or bucket["skipped"] or bucket["other"]):
            extra = stored_total - bucket["processed"]
            bucket["processed"] += extra
            bucket["total"] += extra
    return sorted(merged.values(), key=lambda r: (-int(r["total"]), r["file_type"]))


def _language_reader(language: Optional[str]):
    from core.reporting.i18n import reader_for

    code = (language or "en").split("_")[0].split("-")[0]
    try:
        return reader_for(code)
    except ValueError:
        return reader_for("en")


def render_html(document: Dict[str, Any], *, interactive: bool = False,
                auto_print: bool = False, language: str = "en") -> bytes:
    return render_ingestion_batch(
        document, _language_reader(language),
        interactive=interactive, auto_print=auto_print)


def render_text(document: Dict[str, Any], *, language: str = "en") -> str:
    return format_text(document, _language_reader(language))


def write_html(document: Dict[str, Any], destination: str,
               *, language: str = "en") -> str:
    path = Path(destination)
    if path.suffix.lower() != ".html":
        path = path.with_suffix(".html")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_html(document, interactive=True, language=language))
    return str(path)


def persist_result_report(result, request, *, language: str = "en") -> Optional[str]:
    """Write the printable HTML for a finished ingest and stamp its path."""
    try:
        document = document_from_result(result, request)
        path = write_html(
            document, default_html_path(document.get("identity") or {}),
            language=language)
        if isinstance(getattr(result, "batch_report", None), dict):
            result.batch_report["html_path"] = path
        return path
    except Exception:
        return None


def persist_job_batch_report(
    job_id: str,
    batch: Dict[str, Any],
    document: Optional[Dict[str, Any]] = None,
    *,
    language: str = "en",
) -> Optional[str]:
    """Store recovered path ids and the HTML path on the job record."""
    try:
        from services.jobs.manager import JobManager

        manager = JobManager.get_instance()
        repo = getattr(manager, "repo", None)
        if repo is None or not hasattr(repo, "update_fields"):
            return None
        current = manager.get(job_id)
        if current is None:
            return None
        html_path = batch.get("html_path")
        if document is not None and not html_path:
            try:
                html_path = write_html(
                    document,
                    default_html_path(document.get("identity") or {}),
                    language=language,
                )
            except Exception:
                html_path = None
        summary = dict(current.get("result_summary") or {})
        stored = dict(summary.get("batch_report") or {})
        stored.update({
            "path_ids": normalize_ids(batch.get("path_ids") or stored.get("path_ids") or ()),
            "path_watermark": batch.get("path_watermark", stored.get("path_watermark")),
            "type_outcomes": batch.get("type_outcomes") or stored.get("type_outcomes") or {},
            "source": batch.get("source") or stored.get("source"),
            "side": batch.get("side") or stored.get("side"),
            "path": batch.get("path") or stored.get("path"),
            "recovery": batch.get("recovery") or stored.get("recovery"),
        })
        if html_path:
            stored["html_path"] = html_path
            if document is not None:
                document.setdefault("identity", {})["html_path"] = html_path
        summary["batch_report"] = stored
        repo.update_fields(job_id, {"result_summary": summary})
        return html_path
    except Exception:
        return None


def default_html_path(identity: Dict[str, Any]) -> str:
    from core.app_paths import get_data_root

    folder = get_data_root() / "reports" / "ingestion"
    folder.mkdir(parents=True, exist_ok=True)
    job = identity.get("job_id") or "cli"
    source = identity.get("source") or "source"
    side = identity.get("side") or "side"
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-"
                   for ch in f"{job}_{source}_{side}")
    return str(folder / f"batch-{safe}.html")
