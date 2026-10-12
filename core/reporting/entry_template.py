"""Dedicated printable dossier template for the Full Entry Report.

One HTML document, one section per file: identity and analyst-entered
context, then the stored extracted text in full (or the stated prefix
when a row was shortened). Pure: the same document, language and
interactive flag produce the same bytes. Interactive chrome (print
button, auto-print) is a wrapper used only by the live preview route;
artifacts always call this with ``interactive=False``.
"""

from __future__ import annotations

import html
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.reporting.datasets import ENTRY_CONTENT_CHAR_LIMIT

_STYLE = (
    ":root{--ink:#1a1a1a;--muted:#5c5c5c;--rule:#c8c4bb;--paper:#f7f4ee;"
    "--band:#efeae0;--accent:#3d4a3a}"
    "html{color-scheme:light}"
    "body.entry-dossier{font-family:system-ui,'Segoe UI','Noto Sans',"
    "'Noto Sans Arabic','Noto Sans Hebrew',sans-serif;"
    "margin:0 auto;padding:1.5rem 1.75rem 3rem;color:var(--ink);"
    "background:#fff;line-height:1.55;max-width:46rem}"
    ".dossier-toolbar{display:flex;justify-content:space-between;align-items:center;"
    "gap:.75rem;flex-wrap:wrap;margin:0 0 1.25rem;padding:.65rem .85rem;"
    "background:var(--band);border:1px solid var(--rule);border-radius:6px;"
    "font-family:system-ui,'Segoe UI',sans-serif;font-size:.92rem}"
    ".dossier-toolbar button,.dossier-toolbar a.btn{appearance:none;border:1px solid #2f3a2d;"
    "background:var(--accent);color:#fff;padding:.4rem .9rem;border-radius:4px;"
    "font:inherit;cursor:pointer;text-decoration:none}"
    ".dossier-toolbar button.secondary,.dossier-toolbar a.secondary{background:#fff;"
    "color:var(--ink);border-color:var(--rule)}"
    ".kicker{letter-spacing:.18em;text-transform:uppercase;font-size:.72rem;"
    "color:var(--muted);margin:0 0 .35rem;font-family:system-ui,'Segoe UI',sans-serif}"
    "h1{font-size:1.85rem;font-weight:650;margin:0 0 .45rem;line-height:1.2}"
    "h2{font-size:1.2rem;margin:0 0 .35rem;page-break-after:avoid}"
    "h3{font-size:1rem;margin:1.1rem 0 .4rem;page-break-after:avoid}"
    ".lede{margin:.2rem 0 1rem;font-size:1.02rem}"
    ".basis{background:var(--paper);border:1px solid var(--rule);padding:.75rem 1rem;"
    "margin:0 0 1.15rem}"
    ".cover-meta{font-family:system-ui,'Segoe UI',sans-serif;font-size:.88rem;"
    "color:var(--muted);margin:0 0 1.25rem}"
    ".warn{color:#7a3e00;font-weight:600}"
    "nav.toc{margin:0 0 1.5rem;padding:0}"
    "nav.toc ol{margin:.4rem 0 0;padding-inline-start:1.25rem}"
    "nav.toc a{color:inherit;text-decoration:underline;text-underline-offset:.15em}"
    ".entry{border-top:2px solid var(--ink);padding:1.15rem 0 1.6rem;"
    "break-inside:avoid-page;page-break-before:always}"
    ".entry:first-of-type{page-break-before:auto}"
    ".entry-index{font-family:system-ui,'Segoe UI',sans-serif;font-size:.75rem;"
    "letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 .25rem}"
    ".entry-path{margin:.15rem 0 .75rem;color:var(--muted);font-size:.92rem;"
    "word-break:break-word}"
    "dl.meta{display:grid;grid-template-columns:minmax(7rem,11rem) 1fr;gap:.28rem .85rem;"
    "margin:0 0 .2rem;font-family:system-ui,'Segoe UI',sans-serif;font-size:.88rem}"
    "dl.meta dt{margin:0;color:var(--muted);font-weight:600}"
    "dl.meta dd{margin:0;word-break:break-word}"
    "pre.body{white-space:pre-wrap;word-break:break-word;margin:.35rem 0 0;"
    "padding:.85rem 1rem;background:var(--paper);border:1px solid var(--rule);"
    "font-family:system-ui,'Segoe UI','Noto Sans','Noto Sans Arabic',"
    "'Noto Sans Hebrew',sans-serif;font-size:.98rem;line-height:1.6}"
    ".empty{color:var(--muted);font-style:italic}"
    ".fp{font-family:ui-monospace,'Cascadia Mono',Consolas,monospace;font-size:.82em}"
    "table.prov{border-collapse:collapse;width:100%;font-size:.88rem;"
    "font-family:system-ui,'Segoe UI',sans-serif;margin:.4rem 0 0}"
    "table.prov th,table.prov td{border:1px solid var(--rule);padding:.28rem .5rem;"
    "text-align:start;vertical-align:top}"
    "table.prov th{background:var(--band);width:11rem}"
    ".none{color:#777;font-style:italic}"
    "@page{margin:14mm 15mm 16mm;size:A4}"
    "@media print{"
    "body.entry-dossier{margin:0;padding:0;max-width:none;color:#000;background:#fff}"
    ".no-print{display:none!important}"
    "a{color:inherit;text-decoration:none}"
    ".entry{break-before:page;border-top-color:#000}"
    ".entry:first-of-type{break-before:auto}"
    "h2,h3,.entry-index{break-after:avoid}"
    "pre.body,.basis,dl.meta{break-inside:avoid}"
    "thead{display:table-header-group}"
    "}"
)

