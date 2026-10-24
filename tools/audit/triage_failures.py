#!/usr/bin/env python
"""Turn the JUnit results into the audit's failing-test table.

Nothing here is typed by hand: the file, the test name and the message come
from the XML the suite wrote. Only the *category*, the *decision id* and the
*proposed action* come from the rule table below, which is keyed by test file
and (where one file mixes causes) by test-name prefix.

Categories (the vocabulary the audit report uses)
-------------------------------------------------
``PROJECT-DEFECT``          the product is wrong; fix it plus a regression test
``TEST-ENCODES-OLD-SCHEMA`` the test asserts a migration, constraint name or
                            column the frozen chain (m0001-m0003) does not have
``DOCS-NOT-COMMITTED``      generated documentation the checkout does not carry
``NEEDS-DECISION``          a decision the operator owns; the test is not edited
``ENV``                     caused by the sandbox/environment, not the product
``COLLATERAL``              caused by another failure or by test order

Usage::

    python tools/audit/triage_failures.py \\
        audit_report/evidence_final/junit_unit.xml \\
        audit_report/evidence_final/junit_rest.xml
"""

from __future__ import annotations

import argparse
import collections
import csv
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "audit_report" / "findings"

#: (test file, test-name prefix or None) -> (category, decision, cause, action)
RULES = [
    # ---------------- decisions the operator owns -------------------------
    ("tests/integration/test_scenario_engine_pg.py", "test_sql_priority", "PROJECT-DEFECT",
     "D-1", "the SQL priority and the Python rule disagree (NotificationPriority enum vs "
     "the stored string)", "OPEN: the inconsistency is real; fix the rule or the query, "
     "the test is not edited"),
    ("tests/integration/test_scenario_engine_pg.py", None, "NEEDS-DECISION",
     "D-1", "helper selects alerts.rule_id / rule_evaluation_id; the frozen table has "
     "scenario_id / scenario_evaluation_id", "do-not-edit test; helper rewrite needs "
     "your approval (option a in D-1)"),
    ("tests/integration/test_places_crud_pg.py", None, "NEEDS-DECISION",
     "D-4", "place_key naming and a 500 in the admin curation path", "do-not-edit test"),
    ("tests/integration/test_signal_explorer_pg.py", None, "NEEDS-DECISION",
     "D-4", "the explorer returns no rows for the seeded fixture", "do-not-edit test"),
    ("tests/unit/test_identifiers_intel.py", None, "NEEDS-DECISION",
     "D-4", "email identifiers are reported under a different key", "do-not-edit test"),
    ("tests/integration/test_title_parent_linkage.py", None, "NEEDS-DECISION",
     "D-4", "the test inserts 5 positional args into a repository that takes 4",
     "do-not-edit test"),
    ("tests/unit/test_notification_volume_guards.py", None, "NEEDS-DECISION",
     "D-10", "demands a m0014 alerts-index migration the chain does not have",
     "reverted to 2670f3b as instructed; failure stays visible"),
    ("tests/unit/test_component_library.py", "test_the_audit_counts", "NEEDS-DECISION",
     "—", "hand-written table count is 10 at 2670f3b (expected 9) and 11 now that "
     "reports.html carries a raw table", "migrate the two tables onto record_table, "
     "or change the documented count"),
    # ---------------- tests that encode a schema this checkout lacks ------
    ("tests/integration/test_signal_ingestion.py", None, "TEST-ENCODES-OLD-SCHEMA",
     "D-2", "asserts ck_content_signals_* constraint names; the frozen schema names "
     "them content_signals_check*", "update the expected names (behaviour asserts pass)"),
    ("tests/integration/test_saved_searches_pg.py", None, "TEST-ENCODES-OLD-SCHEMA",
     "D-2", "asserts ck_saved_searches_*; the frozen schema uses saved_searches_*_check",
     "update the expected names"),
    ("tests/integration/test_notification_accuracy.py", None, "TEST-ENCODES-OLD-SCHEMA",
     "D-2", "expects idx_alerts_* index names from a migration this chain does not have",
     "update to the live index names"),
    ("tests/integration/test_db_integrity_audit.py", "test_no_duplicate", "NEEDS-DECISION",
     "D-8", "duplicate index shapes exist in the frozen baseline",
     "register them in DUPLICATION_REGISTER.md, or drop in a migration"),
    ("tests/integration/test_db_integrity_audit.py", None, "TEST-ENCODES-OLD-SCHEMA",
     "D-3", "imports database.migrations.m0039_vocabulary_constraints, which never "
     "existed in this chain", "rewrite against m0001-m0003"),
    ("tests/integration/test_structured_content_display.py", None, "TEST-ENCODES-OLD-SCHEMA",
     "D-3", "asserts schema version >= 0010; the frozen chain ends at 0003",
     "rewrite against m0001-m0003"),
    ("tests/integration/test_places_pg.py", None, "TEST-ENCODES-OLD-SCHEMA",
     "D-4", "expects gazetteer seed rows from a migration; seeding is frozen out of scope",
     "either seed deliberately (needs your approval) or drop the seed assertions"),
    # ---------------- generated documentation the checkout lacks ---------
    ("tests/unit/test_interface_docs.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/INTERFACE_REGISTRY.md, REGISTRY_EVIDENCE.md, endpoint_inventory.json are "
     "generated and uncommitted", "commit the generated set after your review"),
    ("tests/unit/test_component_library.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/COMPONENT_LIBRARY.md is generated and uncommitted", "commit after review"),
    ("tests/unit/test_action_lifecycle_components.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/COMPONENT_LIBRARY.md", "commit after review"),
    ("tests/unit/test_action_surface_audit.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/ACTION_SURFACE_AUDIT.md", "commit after review"),
    ("tests/unit/test_architecture_diagrams.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/ARCHITECTURE.md", "commit after review"),
    ("tests/unit/test_experience_contract.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/EXPERIENCE_CONTRACT.md", "commit after review"),
    ("tests/unit/test_interface_lifecycle.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/INTERFACE_REGISTRY.md", "commit after review"),
    ("tests/unit/test_screen_inspector.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/SCREEN_INSPECTOR_EVIDENCE.md", "commit after review"),
    ("tests/unit/test_ocr_provenance_docs.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/DOMAIN_MODEL.md", "commit after review"),
    ("tests/unit/test_windows_offline_kit.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/windows/DEPENDENCY_INVENTORY.md", "commit after review"),
    ("tests/unit/test_reference_docs.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "the generated reference pages under docs/reference are stale", 
     "run tools/docs/generate_reference.py and commit"),
    ("tests/integration/test_interface_coverage.py", None, "DOCS-NOT-COMMITTED", "D-7",
     "docs/REGISTRY_EVIDENCE.md and docs/endpoint_inventory.json",
     "commit after review"),
    # ---------------- licensing / missing module / translation -----------
    ("tests/unit/test_licensing.py", None, "NEEDS-DECISION", "D-6",
     "pyproject has no licence field, README states none, THIRD_PARTY_NOTICES.md is "
     "absent, pymupdf-layout reports no usable licence metadata",
     "close the metadata gaps (option a in D-6)"),
    ("tests/unit/test_analytics_measures.py", None, "NEEDS-DECISION", "D-5",
     "imports core.reporting, which does not exist", "build the facade (option a)"),
    ("tests/unit/test_bandit_triage_fixes.py", None, "NEEDS-DECISION", "D-5",
     "imports core.reporting.model", "build the facade (option a)"),
    ("tests/unit/test_gazetteer_packaging.py", None, "NEEDS-DECISION", "D-4",
     "data/gazetteer/SOURCES.md is not in the checkout",
     "add the packaging file (option a)"),
    ("tests/integration/test_translation_coverage.py", None, "NEEDS-DECISION", "—",
     "284-359 untranslated/fuzzy entries per locale",
     "needs a translator; filling them is a decision, not a code change"),
    # ---------------- environment, disproved by re-running ---------------
    ("tests/security/test_rate_limiting.py", None, "ENV", "—",
     "the suite inherited RATE_LIMIT_* from the browser-walk launch; the limiter reads "
     "them at import", "re-run at product defaults: 16 passed (see R3 report §c)"),
    ("tests/integration/test_startup_upgrade_path.py", None, "ENV", "—",
     "CREATE DATABASE ... TEMPLATE was refused because another module's pool still held "
     "the source database (ObjectInUse)", "fixed by building the private database from "
     "the migrations instead of cloning it (test isolation, no schema change)"),
]


