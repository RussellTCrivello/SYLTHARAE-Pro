"""Build the extraction archive: text, its location, and its completeness.

For every file in the corpus this runs the product's reader, keeps the text
**per location unit** (one entry per PDF page, Word paragraph, Excel cell,
PowerPoint shape, archive member, OCR word box), and scores completeness by
token recall against an independent oracle.

Why token recall rather than character counts: formatting differs between any
two extractors (whitespace, join order, added headings), so a character ratio
punishes or rewards the wrong things. A word that the file contains and the
stored text does not is a real loss; a tab that one side omits is not.

The archive is one gzip-compressed JSONL: lossless, streamable, one record per
file, full text and full location data included. A CSV would have to flatten
the location tree; a database would not survive the repository.

Usage:
    python tools/audit/archive_extraction.py --corpus test-doc --out <dir>
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import resource
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

class Timeout(Exception):
    """Raised by the per-file alarm when a reader does not return."""


def _alarm(signum, frame):  # noqa: ARG001
    raise Timeout("per-file time limit reached")


SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def scrub(value: Any) -> Any:
    """Make a value JSON-safe, without hiding that it was unsafe."""
    if isinstance(value, str):
        return SURROGATE_RE.sub("\ufffd", value)
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def oracle_for(path: Path, ext: str) -> Dict[str, Any]:
    """Independent identity of the oracle used for this file (not the text)."""
    if ext == ".pdf":
        return {"oracle": "pymupdf"}
    if ext in (".docx", ".docm", ".dotx", ".dotm"):
        return {"oracle": "ooxml-w:t"}
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return {"oracle": "openpyxl"}
    if ext == ".xls":
        return {"oracle": "xlrd"}
    if ext in (".pptx", ".pptm", ".ppsx", ".potx"):
        return {"oracle": "ooxml-a:t"}
    if ext in (".odt", ".ods", ".odp", ".ott", ".ots", ".otp", ".odg"):
        return {"oracle": "content.xml"}
    if ext in (".html", ".htm", ".xhtml"):
        return {"oracle": "bs4"}
    if ext == ".rtf":
        return {"oracle": "striprtf"}
    if ext in (".txt", ".md", ".py", ".csv", ".tsv", ".log", ".json", ".xml",
               ".yml", ".yaml", ".ini", ".cfg"):
        return {"oracle": "direct-read"}
    if ext in (".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar"):
        return {"oracle": None, "note": "container: members, not text"}
    return {"oracle": None, "note": "no independent parser for this format"}

TOKEN_RE = re.compile(r"[0-9A-Za-z\u00c0-\u024f\u0400-\u04ff\u0590-\u05ff"
                      r"\u0600-\u06ff]+")


#: This checkout's own absolute path. Reader error messages quote the file they
#: failed on, so the archive would bake a machine path into a tracked file - and
#: tests/unit/test_no_machine_paths.py scans tracked files for exactly that.
_CHECKOUT = str(Path(__file__).resolve().parents[2])


def scrub_paths(value):
    """Remove this checkout's absolute path from any string in a record."""
    if isinstance(value, str):
        return value.replace(_CHECKOUT + "/", "").replace(_CHECKOUT, ".")
    if isinstance(value, dict):
        return {k: scrub_paths(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub_paths(v) for v in value]
    return value


def tokens(text: str) -> collections.Counter:
    return collections.Counter(TOKEN_RE.findall(text or ""))


def recall(oracle_text, stored_text: str) -> Dict[str, Any]:
    """Share of the oracle's word occurrences that survived to storage.

    ``oracle_text`` may be a list of readings of the same file - Word splits a
    word across runs whenever the formatting changes, so "<w:t>In</w:t>
    <w:t>voice</w:t>" is one word and "<w:t>Gmail</w:t><w:t>Shared</w:t>" in two
    cells is two. Rather than guess, the caller passes both joins and the
    reader gets the benefit of the better one: run boundaries are formatting,
    and a metric that punished them would report formatting as loss.
    """
    if isinstance(oracle_text, (list, tuple)):
        scored = [recall(text, stored_text) for text in oracle_text]
        scored = [s for s in scored if s["oracle_tokens"]]
        if not scored:
            return {"recall": None, "oracle_tokens": 0, "missing_tokens": 0,
                    "missing_sample": []}
        return max(scored, key=lambda s: s["recall"])

    o, s = tokens(oracle_text), tokens(stored_text)
    total = sum(o.values())
    if not total:
        return {"recall": None, "oracle_tokens": 0, "missing_tokens": 0,
                "missing_sample": []}
    kept = sum(min(n, s.get(t, 0)) for t, n in o.items())
    missing = [(t, n - s.get(t, 0)) for t, n in o.items() if s.get(t, 0) < n]
    missing.sort(key=lambda kv: (-len(kv[0]), -kv[1]))
    return {
        "recall": round(kept / total, 4),
        "oracle_tokens": total,
        "missing_tokens": total - kept,
        "missing_sample": [t for t, _ in missing[:20]],
    }


def units_from_content(content: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn a reader's output into located units, without inventing structure.

    Every unit names the container it came from, so a reader can point at the
    exact page, paragraph, cell, slide, member or box the text occupies.
    """
    units: List[Dict[str, Any]] = []

    def add(kind: str, loc: str, text: Any, allow_empty: bool = False,
            **meta: Any) -> None:
        if isinstance(text, (int, float)):
            text = str(text)
        if not allow_empty and (not isinstance(text, str) or not text.strip()):
            return
        unit = {"kind": kind, "loc": loc, "chars": len(text), "text": text}
        if meta:
            unit["meta"] = meta
        units.append(unit)

    pages = content.get("pages")
    if isinstance(pages, list) and pages and isinstance(pages[0], dict):
        for i, page in enumerate(pages, 1):
            number = page.get("page_number", page.get("number", i))
            add("page", f"page {number}", page.get("text"),
                width=page.get("width"), height=page.get("height"),
                rotation=page.get("rotation"), columns=page.get("columns"),
                method=page.get("method"))
            # Where on the page the text sits. A PDF page has no paragraphs, so
            # the block geometry is the only location record the format offers.
            for block in (page.get("blocks") or []):
                if not isinstance(block, dict):
                    continue
                add("pdf-block", f"page {number} block {block.get('index')}",
                    (block.get("text") or ""), allow_empty=True,
                    bbox=block.get("bbox"), column=block.get("column"),
                    dir=block.get("dir"), lines=block.get("lines"),
                    font_size=block.get("font_size"), block_type=block.get("type"))
            for table in (page.get("tables") or []):
                if not isinstance(table, dict):
                    continue
                add("pdf-table", f"page {number} table {table.get('table_number')}",
                    table.get("text"), rows=table.get("row_count"),
                    columns=table.get("column_count"), bbox=table.get("bbox"))

    sheets = content.get("sheets")
    sheet_list = []
    if isinstance(sheets, dict):
        for name, sheet in sheets.items():
            if isinstance(sheet, dict):
                sheet_list.append(dict(sheet, name=sheet.get("name") or name))
    elif isinstance(sheets, list):
        sheet_list = [s for s in sheets if isinstance(s, dict)]
    for sheet in sheet_list:
        name = sheet.get("name") or "?"
        rows = sheet.get("rows") or sheet.get("data") or []
        for ri, row in enumerate(rows, 1):
            if isinstance(row, (list, tuple)):
                for ci, cell in enumerate(row, 1):
                    add("cell", f"{name}!R{ri}C{ci}", cell)
            else:
                add("cell", f"{name}!R{ri}", row)

    elements = content.get("elements")
    if isinstance(elements, list) and elements and isinstance(elements[0], dict):
        for i, el in enumerate(elements, 1):
            kind = el.get("type") or "element"
            loc = (f"element {el.get('position', el.get('index', i))}"
                   f" ({kind})")
            if kind == "table" and isinstance(el.get("rows"), list):
                for ri, row in enumerate(el["rows"], 1):
                    add("table-row", f"{loc} row {ri}",
                        "\t".join(str(c) for c in row) if isinstance(row, list) else row)
            else:
                add(kind, loc, el.get("text"), style=el.get("style"))

    slides = content.get("slides")
    if isinstance(slides, list) and slides and isinstance(slides[0], dict):
        for i, slide in enumerate(slides, 1):
            n = slide.get("slide_number", slide.get("number", i))
            shapes = slide.get("elements") or slide.get("shapes") or \
                slide.get("texts") or []
            if shapes:
                for si, shape in enumerate(shapes, 1):
                    kind = shape.get("type") if isinstance(shape, dict) else "shape"
                    pos = (shape.get("position", si) if isinstance(shape, dict) else si)
                    text = shape.get("text") if isinstance(shape, dict) else shape
                    add("shape", f"slide {n} {kind} {pos}", text)
            else:
                add("slide", f"slide {n}", slide.get("text"))
            notes = slide.get("notes") or slide.get("speaker_notes")
            if isinstance(notes, str) and notes.strip():
                add("slide-notes", f"slide {n} notes", notes)

    members = content.get("members")
    if isinstance(members, list):
        for m in members:
            if isinstance(m, dict):
                add("member", m.get("name") or "member", m.get("text") or m.get("name"))
            else:
                add("member", str(m), str(m))

    coords = content.get("ocr_coordinates")
    if isinstance(coords, list) and coords:
        for i, box in enumerate(coords[:4000], 1):
            if isinstance(box, dict):
                text = box.get("text") or box.get("word") or ""
                bbox = box.get("bbox")
                if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                    loc = f"word {i} bbox={list(bbox)}"
                else:
                    loc = (f"word {i} at ({box.get('x')},{box.get('y')}) "
                           f"{box.get('width')}x{box.get('height')}")
                add("ocr-word", loc, text, confidence=box.get("confidence"))

    if not units:
        paragraphs = content.get("paragraphs")
        if isinstance(paragraphs, list):
            for i, p in enumerate(paragraphs, 1):
                add("paragraph", f"paragraph {i}",
                    p.get("text") if isinstance(p, dict) else p)
        tables = content.get("tables")
        if isinstance(tables, list):
            for ti, table in enumerate(tables, 1):
                rows = table.get("rows") if isinstance(table, dict) else table
                for ri, row in enumerate(rows or [], 1):
                    add("table-row", f"table {ti} row {ri}",
                        "\t".join(str(c) for c in row) if isinstance(row, list) else row)

    if not units:
        for key in ("text", "content", "raw_text", "body"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                add("document", "whole file", value)
                break

    return units


def probe(path: Path, svc, pipe, corpus: Path, timeout: int) -> Dict[str, Any]:
    rel = path.relative_to(corpus).as_posix()
    ext = path.suffix.lower()
    rec: Dict[str, Any] = {
        "path": rel, "folder": rel.split("/")[0], "ext": ext,
        "bytes": path.stat().st_size,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    def peak_memory_kb() -> int:
        """High-water mark of this process, in KiB.

        Not the file's own footprint: the harness reads files in one process, so
        this is a running maximum, and it is reported as an upper bound rather
        than per-file attribution. A true per-file figure needs a child process
        per file (see the backlog); a bound that is honest beats a number that
        is invented.
        """
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    import signal

    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(timeout)
    try:
        rec["sha256"] = sha256_file(path)
        reader, decision = svc.resolve_reader_for_file(str(path), ext)
        rec["reader"] = reader.__class__.__name__ if reader else None
        rec["declared_ext"] = decision.get("declared_extension")
        rec["detected_ext"] = decision.get("detected_extension")
        rec["format_id"] = decision.get("format_id")
        rec["mime_type"] = decision.get("mime_type")
        rec["extension_mismatch"] = decision.get("extension_mismatch")

        t0 = time.perf_counter()
        result = svc.read_file({"path": str(path), "extension": ext}) or {}
        rec["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        if not isinstance(result, dict):
            result = {}

        if result.get("error") and not result.get("pages") and not result.get("text"):
            rec["error"] = str(result["error"])

        content = result.get("content") if isinstance(result, dict) and \
            isinstance(result.get("content"), dict) and "elements" not in result else result

        stored = pipe._extract_text_from_content(content) or ""
        rec["stored_chars"] = len(stored)
        rec["stored_sha256"] = sha256_text(stored)
        rec["lone_surrogates"] = len(re.findall(r"[\ud800-\udfff]", stored))
        rec["peak_rss_kb"] = peak_memory_kb()
        rec["units"] = units_from_content(content)
        rec["unit_kinds"] = dict(collections.Counter(u["kind"] for u in rec["units"]))

        o = oracle_for(path, ext)
        rec["oracle"] = {k: v for k, v in o.items() if k != "text"}
        oracle_text = _oracle_text(path, ext)
        readings = oracle_text if isinstance(oracle_text, (list, tuple)) else [oracle_text]
        if not any((r or "").strip() for r in readings):
            if rec.get("error"):
                rec["verdict"] = "ERROR"
            elif not stored.strip():
                rec["verdict"] = "EMPTY-PLAUSIBLE"
            else:
                proxies = ocr_proxies(content)
                if proxies.get("kind") == "ocr":
                    rec["verdict"] = "UNVERIFIABLE"
                    rec["proxies"] = proxies
                else:
                    rec["verdict"] = "OK-NO-ORACLE"
        else:
            # the oracle text is re-derived from the file, never stored
            rec.update(recall(oracle_text, stored))
            r = rec.get("recall")
            if rec.get("error"):
                rec["verdict"] = "ERROR"
            elif r is None:
                rec["verdict"] = "OK-NO-ORACLE" if stored.strip() else "EMPTY-AGREED"
            elif r >= 0.995:
                rec["verdict"] = "COMPLETE"
            elif r >= 0.95:
                rec["verdict"] = "NEAR-COMPLETE"
            elif r >= 0.75:
                rec["verdict"] = "PARTIAL"
            else:
                rec["verdict"] = "INCOMPLETE"
        rec["text"] = stored
    except Timeout:
        rec["error"] = f"timeout after {timeout}s"
        rec["verdict"] = "TIMEOUT"
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["traceback"] = traceback.format_exc(limit=2)
        rec["verdict"] = "ERROR"
    finally:
        import signal

        signal.alarm(0)
    rec.setdefault("verdict", "ERROR")
    return rec


#: Word at a line end broken by a hyphen. The product's PDF reader rejoins
#: these (correctly - "peri-\nodic" is one word in the document); if the oracle
#: did not do the same, every join would be scored as two lost tokens.
_ORACLE_BREAK_RE = re.compile(r"(?<=[^\W\d_])\-[ \t]*\n[ \t]*(?=[^\W\d_])", re.UNICODE)

#: Presentation ligatures ("\ufb01le"), which no search finds as "file".
_ORACLE_LIGATURES = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi",
                     "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st"}


def normalise_for_recall(text: str) -> str:
    """Orthographic normalisation only - never content removal.

    Both sides of the comparison get the same treatment, so the score measures
    whether text survived, not whether two tools agree about hyphenation.
    """
    for ligature, letters in _ORACLE_LIGATURES.items():
        text = text.replace(ligature, letters)
    text = text.replace("\u00ad", "").replace("\u00a0", " ")
    return _ORACLE_BREAK_RE.sub("", text)


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _ooxml_runs(xml: str, namespace: str) -> List[str]:
    """Text of every ``<t>`` run under ``namespace``, tolerant of bad XML.

    A regex over ``<w:t>(.*?)</w:t>`` is only safe on well-formed input: this
    corpus contains a Word document with an unclosed run, and the regex happily
    swallowed the following markup into the "text", so the oracle counted
    attribute names (``smallCaps``, ``hAnsi``, ``Arial``) as document words and
    every extraction looked lossy.

    ElementTree is authoritative, so it is tried first; a part that will not
    parse falls back to the regex with any residual markup removed.
    """
    import xml.etree.ElementTree as ET

    prefix = "w" if "wordprocessingml" in namespace else "a"
    paragraph_tag = namespace + "p"

    def join_paragraph(runs) -> str:
        # Runs inside one paragraph concatenate with *no* separator: the spaces
        # a document has are inside its runs. Joining them with a space
        # fabricates word breaks - testWORD_various.docx formats a single word
        # as <w:t>ita</w:t><w:t>li</w:t><w:t>c</w:t> - and every such document
        # then looked lossy because the oracle held "ita", "li", "c" where the
        # reader correctly stored "italic".
        return "".join(runs)

    try:
        root = ET.fromstring(xml)
        # A text box anchored in a paragraph carries its own w:p inside a
        # w:txbxContent subtree. Counting its runs as part of the anchoring
        # paragraph as well stores every boxed caption twice.
        box_tag = namespace + "txbxContent"

        def paragraph_text(paragraph) -> str:
            collected: List[str] = []

            def collect(node) -> None:
                for child in node:
                    if child.tag == box_tag:
                        continue
                    if child.tag == namespace + "t":
                        collected.append(child.text or "")
                    collect(child)

            collect(paragraph)
            return join_paragraph(collected)

        paragraphs: List[str] = []

        def walk(node, inside_paragraph: bool = False) -> None:
            for child in node:
                if child.tag == paragraph_tag:
                    if not inside_paragraph:
                        paragraphs.append(paragraph_text(child))
                    walk(child, True)
                elif child.tag == box_tag:
                    walk(child, False)
                else:
                    walk(child, inside_paragraph)

        walk(root)
        if not paragraphs:
            return [node.text or "" for node in root.iter(namespace + "t")]
        return paragraphs
    except ET.ParseError:
        pattern = re.compile(r"<{0}:t(?:\s[^>]*)?>(.*?)</{0}:t>".format(prefix), re.S)
        paragraphs = re.split(r"</{0}:p>".format(prefix), xml)
        out = []
        for paragraph in paragraphs:
            runs = [re.sub(r"<[^>]*>", "", capture)
                    for capture in pattern.findall(paragraph)]
            if runs:
                out.append("".join(runs))
        return out or [re.sub(r"<[^>]*>", "", capture)
                       for capture in pattern.findall(xml)]


def ocr_proxies(content: dict) -> dict:
    """What *can* be said about text no oracle can check.

    A scanned page has no ground truth: the only honest verdict is
    UNVERIFIABLE. Reporting OK-NO-ORACLE for it claimed the extraction was fine
    because nothing objected. The proxies below are what evidence exists -
    coverage (pages that produced text), the engine's own confidence, and how
    much text per page - together with how it could actually be verified.
    """
    pages = content.get("pages") if isinstance(content, dict) else None
    if not isinstance(pages, list) or not pages:
        text = str(content.get("text") or "") if isinstance(content, dict) else ""
        if not text.strip():
            return {}
        return {"kind": "text", "chars": len(text),
                "how_to_verify": "second reader or human transcription"}

    ocr_pages = [p for p in pages if "ocr" in str(p.get("method") or "")]
    confidences = [float(p["ocr_confidence"]) for p in pages
                   if isinstance(p.get("ocr_confidence"), (int, float))]
    with_text = [p for p in pages if str(p.get("text") or "").strip()]
    return {
        "kind": "ocr",
        "pages": len(pages),
        "ocr_pages": len(ocr_pages),
        "pages_with_text": len(with_text),
        "coverage": round(len(with_text) / len(pages), 3) if pages else 0.0,
        "chars_per_page": round(
            sum(len(str(p.get("text") or "")) for p in pages) / len(pages), 1),
        "mean_confidence": (round(sum(confidences) / len(confidences), 3)
                            if confidences else None),
        "engines": sorted({str(p.get("ocr_engine") or p.get("method") or "?")
                           for p in ocr_pages}),
        "how_to_verify": ("recognition of a scanned page cannot be compared with "
                          "an independent reading of the same file; verify with a "
                          "second engine on a sample, or human transcription"),
    }


def _oracle_text(path: Path, ext: str) -> str:
    """Oracle text, kept out of the archive but used for the recall score."""
    try:
        if ext == ".pdf":
            import pymupdf

            with pymupdf.open(path) as doc:
                return normalise_for_recall("".join(p.get_text() for p in doc))
        if ext in (".docx", ".docm", ".dotx", ".dotm"):
            import zipfile

            # <w:t ...> only: a naive <w:t[^>]*> also matches <w:tbl>, which
            # put tag names into the oracle and made every DOCX look lossy.
            t_re = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
            # mc:Fallback repeats the whole DrawingML block (text boxes
            # included) for old readers. Counting it would ask the reader to
            # store every boxed caption twice.
            fallback_re = re.compile(r"<mc:Fallback>.*?</mc:Fallback>", re.S)
            with zipfile.ZipFile(path) as zf:
                parts = [n for n in zf.namelist()
                         if n == "word/document.xml"
                         or re.match(r"word/(header|footer|footnotes|endnotes|comments)\d*\.xml$", n)]
                runs = {n: _ooxml_runs(fallback_re.sub("", zf.read(n).decode("utf-8", "replace")), W_NS)
                        for n in sorted(parts)}
                # One reading, with Word's own semantics: runs inside a
                # paragraph abut (a word may be formatted in pieces), and
                # paragraphs are separated. A second, word-separated reading was
                # kept here once to tolerate readers that glued paragraphs
                # together; it also raised the score of a reader that *split*
                # words at formatting boundaries, which is the same defect seen
                # from the other side, so it is gone.
                return "\n".join("\n".join(r) for r in runs.values())
        if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
            import openpyxl

            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            out = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    out.extend(str(v) for v in row if v is not None)
            wb.close()
            return " ".join(out)
        if ext == ".xls":
            import xlrd

            book = xlrd.open_workbook(str(path), on_demand=True)
            out = []
            for sheet in book.sheets():
                for ri in range(sheet.nrows):
                    out.extend(str(v) for v in sheet.row_values(ri) if v not in ("", None))
            book.release_resources()
            return " ".join(out)
        if ext in (".pptx", ".pptm", ".ppsx", ".potx"):
            import zipfile

            with zipfile.ZipFile(path) as zf:
                slides = [n for n in zf.namelist()
                          if re.match(r"ppt/slides/slide\d+\.xml$", n)]
                notes = [n for n in zf.namelist()
                         if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", n)]
                return "\n".join("\n".join(_ooxml_runs(zf.read(n).decode("utf-8", "replace"), A_NS))
                                 for n in slides + notes)
        if ext in (".odt", ".ods", ".odp", ".ott", ".ots", ".otp", ".odg"):
            import zipfile

            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
                if "META-INF/manifest.xml" in names and b"encryption-data" in zf.read(
                        "META-INF/manifest.xml"):
                    # Ciphertext has no oracle. Decoding it anyway produced
                    # tokens such as "j7U" and scored a protected document as a
                    # total extraction loss, which is not a measurement of the
                    # reader at all.
                    return ""
                xml = zf.read("content.xml").decode("utf-8", "replace")
            return re.sub(r"<[^>]+>", " ", xml)
        if ext in (".html", ".htm", ".xhtml"):
            from bs4 import BeautifulSoup

            return BeautifulSoup(path.read_text("utf-8", "replace"),
                                 "html.parser").get_text(" ")
        if ext in (".txt", ".md", ".py", ".csv", ".tsv", ".log", ".json", ".xml",
                   ".yml", ".yaml", ".ini", ".cfg"):
            raw = path.read_bytes()
            for enc in ("utf-8", "utf-16", "cp1252", "latin-1"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", "replace")
        if ext == ".rtf":
            from striprtf.striprtf import rtf_to_text

            return rtf_to_text(path.read_text("latin-1", "replace"))
    except Exception:
        return ""
    return ""


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="test-doc")
    ap.add_argument("--out", default="audit_report/r15/extraction_archive")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--only", default=None, help="comma-separated corpus paths")
    ap.add_argument("--skip", default=None,
                    help="comma-separated corpus paths to leave out; a file that "
                         "cannot be interrupted is recorded separately")
    args = ap.parse_args(argv)

    corpus = Path(args.corpus).resolve()
    out = Path(args.out).resolve()
    (out / "text").mkdir(parents=True, exist_ok=True)
    jsonl = out / "records.jsonl"

    done = set()
    if args.resume and jsonl.exists():
        done = {json.loads(l)["path"] for l in jsonl.open(encoding="utf-8")}

    files = sorted(p for p in corpus.rglob("*") if p.is_file())
    if args.only:
        wanted = {w.strip() for w in args.only.split(",")}
        files = [p for p in files if p.relative_to(corpus).as_posix() in wanted]
    if args.skip:
        skipped = {w.strip() for w in args.skip.split(",")}
        files = [p for p in files if p.relative_to(corpus).as_posix() not in skipped]
    files = [p for p in files if p.relative_to(corpus).as_posix() not in done]

    from reader_file.services.file_reader_service import FileReaderService
    from pipeline.storage_pipeline import StoragePipeline

    svc = FileReaderService()
    pipe = object.__new__(StoragePipeline)

    print(f"archiving {len(files)} files", flush=True)
    with jsonl.open("a", encoding="utf-8") as fh:
        for i, path in enumerate(files, 1):
            rec = probe(path, svc, pipe, corpus, args.timeout)
            fh.write(json.dumps(scrub_paths(scrub(rec)), ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{i}/{len(files)}] {rec['verdict']:<16} "
                  f"recall={rec.get('recall')} units={len(rec.get('units', [])):4} "
                  f"{rec['path'][:60]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