_META_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("file_type", "File type"),
    ("file_size", "File size"),
    ("file_status", "Status"),
    ("file_date", "File date"),
    ("date_creation", "Created"),
    ("source_name", "Source"),
    ("side_name", "Side"),
    ("coordinates", "Coordinates"),
    ("analyst_categories", "Analyst categories"),
    ("content_chars", "Content characters"),
)


def _escape(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _entries_dataset(document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for ds in document.get("datasets") or ():
        if str(ds.get("dataset_key", "")).startswith("entry_content.entries"):
            return ds
    for ds in document.get("datasets") or ():
        names = {c.get("name") for c in ds.get("columns") or ()}
        if "extracted_text" in names and "file_name" in names:
            return ds
    return None


def _matched_total(document: Dict[str, Any], entries: Optional[Dict[str, Any]]) -> Optional[int]:
    for ds in document.get("datasets") or ():
        if str(ds.get("dataset_key", "")).startswith("entry_content.count"):
            rows = ds.get("rows") or ()
            if rows and rows[0].get("matched") is not None:
                try:
                    return int(rows[0]["matched"])
                except (TypeError, ValueError):
                    return None
    if entries is None:
        return None
    return entries.get("row_count")


def render_entry_dossier(document: Dict[str, Any], t: Any, *,
                         interactive: bool = False,
                         auto_print: bool = False) -> Tuple[bytes, Dict[str, Any]]:
    """Render the dedicated full-entry HTML template.

    ``t`` is a language reader (``gettext`` / ``language``). ``interactive``
    adds a print toolbar and may include a same-document print script;
    artifacts must pass ``interactive=False``.
    """
    from core.reporting.i18n import is_rtl, local_digits
    from core.reporting.render import _completeness, _provenance_pairs

    e: Callable[[Any], str] = _escape
    run = document.get("run") or {}
    report = document.get("report") or {}
    language = getattr(t, "language", "en")
    direction = "rtl" if is_rtl(language) else "ltr"
    title_msgid = report.get("title")
    title = t.gettext(title_msgid) if title_msgid else (run.get("report_key") or "Full Entry Report")
    preview = bool(document.get("preview") or run.get("preview"))
    entries_ds = _entries_dataset(document)
    rows: List[Dict[str, Any]] = list((entries_ds or {}).get("rows") or ())
    shown = len(rows)
    matched = _matched_total(document, entries_ds)
    truncated_listing = bool((entries_ds or {}).get("truncated"))
    if matched is None:
        matched = shown

    run_label = "" if preview or not run.get("id") else f" - run {e(run['id'])}"
    csp = ("default-src 'none'; style-src 'unsafe-inline'"
           + ("; script-src 'unsafe-inline'" if interactive else ""))
    parts: List[str] = [
        "<!DOCTYPE html>",
        f'<html lang="{e(language)}" dir="{direction}">',
        "<head><meta charset=\"utf-8\">",
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">',
        f"<title>{e(title)}{run_label}</title>",
        f"<style>{_STYLE}</style></head>",
        '<body class="entry-dossier">',
    ]
    if interactive:
        print_label = e(t.gettext("Print this report"))
        parts.append(
            '<div class="dossier-toolbar no-print" role="region" '
            f'aria-label="{print_label}">'
            f"<span>{e(t.gettext('Full Entry Report'))}</span>"
            "<span>"
            f'<button type="button" onclick="window.print()">{print_label}</button>'
            "</span></div>"
        )
    else:
        parts.append(
            f'<p class="no-print cover-meta">{e(t.gettext("Print this report"))}: '
            f"{e(t.gettext('Use the browser print command.'))}</p>"
        )

    parts.append(f'<p class="kicker">{e("SYLTHARAE")}</p>')
    parts.append(f"<h1>{e(title)}</h1>")
    if report.get("description"):
        parts.append(f'<p class="lede"><bdi>{e(t.gettext(report["description"]))}</bdi></p>')
    if report.get("help_summary"):
        parts.append(
            f'<section class="basis" aria-label="{e(t.gettext("Method"))}">'
            f"<h2>{e(t.gettext('Method'))}</h2>"
            f"<p><bdi>{e(t.gettext(report['help_summary']))}</bdi></p></section>"
        )

    count_text = t.gettext(
        "%(shown)s of %(total)s entries",
        shown=shown, total=matched,
    )
    count_text = local_digits(count_text, language)
    parts.append(f'<p class="cover-meta"><bdi>{e(count_text)}</bdi></p>')
    if truncated_listing:
        limit = (entries_ds or {}).get("row_limit") or shown
        short = t.gettext(
            "This listing was shortened at %(limit)s entries; more files matched.",
            limit=limit,
        )
        parts.append(f'<p class="warn"><bdi>{e(local_digits(short, language))}</bdi></p>')
    if entries_ds:
        parts.append(f"<p class=\"cover-meta\">{e(_completeness(entries_ds, t))}</p>")

    if rows:
        parts.append(f'<nav class="toc" aria-label="{e(t.gettext("Contents"))}">')
        parts.append(f"<h2>{e(t.gettext('Contents'))}</h2><ol>")
        for index, row in enumerate(rows, start=1):
            name = row.get("file_name") or t.gettext("Entry %(n)s of %(total)s",
                                                     n=index, total=shown)
            parts.append(f'<li><a href="#entry-{index}"><bdi>{e(name)}</bdi></a></li>')
        parts.append("</ol></nav>")

    if not rows:
        parts.append(f'<p class="empty">{e(t.gettext("No rows."))}</p>')

    for index, row in enumerate(rows, start=1):
        name = row.get("file_name") or ""
        heading = t.gettext("Entry %(n)s of %(total)s", n=index, total=shown)
        heading = local_digits(heading, language)
        parts.append(f'<article class="entry" id="entry-{index}">')
        parts.append(f'<p class="entry-index">{e(heading)}</p>')
        parts.append(f"<h2><bdi>{e(name) if name else e(t.gettext('(untitled)'))}</bdi></h2>")
        if row.get("file_path"):
            parts.append(f'<p class="entry-path"><bdi>{e(row["file_path"])}</bdi></p>')
        parts.append(f'<h3>{e(t.gettext("Identity"))}</h3><dl class="meta">')
        for field, label in _META_FIELDS:
            value = row.get(field)
            shown_value = ('<span class="none">(none)</span>' if value in (None, "")
                           else f"<bdi>{e(value)}</bdi>")
            parts.append(f"<dt>{e(t.gettext(label))}</dt><dd>{shown_value}</dd>")
        parts.append("</dl>")
        parts.append(f"<h3>{e(t.gettext('Full extracted text'))}</h3>")
        text = row.get("extracted_text")
        if text in (None, ""):
            parts.append(
                f'<p class="empty">{e(t.gettext("No extracted text is stored for this entry."))}</p>'
            )
        else:
            if row.get("content_truncated"):
                total_chars = row.get("content_chars") or ENTRY_CONTENT_CHAR_LIMIT
                note = t.gettext(
                    "Content shortened: the first %(shown)s of %(total)s characters are included.",
                    shown=min(ENTRY_CONTENT_CHAR_LIMIT, int(total_chars) if str(total_chars).isdigit()
                              else ENTRY_CONTENT_CHAR_LIMIT),
                    total=total_chars,
                )
                parts.append(f'<p class="warn"><bdi>{e(local_digits(note, language))}</bdi></p>')
            parts.append(f"<pre class=\"body\"><bdi>{e(text)}</bdi></pre>")
        parts.append("</article>")

    if not preview:
        parts.append(f"<h2>{e(t.gettext('Provenance'))}</h2><table class=\"prov\"><tbody>")
        for label, value in _provenance_pairs(document):
            shown_value = ('<span class="none">(none)</span>' if value is None
                           else f'<bdi class="fp">{e(value)}</bdi>')
            parts.append(f"<tr><th scope=\"row\">{e(label)}</th><td>{shown_value}</td></tr>")
        parts.append("</tbody></table>")

    if interactive and auto_print:
        parts.append("<script>window.addEventListener('load',function(){window.print();});</script>")
    parts.append("</body></html>\n")
    return "\n".join(parts).encode("utf-8"), {}
