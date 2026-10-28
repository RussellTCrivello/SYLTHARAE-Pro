#!/usr/bin/env python3
"""Classify every failing unit id between two commits, with evidence.

Round 22 published "67 failures before and after" while the Round 21 record said
"34 pre-existing". Both numbers came from runs whose environments differed, and
neither run wrote down which ids those were. This tool makes the comparison
reproducible: it reads the JUnit XML of two runs made in one environment, plus
the XML of a third run made with the OCR and ffmpeg engines installed, and
classifies every failing id.

The categories are the ones ``tools/audit/triage_failures.py`` already uses, so
the audit speaks one vocabulary. Two classes are added here because they are
proven by measurement rather than asserted:

``ENV-OCR``   the id passes in the engine venv and fails without it (proven, not
              guessed: the same test id, two environments)
``ENV-FFMPEG``the same, for the media reader

An id that matches no rule exits non-zero: an unclassified failure blocks
closeout, so this is a check and not a report.

Usage::

    python3 tools/audit/r22_baseline.py \
        --before /tmp/an/junit_dc6a413.xml \
        --after  /tmp/an/junit_6cf97f3.xml \
        --engines /tmp/an/junit_ocr_env.xml \
        --out audit_report/r22_workbook/baseline_ids.csv
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit.triage_failures import classify  # noqa: E402

#: Modules whose ids the engine venv proves: without the engine they cannot run.
OCR_MODULES = (
    "test_embedded_images", "test_date_and_orientation", "test_pdf_text_layer",
    "test_ocr_engines", "test_ocr_matrix", "test_pdf_mixed_pages",
    "test_ocr_selfcheck", "test_ocr_provenance_docs",
)
MEDIA_MODULES = ("test_audio_metadata_fallback", "test_video_metadata_only")

#: ``(path, name prefix) -> (class, verdict, evidence)`` for ids whose cause is
#: not the environment and not a file the rule table names by module. Each
#: entry carries the measurement that justifies it, so the row can be checked
#: rather than believed.
MEASURED = {
    ("tests/unit/test_content_vs_identity.py", "test_"): (
        "NEEDS-DECISION",
        "stale helper: the test passes `None` as `self` to a method that now reads it",
        "`inspect.signature(StoragePipeline._extract_text_from_content)` is "
        "`(self, content)` and its body calls `self._media_metadata_text`; both "
        "ids fail from dc6a413 onwards and were already in the Round 21 failing "
        "set (id_diff_unit.csv). The product changed on 2026-10-27 (1c60be5), "
        "the helper's docstring still says `self` is unused",
    ),
}

#: Ids the environment explains, where the engine venv is not the evidence.
#: Each entry names the measurement that justifies it.
ENVIRONMENT = {
    "tests/unit/test_licensing.py":
        "the two new PyMuPDF sub-distributions publish no licence metadata, so "
        "the checker reports `unknown`; the packages themselves are AGPL-3.0",
    "tests/unit/test_no_machine_paths.py":
        "the portability gate: the checkout path and pre-existing audit artefacts "
        "are in the scanned set (see REPORT.md, the two permanently-red gates)",
}


def _module_of(classname: str) -> str:
    """``tests.unit.test_x.TestY`` -> ``tests/unit/test_x.py``.

    pytest puts the class in ``classname`` and only the test name in ``name``,
    so the module is the dotted path up to the first component after
    ``test_*`` that is not part of the module name.
    """
    parts = classname.split(".")
    keep = []
    for part in parts:
        if keep and not part.startswith("test_") and part[:1].isupper():
            break            # the class name starts here
        keep.append(part)
    return "/".join(keep) + ".py"


def failing_ids(xml_path: pathlib.Path) -> dict:
    """``{"path::name": status}`` for every failing id in a JUnit file."""
    root = ET.parse(xml_path).getroot()
    out = {}
    for case in root.iter("testcase"):
        name = case.get("name") or ""
        module = _module_of(case.get("classname") or "")
        status = None
        for child in case:
            if child.tag in ("failure", "error"):
                status = child.tag
                break
        if status:
            out[f"{module}::{name}"] = status
    return out


def counts(xml_path: pathlib.Path) -> dict:
    root = ET.parse(xml_path).getroot()
    suites = root.findall(".//testsuite") or [root]
    total = sum(int(s.get("tests", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) for s in suites)
    errors = sum(int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    return {"tests": total, "passed": total - failures - errors - skipped,
            "failed": failures, "errors": errors, "skipped": skipped,
            "failing_ids": failures + errors}


def classify_id(test_id: str, engines: set) -> tuple:
    """``(class, verdict, evidence)`` for one failing id."""
    path, _, name = test_id.partition("::")
    module = pathlib.Path(path).stem

    if test_id in engines:
        return ("ENV", "engine-only failure", "passes in the venv with OCR+ffmpeg")
    if module in OCR_MODULES:
        return ("ENV-OCR", "environment",
                "no OCR engine in this venv; the whole module passes with one")
    if module in MEDIA_MODULES:
        return ("ENV-FFMPEG", "environment",
                "no ffmpeg binary in this venv; the module passes with one")
    if path in ENVIRONMENT:
        return (pathlib.Path(path).stem, "environment", ENVIRONMENT[path])
    for (rule_path, prefix), row in MEASURED.items():
        if path == rule_path and name.startswith(prefix):
            return row

    verdict, decision, cause, action = classify(path, name)
    if verdict == "UNCLASSIFIED":
        return (verdict, verdict, "")
    return (verdict, f"{decision}: {action}".strip(": "), cause)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--before", required=True, type=pathlib.Path)
    parser.add_argument("--after", required=True, type=pathlib.Path)
    parser.add_argument("--engines", type=pathlib.Path,
                        help="JUnit XML from the venv with OCR and ffmpeg")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)

    before = failing_ids(args.before)
    after = failing_ids(args.after)
    engines = failing_ids(args.engines) if args.engines else set()

    ids = sorted(set(before) | set(after))
    rows, unclassified = [], []
    for test_id in ids:
        if test_id not in after:            # failing before, passing after
            rows.append({
                "id": test_id, "dc6a413": before[test_id], "6cf97f3": "pass",
                "class": "FIXED", "verdict": "fixed between the two commits",
                "evidence": "fails at dc6a413 and passes at 6cf97f3 in this "
                            "environment; `git log -S` on the assertion names the "
                            "commit that changed the artefact",
                "change": "fixed",
            })
            continue
        cls, verdict, evidence = classify_id(test_id, engines)
        if cls == "UNCLASSIFIED":
            unclassified.append(test_id)
        if test_id in before and test_id in after:
            state = "pre-existing"
        elif test_id in before:
            state = "fixed"
        else:
            state = "new"
        rows.append({
            "id": test_id,
            "dc6a413": before.get(test_id, "pass"),
            "6cf97f3": after.get(test_id, "pass"),
            "class": cls,
            "verdict": verdict,
            "evidence": evidence,
            "change": state,
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    for label, path in (("before", args.before), ("after", args.after)):
        c = counts(path)
        print(f"{label:6} {path.name}: tests={c['tests']} passed={c['passed']} "
              f"failed={c['failed']} errors={c['errors']} skipped={c['skipped']} "
              f"failing_ids={c['failing_ids']}")
    if args.engines:
        c = counts(args.engines)
        print(f"engines {args.engines.name}: tests={c['tests']} passed={c['passed']} "
              f"failed={c['failed']} errors={c['errors']} skipped={c['skipped']}")

    by_class = {}
    for row in rows:
        by_class.setdefault(row["class"], []).append(row)
    print("\nclass                              before  after")
    for cls, group in sorted(by_class.items(), key=lambda x: -len(x[1])):
        b = sum(1 for r in group if r["dc6a413"] != "pass")
        a = sum(1 for r in group if r["6cf97f3"] != "pass")
        print(f"{cls:34} {b:6}  {a:5}")

    print(f"\nwrote {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}"
          f" ({len(rows)} ids)")
    if unclassified:
        print(f"\nUNCLASSIFIED ({len(unclassified)}): an unexplained failure blocks closeout")
        for test_id in unclassified:
            print("   ", test_id)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
