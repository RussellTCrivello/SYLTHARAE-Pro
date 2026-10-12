"""Dedicated printable template for one ingestion batch.

Source and side open the document. Counts, per-type outcomes, automatic
categories, analyst category labels, keywords, signals and the file list
follow. Interactive chrome (print / auto-print) is only for the live
preview; callers that persist bytes pass ``interactive=False``.
"""

from __future__ import annotations

import html
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_STYLE = (
    ":root{--ink:#1a1a1a;--muted:#5c5c5c;--rule:#c8c4bb;--paper:#f7f4ee;"
    "--band:#efeae0;--accent:#3d4a3a}"
    "html{color-scheme:light}"
    "body.ingest-batch{font-family:system-ui,'Segoe UI','Noto Sans',"
    "'Noto Sans Arabic','Noto Sans Hebrew',sans-serif;"
    "margin:0 auto;padding:1.5rem 1.75rem 3rem;color:var(--ink);"
    "background:#fff;line-height:1.55;max-width:52rem}"
    ".dossier-toolbar{display:flex;justify-content:space-between;align-items:center;"
    "gap:.75rem;flex-wrap:wrap;margin:0 0 1.25rem;padding:.65rem .85rem;"
    "background:var(--band);border:1px solid var(--rule);border-radius:6px;"
    "font-size:.92rem}"
    ".dossier-toolbar button,.dossier-toolbar a.btn{appearance:none;border:1px solid #2f3a2d;"
    "background:var(--accent);color:#fff;padding:.4rem .9rem;border-radius:4px;"
    "font:inherit;cursor:pointer;text-decoration:none}"
    ".kicker{letter-spacing:.18em;text-transform:uppercase;font-size:.72rem;"
    "color:var(--muted);margin:0 0 .35rem}"
    "h1{font-size:1.85rem;font-weight:650;margin:0 0 .45rem;line-height:1.2}"
    "h2{font-size:1.15rem;margin:1.4rem 0 .45rem;page-break-after:avoid}"
    ".lede{margin:.2rem 0 1rem}"
    ".identity{background:var(--paper);border:2px solid var(--ink);padding:.9rem 1.1rem;"
    "margin:0 0 1.2rem}"
    ".identity .pair{display:flex;gap:1.5rem;flex-wrap:wrap}"
    ".identity .pair div{min-width:10rem}"
    ".identity .lbl{font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;"
    "color:var(--muted)}"
    ".identity .val{font-size:1.25rem;font-weight:650}"
    ".cover-meta{font-size:.88rem;color:var(--muted);margin:0 0 1rem}"
    "table.data{border-collapse:collapse;width:100%;font-size:.9rem;margin:.35rem 0 0}"
    "table.data th,table.data td{border:1px solid var(--rule);padding:.32rem .5rem;"
    "text-align:start;vertical-align:top}"
    "table.data th{background:var(--band)}"
    "table.data td.num,table.data th.num{text-align:end;font-variant-numeric:tabular-nums}"
    "dl.meta{display:grid;grid-template-columns:minmax(8rem,12rem) 1fr;gap:.28rem .85rem;"
    "margin:0;font-size:.9rem}"
    "dl.meta dt{margin:0;color:var(--muted);font-weight:600}"
    "dl.meta dd{margin:0;word-break:break-word}"
    ".tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(8.5rem,1fr));"
    "gap:.55rem;margin:.4rem 0 0}"
    ".tile{border:1px solid var(--rule);background:var(--paper);padding:.55rem .7rem}"
    ".tile .n{font-size:1.35rem;font-weight:650;font-variant-numeric:tabular-nums}"
    ".tile .l{font-size:.75rem;color:var(--muted);text-transform:uppercase;"
    "letter-spacing:.06em}"
    ".empty{color:var(--muted);font-style:italic}"
    ".warn{color:#7a3e00;font-weight:600}"
    ".chips{display:flex;flex-wrap:wrap;gap:.35rem;margin:.35rem 0 0}"
    ".chip{border:1px solid var(--rule);background:var(--band);padding:.15rem .5rem;"
    "font-size:.85rem}"
    "@page{margin:14mm 15mm 16mm;size:A4}"
    "@media print{"
    "body.ingest-batch{margin:0;padding:0;max-width:none;color:#000;background:#fff}"
    ".no-print{display:none!important}"
    "a{color:inherit;text-decoration:none}"
    "h2,.identity,.tile{break-inside:avoid}"
    "thead{display:table-header-group}"
    "}"
)