def classify(path, name):
    best = None
    for rule_path, prefix, category, decision, cause, action in RULES:
        if rule_path != path or (prefix and not name.startswith(prefix)):
            continue
        score = len(prefix or "")
        if best is None or score > best[0]:
            best = (score, category, decision, cause, action)
    if best is None:
        return ("UNCLASSIFIED", "—", "no rule matched this file",
                "classify before claiming the suite is triaged")
    return best[1:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("junit", nargs="+",
                    help="the JUnit XMLs of one clean run")
    ap.add_argument("--out", default="audit_report/findings/failure_triage.csv")
    args = ap.parse_args(argv)

    rows = []
    totals = collections.Counter()
    for source in args.junit:
        root = ET.parse(ROOT / source).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        totals["tests"] += int(suite.get("tests", 0))
        totals["failures"] += int(suite.get("failures", 0))
        totals["errors"] += int(suite.get("errors", 0))
        totals["skipped"] += int(suite.get("skipped", 0))
        totals["suites"] += 1
        for tc in suite.iter("testcase"):
            bad = [c for c in tc if c.tag in ("failure", "error")]
            if not bad:
                continue
            cls = tc.get("classname", "")
            parts = [p for p in cls.split(".") if not p[:1].isupper()]
            path = "/".join(parts) + ".py"
            message = (bad[0].get("message") or bad[0].text or "").strip()
            first = message.split("\n")[0][:200]
            category, decision, cause, action = classify(path, tc.get("name", ""))
            rows.append((path, tc.get("name", ""), bad[0].tag, first, category,
                         decision, cause, action))

    rows.sort(key=lambda r: (r[4], r[0], r[1]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (ROOT / args.out).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "test", "outcome", "message", "category", "decision",
                    "cause", "proposed_action"])
        w.writerows(rows)

    counts = collections.Counter(r[4] for r in rows)
    print(f"XMLs: {args.junit}")
    print(f"tests: {totals['tests']}  failures: {totals['failures']}  "
          f"errors: {totals['errors']}  skipped: {totals['skipped']}")
    print(f"failing/erroring test cases: {len(rows)}")
    for category, count in counts.most_common():
        print(f"  {category:26s} {count}")
    print(f"wrote {args.out}")
    return 1 if counts.get("UNCLASSIFIED") else 0


if __name__ == "__main__":
    sys.exit(main())
