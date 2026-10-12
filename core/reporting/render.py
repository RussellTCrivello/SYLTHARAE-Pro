"""Artifact renderers: a completed run's stored datasets -> bytes (step 15).

Pure functions. Input is the *run document* - the run's recorded provenance
and the rows it stored (``services/reporting/artifacts.py`` builds it from
``report_runs`` / ``report_run_datasets``); nothing here touches the database,
the clock or the environment. The same document and renderer version give the
same bytes, byte for byte: generation time and the generating user belong to
the manifest, never to the content, and the XLSX container's timestamps are
pinned to the run's snapshot time.

Every rendering states, inside the content, the report and version, the run,
the snapshot, and for every dataset its limit semantics, its row count and
whether it was shortened - a reader of the file alone can tell a complete
listing from a capped one.

Values: the stored JSON values (dates and timestamps as ISO 8601 text,
numerics as exact decimal text). NULL is kept distinct where the format can
express it: JSON ``null``; HTML shows a marked "(none)"; CSV and XLSX have no
NULL, so an empty cell - the JSON artifact of the same run is the exact form,
and every manifest says how NULL was written (``null_representation``).

Spreadsheet safety: text that a spreadsheet would evaluate (leading ``=``,
``+``, ``-``, ``@``) is written with a leading apostrophe in CSV and XLSX,
using the repository's existing guard (``spreadsheet_safe_text``). Characters
XLSX cannot store (C0 controls) are replaced with U+FFFD and counted; the
count is reported, never silent.

Analyses (step 16): JSON, HTML and XLSX carry every stored analysis of the run -
its state, measures, rows and the five-voice narrative. The narrative is
stored as template references; it is rendered here from the reviewed msgids
and the JSON also keeps the references, so the text can be re-rendered in
any catalog language. CSV renders one dataset; XLSX keeps datasets on their
own sheets and puts the analytical narrative on an "Analytical findings"
sheet. HTML leads with the report description and help-topic basis, then
findings, then supporting tables, with print styles for analyst-readable
paper output. The manifest of every artifact lists the run's analyses and
says whether the artifact includes them.

PDF and SVG charts are multilingual rendering (step 18) and are not produced
here; asking for them is refused, not approximated.
"""

from __future__ import annotations

import csv
import html
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

#: Renderer identity per format. Bump the number whenever the bytes a format
#: produces for the same run would change.
RENDERERS: Dict[str, str] = {
    "json": "report-json/3",     # 3: language-aware (the language is stated)
    "csv": "report-csv/1",       # data-only: headers are the declared column names
    "xlsx": "report-xlsx/3",     # 3: analysis narratives as their own sheet
    "html": "report-html/4",     # 4: methodology preamble + print layout
}
#: Formats whose content includes the run's analyses.
WITH_ANALYSES = frozenset({"json", "html", "xlsx"})
MEDIA_TYPES: Dict[str, str] = {
    "json": "application/json",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "html": "text/html",
}
#: Formats that render exactly one dataset (``dataset_key`` required).
SINGLE_DATASET = frozenset({"csv"})
#: Declared but produced in a later step; refused with this reason.
NOT_YET = {"pdf": "PDF rendering is not implemented (the step 18 limitation stated "
                  "in the docs): server-side PDF with shaped Arabic/Hebrew text and "
                  "bundled fonts remains future work - a refusal, never an approximation",
           "svg": "charts are not implemented yet (the step 18 limitation stated in "
                  "the docs) - a refusal, never an approximation"}
NULL_REPRESENTATION = {"json": "JSON null", "html": "the marked text (none)",
                       "csv": "empty cell (indistinguishable from empty text; the JSON "
                              "artifact of the same run is exact)",
                       "xlsx": "empty cell (indistinguishable from empty text; the JSON "
                               "artifact of the same run is exact)"}

_XLSX_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class RenderError(ValueError):
    """The request cannot be rendered (unknown format, missing dataset...)."""


@dataclass
class Rendering:
    content: bytes
    format: str
    renderer_version: str
    media_type: str
    filename: str
    dataset_key: Optional[str]
    notes: Dict[str, Any] = field(default_factory=dict)


def safe_filename(*parts: Any) -> str:
    """A filename from server-side identifiers only, restricted to
    ``[A-Za-z0-9._-]`` (matches the table's CHECK)."""
    text = "_".join(str(p) for p in parts if p not in (None, ""))
    text = _FILENAME_UNSAFE.sub("-", text).strip("-._")
    text = re.sub(r"\.{2,}", ".", text)
    return (text or "report")[:180]


