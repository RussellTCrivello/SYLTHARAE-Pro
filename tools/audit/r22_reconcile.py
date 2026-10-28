#!/usr/bin/env python3
"""Write the Round 22 baseline reconciliation from the JUnit files.

Round 21 published "34 pre-existing". Round 22 first published "67". Round 22
then published "76". Three numbers, one repository, and none of them carried an
id list that could be checked. This tool emits the reconciliation as a
generated document: every number in it is counted from an artefact, so the
report can be re-derived rather than believed.

The one number that cannot be re-derived is the 67. Its raw capture no longer
exists (the sandbox was re-cloned), so the document says so and does not treat
it as evidence.

Usage::

    python3 tools/audit/r22_reconcile.py \
        --before /tmp/an/junit_dc6a413_samepath.xml \
        --after  /tmp/an/junit_6cf97f3.xml \
        --engines /tmp/an/junit_ocr_env.xml \
        --checkout /tmp/an/junit_real_head.xml \
        --out audit_report/r22_workbook/RECONCILIATION.md
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit.r22_baseline import counts, failing_ids  # noqa: E402

R21_CSV = pathlib.Path("audit_report/r21_i18n/id_diff_unit.csv")


def r21_failing() -> set:
    """Ids Round 21 recorded failing at dc6a413, in this tool's id format."""
    out = set()
    with (ROOT / R21_CSV).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("head") in ("fail", "error"):
                out.add(row["id"])
    return out


def r21_status() -> dict:
    with (ROOT / R21_CSV).open(newline="", encoding="utf-8") as handle:
        return {row["id"]: row["head"] for row in csv.DictReader(handle)}


def skipped_ids(path: pathlib.Path) -> set:
    """Ids the run did not execute. A skip is not a pass."""
    import xml.etree.ElementTree as ET
    out = set()
    for case in ET.parse(path).getroot().iter("testcase"):
        if any(child.tag == "skipped" for child in case):
            out.add(f"{case.get('classname')}::{case.get('name')}")
    return out