def _e(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _none(text: str) -> str:
    return f'<p class="empty">{_e(text)}</p>'


def _toolbar(t: Any, auto_print: bool) -> str:
    script = (
        '<script>window.addEventListener("load",function(){window.print();});</script>'
        if auto_print else
        '<script>function printDossier(){window.print();}</script>'
    )
    return (
        '<div class="dossier-toolbar no-print">'
        f'<span>{_e(t.gettext("Ingestion batch report — printable dossier"))}</span>'
        f'<button type="button" onclick="printDossier()">{_e(t.gettext("Print"))}</button>'
        f"</div>{script}"
    )


def _tiles(counts: Dict[str, Any], t: Any) -> str:
    order: Sequence[Tuple[str, str]] = (
        ("files_total", "Total files"),
        ("files_processed", "Processed"),
        ("files_stored", "Stored"),
        ("files_failed", "Failed"),
        ("files_skipped", "Skipped"),
        ("files_duplicates", "Duplicates"),
        ("files_unsupported", "Unsupported"),
        ("files_retryable", "Retryable"),
        ("files_locked", "Locked"),
        ("files_cancelled", "Cancelled"),
        ("file_types", "File types"),
        ("files_nested", "Nested"),
        ("containers_opened", "Containers"),
        ("bytes_processed", "Bytes"),
    )
    parts = ['<div class="tiles">']
    for key, label in order:
        if key not in counts or counts[key] is None:
            continue
        parts.append(
            f'<div class="tile"><div class="n">{_e(counts[key])}</div>'
            f'<div class="l">{_e(t.gettext(label))}</div></div>'
        )
    parts.append("</div>")
    return "".join(parts)


def _table(headers: Sequence[str], rows: Iterable[Sequence[Any]],
           numeric: Optional[Sequence[int]] = None,
           empty: str = "None recorded") -> str:
    numeric = set(numeric or ())
    parts = ['<table class="data"><thead><tr>']
    for i, header in enumerate(headers):
        cls = ' class="num"' if i in numeric else ""
        parts.append(f"<th{cls}>{_e(header)}</th>")
    parts.append("</tr></thead><tbody>")
    empty = True
    for row in rows:
        empty = False
        parts.append("<tr>")
        for i, cell in enumerate(row):
            cls = ' class="num"' if i in numeric else ""
            parts.append(f"<td{cls}>{_e(cell if cell is not None else '—')}</td>")
        parts.append("</tr>")
    if empty:
        parts.append(
            f'<tr><td colspan="{len(headers)}" class="empty">{_e(empty)}</td></tr>'
        )
    parts.append("</tbody></table>")
    return "".join(parts)


_RECOVERY_NOTES = {
    "stored": "File binding: stored path identifiers",
    "watermark": "File binding: recovered from the path watermark",
    "time_window": "File binding: recovered from source, side and the job time window",
    "date_and_path": "File binding: recovered from source, side, date and intake path",
    "path_prefix": "File binding: recovered from the intake path under this source and side",
    "none": "File binding: counts are available; individual files could not be bound",
}


def _reader(t: Any) -> Any:
    if t is not None:
        return t
    from core.reporting.i18n import reader_for

    return reader_for("en")


def render_ingestion_batch(document: Dict[str, Any], t: Any = None, *,
                           interactive: bool = False,
                           auto_print: bool = False) -> bytes:
    t = _reader(t)
    from core.reporting.i18n import is_rtl, local_digits

    identity = document.get("identity") or {}
    counts = document.get("counts") or {}
    types = document.get("types") or []
    statuses = document.get("statuses") or []
    categories = document.get("categories") or []
    labels = document.get("category_labels") or []
    keywords = document.get("keywords") or []
    files = document.get("files") or []
    signals = document.get("signals") or []
    places = document.get("places") or []
    errors = document.get("errors") or []
    warnings = document.get("warnings") or []
    notes = document.get("notes") or []
    title = t.gettext(document.get("title") or "Ingestion Batch Report")
    language = getattr(t, "language", "en")
    direction = "rtl" if is_rtl(language) else "ltr"
    empty = t.gettext("None recorded")

    parts: List[str] = [
        "<!DOCTYPE html>",
        f'<html lang="{_e(language)}" dir="{direction}"><head><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'style-src \'unsafe-inline\'; script-src \'unsafe-inline\'">',
        f"<title>{_e(title)}</title>",
        f"<style>{_STYLE}</style></head>",
        '<body class="ingest-batch">',
    ]
    if interactive:
        parts.append(_toolbar(t, auto_print))
    parts.append(f'<p class="kicker">{_e(t.gettext("Ingestion batch"))}</p>')
    parts.append(f"<h1>{_e(title)}</h1>")
    parts.append(
        f'<p class="lede">{_e(t.gettext("A complete account of one intake: the source and side that classified it, every outcome count, the file-type breakdown, and the categories, labels and keywords assigned to the files that entered in this batch."))}</p>'
    )
    parts.append(
        f'<section class="identity" aria-label="{_e(t.gettext("Source and side"))}">'
    )
    parts.append('<div class="pair">')
    parts.append(
        f'<div><div class="lbl">{_e(t.gettext("Source"))}</div>'
        f'<div class="val">{_e(identity.get("source") or "—")}</div></div>'
    )
    parts.append(
        f'<div><div class="lbl">{_e(t.gettext("Side"))}</div>'
        f'<div class="val">{_e(identity.get("side") or "—")}</div></div>'
    )
    parts.append("</div></section>")

    meta_bits = []
    for key, label in (
        ("job_id", "Job"),
        ("path", "Path"),
        ("started_at", "Started"),
        ("finished_at", "Finished"),
        ("created_by", "Operator"),
    ):
        if identity.get(key):
            meta_bits.append(f"{_e(t.gettext(label))}: {_e(identity[key])}")
    if meta_bits:
        parts.append(f'<p class="cover-meta">{" · ".join(meta_bits)}</p>')
    recovery = identity.get("recovery")
    if recovery in _RECOVERY_NOTES:
        parts.append(
            f'<p class="cover-meta">{_e(t.gettext(_RECOVERY_NOTES[recovery]))}</p>'
        )

    parts.append(f"<h2>{_e(t.gettext('Outcome counts'))}</h2>")
    parts.append(_tiles(counts, t))

    parts.append(f"<h2>{_e(t.gettext('Files by type'))}</h2>")
    parts.append(_table(
        tuple(t.gettext(h) for h in (
            "Type", "Total", "Processed", "Failed", "Skipped", "Other")),
        (
            (row.get("file_type"), row.get("total"), row.get("processed"),
             row.get("failed"), row.get("skipped"), row.get("other"))
            for row in types
        ),
        numeric=(1, 2, 3, 4, 5),
        empty=empty,
    ))
    if not types:
        parts.append(_none(t.gettext(
            "No per-type breakdown is stored for this batch.")))

    if statuses:
        parts.append(f"<h2>{_e(t.gettext('Processing status'))}</h2>")
        parts.append(_table(
            (t.gettext("Status"), t.gettext("Count")),
            ((row.get("status"), row.get("count")) for row in statuses),
            numeric=(1,),
            empty=empty,
        ))

    parts.append(f"<h2>{_e(t.gettext('Categories assigned in this batch'))}</h2>")
    if categories:
        parts.append(_table(
            tuple(t.gettext(h) for h in ("Category", "Files", "Word hits")),
            ((row.get("name"), row.get("file_count"), row.get("occurrence_count"))
             for row in categories),
            numeric=(1, 2),
            empty=empty,
        ))
    else:
        parts.append(_none(t.gettext(
            "No automatic categories were assigned to files in this batch.")))

    parts.append(f"<h2>{_e(t.gettext('Category labels assigned in this batch'))}</h2>")
    if labels:
        parts.append('<div class="chips">')
        for row in labels:
            extra = ""
            if row.get("file_count"):
                extra = " · " + t.gettext("%(n)s file(s)", n=row.get("file_count"))
            parts.append(f'<span class="chip">{_e(row.get("name"))}{_e(extra)}</span>')
        parts.append("</div>")
        parts.append(_table(
            tuple(t.gettext(h) for h in ("Label", "Description", "Files")),
            ((row.get("name"), row.get("description"), row.get("file_count"))
             for row in labels),
            numeric=(2,),
            empty=empty,
        ))
    else:
        parts.append(_none(t.gettext(
            "No analyst category labels were assigned to files in this batch.")))

    parts.append(f"<h2>{_e(t.gettext('Keywords assigned in this batch'))}</h2>")
    if keywords:
        parts.append(_table(
            tuple(t.gettext(h) for h in ("Keyword", "Category", "Files", "Hits")),
            ((row.get("keyword"), row.get("category"), row.get("file_count"),
              row.get("hits"))
             for row in keywords),
            numeric=(2, 3),
            empty=empty,
        ))
    else:
        parts.append(_none(t.gettext(
            "No keywords were assigned to files in this batch.")))

    parts.append(f"<h2>{_e(t.gettext('Signals detected'))}</h2>")
    if signals:
        parts.append(_table(
            tuple(t.gettext(h) for h in ("Detector", "Type", "Resolution", "Count")),
            ((row.get("detector"), row.get("signal_type"), row.get("resolution"),
              row.get("count"))
             for row in signals),
            numeric=(3,),
            empty=empty,
        ))
    else:
        parts.append(_none(t.gettext(
            "No detector signals were stored for this batch.")))

    parts.append(f"<h2>{_e(t.gettext('Places mentioned'))}</h2>")
    if places:
        parts.append(_table(
            tuple(t.gettext(h) for h in ("Place", "Files", "Mentions")),
            ((row.get("place"), row.get("file_count"), row.get("mentions"))
             for row in places),
            numeric=(1, 2),
            empty=empty,
        ))
    else:
        parts.append(_none(t.gettext(
            "No place mentions were stored for this batch.")))

    parts.append(f"<h2>{_e(t.gettext('Files in this batch'))}</h2>")
    listed = counts.get("files_listed")
    stored = counts.get("files_in_report")
    if listed is not None and stored is not None and listed < stored:
        cap_note = t.gettext(
            "Listing %(listed)s of %(stored)s stored files; "
            "the listing is capped and the cap is stated.",
            listed=listed, stored=stored,
        )
        parts.append(
            f'<p class="warn">{_e(local_digits(cap_note, language))}</p>'
        )
    if files:
        parts.append(_table(
            tuple(t.gettext(h) for h in (
                "ID", "Name", "Type", "Size", "Status", "Processing")),
            ((row.get("path_id"), row.get("file_name"), row.get("file_type"),
              row.get("file_size"), row.get("file_status"),
              row.get("processing_status"))
             for row in files),
            numeric=(0, 3),
            empty=empty,
        ))
    else:
        parts.append(_none(t.gettext(
            "No stored file rows were identified for this batch.")))

    if errors:
        parts.append(f"<h2>{_e(t.gettext('Errors'))}</h2><ul>")
        for item in errors:
            parts.append(f"<li>{_e(item)}</li>")
        parts.append("</ul>")
    if warnings:
        parts.append(f"<h2>{_e(t.gettext('Warnings'))}</h2><ul>")
        for item in warnings:
            parts.append(f"<li>{_e(item)}</li>")
        parts.append("</ul>")
    if notes:
        parts.append(f"<h2>{_e(t.gettext('Notes'))}</h2><ul>")
        for item in notes:
            msgid = _RECOVERY_NOTES.get(item, item) if item in _RECOVERY_NOTES.values() else item
            parts.append(f"<li>{_e(t.gettext(msgid))}</li>")
        parts.append("</ul>")

    parts.append("</body></html>")
    return "".join(parts).encode("utf-8")


def format_text(document: Dict[str, Any], t: Any = None) -> str:
    """Plain-text rendering for the CLI."""
    t = _reader(t)
    identity = document.get("identity") or {}
    counts = document.get("counts") or {}
    title = t.gettext("Ingestion Batch Report").upper()
    lines = [
        "=" * 70,
        title,
        "=" * 70,
        f"{t.gettext('Source') + ':':<24}{identity.get('source') or '—'}",
        f"{t.gettext('Side') + ':':<24}{identity.get('side') or '—'}",
    ]
    if identity.get("job_id"):
        lines.append(f"{t.gettext('Job') + ':':<24}{identity['job_id']}")
    if identity.get("path"):
        lines.append(f"{t.gettext('Path') + ':':<24}{identity['path']}")
    if identity.get("started_at"):
        lines.append(f"{t.gettext('Started') + ':':<24}{identity['started_at']}")
    if identity.get("finished_at"):
        lines.append(f"{t.gettext('Finished') + ':':<24}{identity['finished_at']}")
    recovery = identity.get("recovery")
    if recovery in _RECOVERY_NOTES:
        lines.append(t.gettext(_RECOVERY_NOTES[recovery]))
    lines.append("-" * 70)
    for key, label in (
        ("files_total", "Total files"),
        ("files_processed", "Processed"),
        ("files_stored", "Stored"),
        ("files_failed", "Failed"),
        ("files_skipped", "Skipped"),
        ("files_duplicates", "Duplicates"),
        ("files_unsupported", "Unsupported"),
        ("file_types", "File types"),
    ):
        if counts.get(key) is not None:
            lines.append(f"{t.gettext(label) + ':':<24}{counts[key]}")
    types = document.get("types") or []
    if types:
        lines.append("")
        lines.append(t.gettext("Files by type (processed / failed / skipped):"))
        for row in types:
            lines.append(
                f"  {(row.get('file_type') or '?'):<16}"
                f"{row.get('total') or 0:>5}  "
                f"ok {row.get('processed') or 0:>4}  "
                f"fail {row.get('failed') or 0:>4}  "
                f"skip {row.get('skipped') or 0:>4}"
            )
    categories = document.get("categories") or []
    if categories:
        lines.append("")
        lines.append(t.gettext("Categories assigned:"))
        for row in categories:
            lines.append(
                f"  {row.get('name')}  "
                f"({row.get('file_count')} files, {row.get('occurrence_count')} hits)"
            )
    labels = document.get("category_labels") or []
    if labels:
        lines.append("")
        lines.append(t.gettext("Category labels assigned:"))
        for row in labels:
            lines.append(f"  {row.get('name')}  ({row.get('file_count')} files)")
    keywords = document.get("keywords") or []
    if keywords:
        lines.append("")
        lines.append(t.gettext("Keywords assigned:"))
        for row in keywords[:40]:
            cat = f" [{row.get('category')}]" if row.get("category") else ""
            lines.append(
                f"  {row.get('keyword')}{cat}  "
                f"({row.get('file_count')} files, {row.get('hits')} hits)"
            )
        if len(keywords) > 40:
            lines.append(f"  … {len(keywords) - 40} more")
    lines.append("=" * 70)
    return "\n".join(lines) + "\n"