def canonical_json(value: Any) -> bytes:
    """The one serialisation used for JSON artifacts and manifest digests."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _dataset(document: Dict[str, Any], key: Optional[str]) -> Dict[str, Any]:
    for ds in document["datasets"]:
        if ds["dataset_key"] == key:
            return ds
    raise RenderError(f"the run has no dataset {key!r}")


def _completeness(ds: Dict[str, Any], t) -> str:
    # Pure chrome: the only substituted values are counts and limits, so
    # local numerals apply to the whole phrase.
    from core.reporting.i18n import local_digits

    kind = "top-N" if ds["semantics"] == "top_n" else "capped"
    if ds["semantics"] == "exact":
        text = t.gettext("complete: %(count)s rows (exact)", count=ds["row_count"])
    elif ds["truncated"]:
        text = t.gettext("shortened: the first %(count)s rows are included; more rows "
                         "existed (%(kind)s at %(limit)s)",
                         count=ds["row_count"], kind=kind, limit=ds["row_limit"])
    else:
        text = t.gettext("complete: %(count)s rows (%(kind)s at %(limit)s, not reached)",
                         count=ds["row_count"], kind=ds["semantics"],
                         limit=ds["row_limit"])
    return local_digits(text, t.language)


def _provenance_pairs(document: Dict[str, Any]) -> List[Tuple[str, Any]]:
    run = document["run"]
    return [
        ("report", run["report_key"]),
        ("title", document["report"].get("title")),
        ("unit", document["report"].get("unit")),
        ("definition fingerprint", run["definition_fingerprint"]),
        ("run", run["id"]),
        ("parameters fingerprint", run["parameters_fingerprint"]),
        ("criteria fingerprint", run["criteria_fingerprint"]),
        ("saved search", run["saved_search_id"]),
        ("requested by", run["requester_username"]),
        ("requester role", run["requester_role"]),
        ("snapshot", run["snapshot"]),
        ("snapshot time", run["snapshot_at"]),
        ("isolation", run["isolation_level"]),
        ("runner", run["generator_version"]),
        ("requested at", run["requested_at"]),
        ("finished at", run["finished_at"]),
    ]


def _analysis_text(analysis: Dict[str, Any], t) -> List[Dict[str, str]]:
    from core.analytics.narrative import render as render_narrative, source_ngettext
    from core.reporting.i18n import local_digits

    def format_number(value):
        text = f"{value:,}" if isinstance(value, int) else (
            f"{value:,.2f}" if isinstance(value, float) else str(value))
        return local_digits(text, t.language)

    return render_narrative(analysis["narrative"], t.gettext,
                            format_number=format_number,
                            ngettext=(t.ngettext if t.language != "en"
                                      else source_ngettext))


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------

def _render_json(document, dataset_key, t):
    body = {
        "format": RENDERERS["json"],
        "language": t.language,
        "report": document["report"],
        "run": document["run"],
        "datasets": [dict(ds, completeness=_completeness(ds, t))
                     for ds in document["datasets"]],
        "analyses": [dict(a, text=_analysis_text(a, t))
                     for a in document.get("analyses", ())],
    }
    return canonical_json(body) + b"\n", {}


def _render_csv(document, dataset_key, t):
    from Api.services.document_intelligence import spreadsheet_safe_text

    ds = _dataset(document, dataset_key)
    names = [c["name"] for c in ds["columns"]]
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(names)
    guarded = 0
    for row in ds["rows"]:
        cells = []
        for name in names:
            text = _cell_text(row.get(name))
            safe = spreadsheet_safe_text(text) if isinstance(row.get(name), str) else text
            guarded += safe != text
            cells.append(safe)
        writer.writerow(cells)
    return out.getvalue().encode("utf-8-sig"), {"formula_guarded_cells": guarded}


def _pin_zip(data: bytes, date_time: Tuple[int, int, int, int, int, int]) -> bytes:
    """Rewrite a ZIP container with fixed entry timestamps (content unchanged)."""
    source = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            pinned = zipfile.ZipInfo(info.filename, date_time=date_time)
            pinned.compress_type = zipfile.ZIP_DEFLATED
            pinned.external_attr = 0o600 << 16
            target.writestr(pinned, source.read(info.filename))
    return out.getvalue()


def _render_xlsx(document, dataset_key, t):
    from openpyxl import Workbook

    from Api.services.document_intelligence import spreadsheet_safe_text

    notes = {"formula_guarded_cells": 0, "replaced_control_characters": 0}

    def text(value: str) -> str:
        cleaned, n = _XLSX_ILLEGAL.subn("\ufffd", value)
        notes["replaced_control_characters"] += n
        safe = spreadsheet_safe_text(cleaned)
        notes["formula_guarded_cells"] += safe != cleaned
        return safe

    def cell(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int) and abs(value) < 2 ** 53:
            return value
        if isinstance(value, float):
            return value
        return text(_cell_text(value))

    workbook = Workbook()
    info = workbook.active
    info.title = t.gettext("Provenance")[:31]
    info.append([t.gettext("Field"), t.gettext("Value")])
    for label, value in _provenance_pairs(document):
        info.append([label, cell(value)])
    info.append([])
    info.append([t.gettext("Dataset"), t.gettext("Sheet"), t.gettext("Semantics"),
                 t.gettext("Row limit"), t.gettext("Rows"), t.gettext("Truncated"),
                 t.gettext("Completeness"), t.gettext("Query fingerprint")])
    used = {info.title}
    sheets = []
    for index, ds in enumerate(document["datasets"], start=1):
        base = re.sub(r"[\[\]\*\?/\\:]", "_", ds["dataset_key"].split("@")[0])[:26] or "data"
        name = base if base not in used else f"{base[:23]}_{index}"
        used.add(name)
        sheets.append((name, ds))
        info.append([ds["dataset_key"], name, ds["semantics"], ds["row_limit"],
                     ds["row_count"],
                     t.gettext("yes") if ds["truncated"] else t.gettext("no"),
                     _completeness(ds, t), ds["query_fingerprint"]])

    analyses = document.get("analyses") or ()
    if analyses:
        analysis_sheet = workbook.create_sheet(t.gettext("Analysis")[:31])
        used.add(analysis_sheet.title)
        analysis_sheet.append([t.gettext("Name"), t.gettext("Field"), t.gettext("Value"),
                               t.gettext("Status"), t.gettext("Analysis")])
        for a in analyses:
            # Read into a local first: the title is stored data, and a message
            # extractor walks a translation call's arguments for string
            # constants - a lookup key would be offered as a message (NARR-02).
            analysis_title = a.get("title")
            title = t.gettext(analysis_title) if analysis_title else a["analysis_key"]
            state = (t.gettext("measured") if a["state"] == "measured"
                     else t.gettext("not measurable (%(reason)s)", reason=a["reason"]))
            for voice in _analysis_text(a, t):
                analysis_sheet.append([
                    text(title), text(_voice_label(voice["voice"], t)),
                    text(voice["text"]), text(state), text(a["analysis_key"])])
            analysis_sheet.append([])

    for name, ds in sheets:
        sheet = workbook.create_sheet(name)
        names = [c["name"] for c in ds["columns"]]
        sheet.append(names)
        for row in ds["rows"]:
            sheet.append([cell(row.get(n)) for n in names])
        sheet.freeze_panes = "A2"
    pinned = _snapshot_time(document)
    workbook.properties.creator = "SYLTHARAE " + RENDERERS["xlsx"]
    workbook.properties.created = pinned
    workbook.properties.modified = pinned
    workbook.properties.lastModifiedBy = None
    buffer = io.BytesIO()
    # openpyxl's save() stamps "now" into docProps; write through its
    # ExcelWriter instead so the pinned times stay, then pin the ZIP entries.
    from openpyxl.writer.excel import ExcelWriter

    archive = zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, allowZip64=True)
    ExcelWriter(workbook, archive).save()
    workbook.close()
    data = _pin_zip(buffer.getvalue(), (max(pinned.year, 1980), pinned.month, pinned.day,
                                        pinned.hour, pinned.minute, pinned.second))
    return data, notes


def _snapshot_time(document):
    import datetime

    raw = document["run"].get("snapshot_at")
    moment = datetime.datetime.fromisoformat(raw)
    if moment.tzinfo is not None:
        moment = moment.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return moment.replace(microsecond=0)


_HTML_STYLE = (
    "body{font-family:system-ui,'Segoe UI','Noto Sans','Noto Sans Arabic','Noto Sans Hebrew',"
    "sans-serif;margin:1.5rem;color:#111;line-height:1.45;max-width:52rem}"
    "h1{font-size:1.6rem;margin:0 0 .4rem}h2{font-size:1.15rem;margin:1.4rem 0 .5rem;"
    "page-break-after:avoid}h3{font-size:1rem;margin:1rem 0 .35rem;page-break-after:avoid}"
    "p,li,dd,dt{page-break-inside:avoid}.lede{font-size:1.02rem;margin:.35rem 0 1rem}"
    ".basis{background:#f7f7f7;border:1px solid #ddd;padding:.75rem 1rem;margin:0 0 1.25rem}"
    "table{border-collapse:collapse;margin:.5rem 0 1.5rem;width:100%;font-size:.92rem}"
    "th,td{border:1px solid #bbb;padding:.3rem .55rem;text-align:start;vertical-align:top}"
    "th{background:#f0f0f0}.none{color:#777;font-style:italic}.short{color:#8a4b00;"
    "font-weight:600}.fp{font-family:monospace;font-size:.85em}"
    "dl.voices{margin:.4rem 0 1rem}dl.voices dt{font-weight:700;margin-top:.55rem}"
    "dl.voices dd{margin:.15rem 0 .35rem 0}"
    "@media print{body{margin:12mm;max-width:none;color:#000}"
    ".basis{background:#fff;border-color:#999}a{color:inherit;text-decoration:none}"
    "h2,h3{break-after:avoid}table,dl.voices,.basis{break-inside:avoid}"
    "thead{display:table-header-group}}"
)


_VOICE_LABELS = {
    "measure": "Measure",
    "finding": "Finding",
    "confidence": "Confidence",
    "consequence": "Consequence",
    "caveat": "Caveat",
}


def _voice_label(voice: str, t) -> str:
    return t.gettext(_VOICE_LABELS.get(voice, voice.capitalize()))


def _uses_entry_dossier(document: Dict[str, Any]) -> bool:
    report = document.get("report") or {}
    run = document.get("run") or {}
    if report.get("layout") == "entry_dossier":
        return True
    report_id = report.get("id") or run.get("report_id") or ""
    key = run.get("report_key") or ""
    return report_id == "entry_content" or str(key).startswith("entry_content@")


def _render_html(document, dataset_key, t):
    from core.reporting.i18n import is_rtl

    if _uses_entry_dossier(document):
        from core.reporting.entry_template import render_entry_dossier

        return render_entry_dossier(document, t, interactive=False)

    e = lambda v: html.escape(_cell_text(v), quote=True)   # noqa: E731
    run, report = document["run"], document["report"]
    language = t.language
    direction = "rtl" if is_rtl(language) else "ltr"
    title_msgid = report.get("title")
    title = t.gettext(title_msgid) if title_msgid else run["report_key"]
    parts = ["<!DOCTYPE html>",
             f'<html lang="{e(language)}" dir="{direction}"><head><meta charset="utf-8">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
             'style-src \'unsafe-inline\'">',
             f"<title>{e(title)} - run {e(run['id'])}</title>",
             f"<style>{_HTML_STYLE}</style></head><body>",
             f"<h1>{e(title)}</h1>"]
    report_description = report.get("description")
    if report_description:
        parts.append(f'<p class="lede"><bdi>{e(t.gettext(report_description))}</bdi></p>')
    help_summary = report.get("help_summary")
    if help_summary:
        parts.append(
            f'<section class="basis" aria-label="{e(t.gettext("Method"))}">'
            f"<h2>{e(t.gettext('Method'))}</h2>"
            f"<p><bdi>{e(t.gettext(help_summary))}</bdi></p></section>")
    parts.append(f"<h2>{e(t.gettext('Provenance'))}</h2><table><tbody>")
    for label, value in _provenance_pairs(document):
        shown = ('<span class="none">(none)</span>' if value is None
                 else f'<bdi class="fp">{e(value)}</bdi>')
        parts.append(f"<tr><th scope=\"row\">{e(label)}</th><td>{shown}</td></tr>")
    parts.append("</tbody></table>")
    if document.get("analyses"):
        parts.append(f"<h2>{e(t.gettext('Analysis'))}</h2>")
    for a in document.get("analyses", ()):
        analysis_title = a.get("title")
        parts.append(f"<h3><bdi>{e(t.gettext(analysis_title) if analysis_title else a['analysis_key'])}"
                     "</bdi></h3>")
        state = (t.gettext("measured") if a["state"] == "measured"
                 else t.gettext("not measurable (%(reason)s)", reason=a["reason"]))
        sentence = t.gettext(
            "Analysis %(key)s, %(state)s; templates %(tpl)s@%(ver)s.",
            key=a["analysis_key"], state=state,
            tpl=a["template_set"], ver=a["template_version"])
        parts.append(f"<p><bdi>{e(sentence)}</bdi></p><dl class=\"voices\">")
        for voice in _analysis_text(a, t):
            parts.append(f"<dt>{e(_voice_label(voice['voice'], t))}</dt>"
                         f"<dd><bdi>{e(voice['text'])}</bdi></dd>")
        parts.append("</dl>")
    if document["datasets"]:
        parts.append(f"<h2>{e(t.gettext('Datasets'))}</h2>")
    for ds in document["datasets"]:
        cls = ' class="short"' if ds["truncated"] else ""
        heading = ds.get("label") or ds["dataset_key"]
        parts.append(f"<h3><bdi>{e(heading)}</bdi></h3>")
        fp_sentence = t.gettext("Query fingerprint %(fingerprint)s.",
                                fingerprint=str(ds["query_fingerprint"]))
        parts.append(f"<p{cls}>{e(_completeness(ds, t))}. "
                     f"{e(fp_sentence)}</p>")
        parts.append("<table><thead><tr>")
        for column in ds["columns"]:
            parts.append(f"<th scope=\"col\" title=\"{e(column['name'])}\">"
                         f"{e(column.get('label') or column['name'])}</th>")
        parts.append("</tr></thead><tbody>")
        names = [c["name"] for c in ds["columns"]]
        for row in ds["rows"]:
            parts.append("<tr>")
            for name in names:
                value = row.get(name)
                parts.append('<td><span class="none">(none)</span></td>' if value is None
                             else f"<td><bdi>{e(value)}</bdi></td>")
            parts.append("</tr>")
        if not ds["rows"]:
            parts.append(f"<tr><td colspan=\"{max(1, len(names))}\">"
                         f"{e(t.gettext('No rows.'))}</td></tr>")
        parts.append("</tbody></table>")
    parts.append("</body></html>\n")
    return "\n".join(parts).encode("utf-8"), {}


_RENDER: Dict[str, Callable] = {"json": _render_json, "csv": _render_csv,
                                "xlsx": _render_xlsx, "html": _render_html}


def check_request(document_datasets: List[str], fmt: Any, dataset_key: Any) -> Tuple[str, Optional[str]]:
    """Validate a format/dataset request against a run's dataset keys."""
    if not isinstance(fmt, str) or not fmt:
        raise RenderError("format is required")
    if fmt in NOT_YET:
        raise RenderError(f"{fmt} is not available yet: {NOT_YET[fmt]}")
    if fmt not in RENDERERS:
        raise RenderError(f"format must be one of: {', '.join(sorted(RENDERERS))}")
    if fmt in SINGLE_DATASET:
        if not isinstance(dataset_key, str) or dataset_key not in document_datasets:
            raise RenderError(f"{fmt} renders one dataset: dataset_key must be one of "
                              f"{', '.join(document_datasets)}")
        return fmt, dataset_key
    if dataset_key not in (None, ""):
        raise RenderError(f"{fmt} renders every dataset of the run; omit dataset_key")
    return fmt, None