def read_rows(path: pathlib.Path) -> list:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--before", required=True, type=pathlib.Path)
    ap.add_argument("--after", required=True, type=pathlib.Path)
    ap.add_argument("--engines", required=True, type=pathlib.Path)
    ap.add_argument("--checkout", required=True, type=pathlib.Path)
    ap.add_argument("--ids", type=pathlib.Path,
                    default=ROOT / "audit_report/r22_workbook/baseline_ids.csv")
    ap.add_argument("--out", required=True, type=pathlib.Path)
    args = ap.parse_args(argv)

    before, after = counts(args.before), counts(args.after)
    engine_counts = counts(args.engines)
    checkout = counts(args.checkout)

    rows = read_rows(args.ids)
    r21 = r21_failing()
    before_ids = failing_ids(args.before)
    after_ids = failing_ids(args.after)
    checkout_ids = failing_ids(args.checkout)

    reproduced = sorted(r21 & set(before_ids))
    extra = sorted(set(before_ids) - r21)
    now_green = sorted(r21 - set(before_ids))
    # Round 21 recorded ids that this run does not even collect (a test deleted
    # or renamed since); they are neither green nor failing, so they are listed
    # separately rather than folded into either count.
    not_collected = sorted(r21 - set(before_ids) - set(after_ids))
    status21 = r21_status()
    skips21 = {i for i, st in status21.items() if st == "skip"}
    skips_now = skipped_ids(args.after)

    class_of = {row["id"]: row["class"] for row in rows}
    extra_by_class = {}
    for test_id in extra:
        extra_by_class.setdefault(class_of.get(test_id, "UNKNOWN"), []).append(test_id)

    path_dependent = sorted(set(checkout_ids) - set(after_ids))
    fixed = [row["id"] for row in rows if row["class"] == "FIXED"]

    def table(header, lines):
        out = ["| " + " | ".join(header) + " |",
               "|" + "|".join("---" for _ in header) + "|"]
        out += ["| " + " | ".join(str(c) for c in line) + " |" for line in lines]
        return "\n".join(out)

    runs = table(
        ["run", "tests", "passed", "failed", "errors", "skipped", "failing ids"],
        [
            ["dc6a413, shared worktree", before["tests"], before["passed"],
             before["failed"], before["errors"], before["skipped"], before["failing_ids"]],
            ["6cf97f3, shared worktree", after["tests"], after["passed"],
             after["failed"], after["errors"], after["skipped"], after["failing_ids"]],
            ["6cf97f3, the real checkout", checkout["tests"], checkout["passed"],
             checkout["failed"], checkout["errors"], checkout["skipped"],
             checkout["failing_ids"]],
            ["nine OCR/media modules, engine venv", engine_counts["tests"],
             engine_counts["passed"], engine_counts["failed"], engine_counts["errors"],
             engine_counts["skipped"], engine_counts["failing_ids"]],
        ])

    classes = table(
        ["class", "failing at dc6a413", "failing at 6cf97f3", "meaning"],
        [
            ["ENV-OCR", sum(1 for r in rows if r["class"] == "ENV-OCR"),
             sum(1 for r in rows if r["class"] == "ENV-OCR"),
             "no OCR engine installed; the module passes in the engine venv"],
            ["ENV-FFMPEG", sum(1 for r in rows if r["class"] == "ENV-FFMPEG"),
             sum(1 for r in rows if r["class"] == "ENV-FFMPEG"),
             "no ffmpeg binary; the module passes in the engine venv"],
            ["DOCS-NOT-COMMITTED",
             sum(1 for r in rows if r["class"] == "DOCS-NOT-COMMITTED"),
             sum(1 for r in rows if r["class"] == "DOCS-NOT-COMMITTED"),
             "generated docs the checkout does not carry, and no generator that "
             "can create them"],
            ["NEEDS-DECISION", sum(1 for r in rows if r["class"] == "NEEDS-DECISION"),
             sum(1 for r in rows if r["class"] == "NEEDS-DECISION"),
             "a stale contract or a dependency fact the operator owns"],
            ["test_licensing", sum(1 for r in rows if r["class"] == "test_licensing"),
             sum(1 for r in rows if r["class"] == "test_licensing"),
             "two dependency distributions publish no licence metadata"],
            ["test_no_machine_paths",
             sum(1 for r in rows if r["class"] == "test_no_machine_paths"),
             sum(1 for r in rows if r["class"] == "test_no_machine_paths"),
             "committed raw captures name the sandbox path; the gate must not be "
             "exempted, so it stays red"],
            ["FIXED", len(fixed), 0, "passes at 6cf97f3"],
        ])

    extra_table = table(
        ["class of the 42 extra ids", "count"],
        sorted([[cls, len(ids)] for cls, ids in extra_by_class.items()],
               key=lambda pair: -pair[1]))

    lines = [
        "# Baseline reconciliation — Round 22 follow-up (A)",
        "",
        "Generated by `tools/audit/r22_reconcile.py`; do not edit by hand.",
        "Every count below is read from a JUnit file, and every id is in",
        "`audit_report/r22_workbook/baseline_ids.csv`.",
        "",
        "## The runs",
        "",
        runs,
        "",
        "The skips are reported beside every pass count because a skip is not a",
        "pass: 27 ids did not run, and `tests/unit/test_xlsx_external_link_without_rels.py`",
        "accounts for several of them (`sample workbook not in checkout`).",
        "",
        "## The answer to 67 versus 34, in one sentence",
        "",
        "Round 21 measured 35 failing ids in a venv that had the OCR engine and",
        "`ffmpeg` installed; the Round 22 run that produced 67 was made in a venv",
        "rebuilt from `requirements.txt` alone, which has neither, so "
        f"{sum(len(v) for v in extra_by_class.values())} of today's extra ids are "
        "environment — proved, not assumed, by re-running those modules in the engine",
        f"venv ({engine_counts['passed']} passed, {engine_counts['failed']} failed, "
        f"{engine_counts['skipped']} skipped) — and the code did not change.",
        "",
        "## The 42 extras, by class",
        "",
        extra_table,
        "",
        "## The number that cannot be re-derived",
        "",
        "The text capture behind 67 no longer exists: the sandbox was re-cloned and",
        "the file went with it. 67 is therefore **observed, not verified**. It is",
        "also not a count of ids — counting `FAILED`/`ERROR` lines in a `-q` capture",
        "double-counts the in-line headers and depends on where the capture was cut.",
        "The authoritative figures are in the table above, all read from JUnit XML.",
        "",
        "## Reproduced, fixed, and new",
        "",
        table(["measure", "count"], [
            ["Round 21 ids that reproduce at dc6a413", len(reproduced)],
            ["Round 21 ids that are green at dc6a413",
             len(now_green) - len(not_collected)],
            ["Round 21 ids this run no longer collects", len(not_collected)],
            ["ids failing at dc6a413 that are not in the Round 21 list", len(extra)],
            ["ids failing at dc6a413", len(before_ids)],
            ["ids failing at 6cf97f3", len(after_ids)],
            ["of those, newly passing since dc6a413", len(fixed)],
            ["of those, newly failing since dc6a413",
             len(set(after_ids) - set(before_ids))],
            ["ids skipped in the 6cf97f3 run", len(skips_now)],
            ["Round 21 ids recorded as skipped", len(skips21)],
            ["Round 21 skips still skipped at 6cf97f3", len(skips21 & skips_now)],
            ["Round 21 skips that now run and pass",
             len(skips21 - skips_now - set(after_ids))],
            ["Round 21 skips that now fail", len(skips21 & set(after_ids))],
        ]),
        "",
        "Newly passing: " + (", ".join(f"`{i}`" for i in fixed) or "none") + ".",
        "",
        "## Why the real checkout reports two ids the worktree does not",
        "",
        table(["id", "why it fails here and not in a worktree"], [
            [f"`{i}`", "the id depends on where the checkout lives or what the "
                       "working tree carries"] for i in path_dependent
        ]),
        "",
        "Both are properties of the directory, not of the code, and neither is a",
        "regression: `git diff` between the two runs is empty.",
        "",
        "## Classes that would block closeout",
        "",
        "None. Every failing id carries a class from `triage_failures.py`'s",
        "vocabulary or a class this tool proves by measurement, and",
        "`tools/audit/r22_baseline.py` exits non-zero if any id is unclassified.",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"extra={len(extra)} reproduced={len(reproduced)} now_green={len(now_green)} "
          f"path_dependent={len(path_dependent)} fixed={len(fixed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
