"""Unit: the baseline tools classify every id, or refuse to close the round.

`tools/audit/r22_baseline.py` decides whether a failing test is pre-existing, a
regression or a property of the environment. That decision is the one the audit
report leans on, so it gets a test: the tool must name every id it is given and
must exit non-zero when it cannot, because "unclassified" is what blocks the
round from closing.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

baseline = importlib.import_module("tools.audit.r22_baseline")
reconcile = importlib.import_module("tools.audit.r22_reconcile")


def _junit(path: Path, cases, skipped=()):
    """Write the smallest JUnit file that still has the shape pytest emits."""
    body = []
    for classname, name, status in cases:
        inner = ""
        if status in ("failure", "error"):
            inner = f'<{status} message="boom">trace</{status}>'
        body.append(f'<testcase classname="{classname}" name="{name}">{inner}</testcase>')
    for classname, name in skipped:
        body.append(f'<testcase classname="{classname}" name="{name}">'
                    '<skipped message="no sample"/></testcase>')
    path.write_text(
        '<testsuites><testsuite name="pytest" tests="%d" failures="%d" errors="%d" '
        'skipped="%d" time="0">%s</testsuite></testsuites>' % (
            len(cases) + len(skipped),
            sum(1 for c in cases if c[2] == "failure"),
            sum(1 for c in cases if c[2] == "error"),
            len(skipped),
            "".join(body)),
        encoding="utf-8")
    return path


def test_the_module_is_recovered_from_pytest_classname():
    # pytest puts the class in `classname` and only the test name in `name`;
    # the rule table is keyed by file, so the class must be dropped, not kept.
    assert baseline.module_of_id(
        "tests.unit.test_component_library.TestAdoption::test_x") == \
        "tests/unit/test_component_library.py"
    assert baseline.module_of_id("tests.unit.test_x::test_y") == "tests/unit/test_x.py"


def test_the_counts_come_from_the_suite_totals(tmp_path):
    path = _junit(tmp_path / "run.xml",
                  [("tests.unit.test_a.TestB", "test_f", "failure"),
                   ("tests.unit.test_a.TestB", "test_e", "error"),
                   ("tests.unit.test_a.TestB", "test_ok", None)],
                  skipped=[("tests.unit.test_a.TestB", "test_s")])
    got = baseline.counts(path)
    assert got == {"tests": 4, "passed": 1, "failed": 1, "errors": 1,
                   "skipped": 1, "failing_ids": 2}


def test_a_skip_is_not_counted_as_a_pass(tmp_path):
    path = _junit(tmp_path / "run.xml",
                  [("tests.unit.test_a.TestB", "test_ok", None)],
                  skipped=[("tests.unit.test_a.TestB", "test_s")])
    got = baseline.counts(path)
    assert got["passed"] == 1 and got["skipped"] == 1 and got["tests"] == 2


def test_an_id_in_the_engine_run_is_classed_environment():
    cls, _, evidence = baseline.classify_id(
        "tests.unit.test_ocr_matrix.TestNoText::test_blank", {"tests.unit.test_ocr_matrix.TestNoText::test_blank"})
    assert cls == "ENV"
    assert "passes in the venv with OCR" in evidence


def test_an_ocr_module_without_an_engine_is_environment_not_code():
    cls, _, _ = baseline.classify_id(
        "tests.unit.test_embedded_images.TestX::test_y", set())
    assert cls == "ENV-OCR"


def test_a_known_docs_failure_uses_the_repository_vocabulary():
    cls, verdict, _ = baseline.classify_id(
        "tests.unit.test_interface_docs.TestRegistryEvidence::test_x", set())
    assert cls == "DOCS-NOT-COMMITTED"
    assert "D-7" in verdict


def test_an_unknown_id_is_reported_as_unclassified():
    cls, _, _ = baseline.classify_id("tests/unit/test_nope.py::test_x", set())
    assert cls == "UNCLASSIFIED"


def test_main_exits_non_zero_when_an_id_cannot_be_classified(tmp_path):
    before = _junit(tmp_path / "before.xml",
                    [("tests.unit.test_nope.TestX", "test_y", "failure")])
    after = _junit(tmp_path / "after.xml",
                   [("tests.unit.test_nope.TestX", "test_y", "failure")])
    out = tmp_path / "ids.csv"
    assert baseline.main(["--before", str(before), "--after", str(after),
                          "--out", str(out)]) == 1
    assert "test_nope" in out.read_text(encoding="utf-8")


def test_a_fixed_id_is_classed_fixed_and_does_not_block_closeout(tmp_path):
    before = _junit(tmp_path / "before.xml",
                    [("tests.unit.test_nope.TestX", "test_y", "failure")])
    after = _junit(tmp_path / "after.xml",
                   [("tests.unit.test_nope.TestX", "test_y", None)])
    out = tmp_path / "ids.csv"
    assert baseline.main(["--before", str(before), "--after", str(after),
                          "--out", str(out)]) == 0
    row = out.read_text(encoding="utf-8")
    assert ",FIXED," in row


def test_the_reconciliation_reads_a_skip_as_a_skip(tmp_path):
    path = _junit(tmp_path / "run.xml",
                  [("tests.unit.test_a.TestB", "test_f", "failure")],
                  skipped=[("tests.unit.test_a.TestB", "test_s")])
    assert reconcile.skipped_ids(path) == {"tests.unit.test_a.TestB::test_s"}


@pytest.mark.parametrize("status", ["failure", "error"])
def test_both_failure_kinds_are_failing_ids(tmp_path, status):
    path = _junit(tmp_path / "run.xml", [("tests.unit.test_a.TestB", "test_x", status)])
    assert baseline.failing_ids(path) == {"tests.unit.test_a.TestB::test_x": status}