def render(document: Dict[str, Any], fmt: str, dataset_key: Optional[str] = None,
           language: str = "en") -> Rendering:
    """Render one run document. ``language`` is part of the rendering -
    explicit, validated (an unknown language is refused, never silently
    rendered as English) and recorded in the notes; a missing catalog
    entry falls back to the msgid and is counted there."""
    from core.reporting.i18n import reader_for

    fmt, dataset_key = check_request([d["dataset_key"] for d in document["datasets"]],
                                     fmt, dataset_key)
    try:
        t = reader_for(language)
    except ValueError as exc:
        raise RenderError(str(exc)) from None
    content, notes = _RENDER[fmt](document, dataset_key, t)
    run = document["run"]
    filename = safe_filename("report", run["report_id"], f"v{run['report_version']}",
                             f"run{run['id']}",
                             dataset_key.split("@")[0] if dataset_key else None,
                             t.language) + "." + fmt
    notes = dict(notes, null_representation=NULL_REPRESENTATION[fmt],
                 language=t.language)
    if fmt != "csv":
        # A data-only CSV carries no renderer chrome, so it has no
        # fallback to report; every chrome-bearing format states its own.
        notes["translation_fallbacks"] = t.fallbacks
    return Rendering(content=content, format=fmt, renderer_version=RENDERERS[fmt],
                     media_type=MEDIA_TYPES[fmt], filename=filename,
                     dataset_key=dataset_key, notes=notes)
