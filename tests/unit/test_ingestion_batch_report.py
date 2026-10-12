"""Unit tests for the dedicated per-ingestion-batch report."""

from core.reporting.ingestion_template import format_text, render_ingestion_batch
from services.reporting.ingestion_batch import (
    collect_path_ids, collect_type_outcomes, document_from_parts,
    normalize_ids,
)


def test_normalize_and_collect_path_ids():
    assert normalize_ids(["1", 1, 0, "x", 2]) == [1, 2]
    assert collect_path_ids([
        {"database_path_id": 12},
        {"path_id": 12},
        {"database_path_id": "13"},
        "nope",
    ]) == [12, 13]


def test_collect_type_outcomes_from_results():
    outcomes = collect_type_outcomes([
        {"Metadata": {"path": "a.pdf"}, "extracted": True, "text": "ok"},
        {"Metadata": {"path": "b.pdf"}, "error": "read failed"},
        {"file_path": "notes.txt", "reason": "maximum recursion depth"},
    ])
    assert outcomes["pdf"]["total"] == 2
    assert outcomes["pdf"]["failed"] == 1
    assert outcomes["txt"]["skipped"] == 1


def test_template_opens_with_source_and_side_and_is_printable():
    document = document_from_parts(
        identity={"source": "Field Office", "side": "North", "job_id": "J9"},
        counts={
            "files_total": 4,
            "files_processed": 3,
            "files_failed": 1,
            "files_skipped": 0,
            "file_types": 2,
        },
        type_outcomes={
            "pdf": {"total": 3, "completed": 2, "failed": 1},
            "txt": {"total": 1, "completed": 1},
        },
        notes=["Listing is scoped to this batch only."],
    )
    document["categories"] = [{"name": "Finance", "file_count": 2, "occurrence_count": 9}]
    document["category_labels"] = [{"name": "Priority", "description": "Watch", "file_count": 1}]
    document["keywords"] = [{"keyword": "invoice", "category": "Finance", "file_count": 2, "hits": 6}]
    html = render_ingestion_batch(document, interactive=True).decode("utf-8")
    assert 'class="ingest-batch"' in html
    assert "Field Office" in html
    assert "North" in html
    assert "Outcome counts" in html
    assert "Files by type" in html
    assert "Categories assigned" in html
    assert "Category labels assigned" in html
    assert "Keywords assigned" in html
    assert "invoice" in html
    assert "@media print" in html
    assert "window.print" in html
    text = format_text(document)
    assert "Source:" in text and "Field Office" in text
    assert "Side:" in text and "North" in text
    assert "Failed" in text


def test_historical_recovery_prefers_watermark_then_time_window():
    from services.reporting.ingestion_batch import recover_path_ids

    class FakeCur:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            self._sql = sql

        def fetchall(self):
            if "p.id >" in self._sql:
                return [(11,), (12,)]
            return [(99,)]

    ids, method = recover_path_ids(
        FakeCur(), source="Field", side="North", watermark=10,
        started="2026-10-06T07:00:00+00:00", finished="2026-10-06T07:10:00+00:00",
    )
    assert ids == [11, 12]
    assert method == "watermark"

    class EmptyThenWindow:
        def __init__(self):
            self.n = 0

        def execute(self, sql, params=None):
            self._sql = sql
            self.n += 1

        def fetchall(self):
            if "p.id >" in self._sql:
                return []
            return [(21,), (22,)]

    ids, method = recover_path_ids(
        EmptyThenWindow(), source="Field", side="North", watermark=10,
        started="2026-10-06T07:00:00+00:00", finished="2026-10-06T07:10:00+00:00",
    )
    assert ids == [21, 22]
    assert method == "time_window"


def test_type_outcomes_from_processing_status():
    from services.reporting.ingestion_batch import _outcomes_from_status_rows

    rows = [
        {"file_type": "pdf", "processing_status": "processed", "n": 3},
        {"file_type": "pdf", "processing_status": "failed", "n": 1},
        {"file_type": "txt", "processing_status": "skipped", "n": 2},
        {"file_type": "txt", "processing_status": "unsupported", "n": 1},
    ]
    types = {row["file_type"]: row for row in _outcomes_from_status_rows(rows)}
    assert types["pdf"]["processed"] == 3
    assert types["pdf"]["failed"] == 1
    assert types["pdf"]["total"] == 4
    assert types["txt"]["skipped"] == 3


def test_template_uses_the_requested_language():
    from core.reporting.i18n import reader_for
    from core.reporting.ingestion_template import render_ingestion_batch
    from services.reporting.ingestion_batch import document_from_parts

    document = document_from_parts(
        identity={"source": "مكتب", "side": "شمال", "recovery": "stored"},
        counts={"files_total": 1, "files_processed": 1, "files_failed": 0,
                "files_skipped": 0, "file_types": 1},
        type_outcomes={"pdf": {"total": 1, "completed": 1}},
    )
    html = render_ingestion_batch(
        document, reader_for("ar"), interactive=True).decode("utf-8")
    assert 'lang="ar"' in html
    assert 'dir="rtl"' in html
    assert "مكتب" in html
    assert "شمال" in html


def test_cli_report_job_flag_does_not_require_an_ingest_path():
    from apps.cli.main import cli_main

    class FakeManager:
        @classmethod
        def get_instance(cls):
            return cls()

        def get(self, job_id):
            assert job_id == "job-1"
            return {
                "job_id": "job-1",
                "job_type": "ingestion",
                "options": {"source": "Web", "side": "A", "path": "/data/in"},
                "stats": {
                    "files_total": 2,
                    "files_processed": 2,
                    "files_failed": 0,
                    "files_skipped": 0,
                    "files_stored": 2,
                },
                "result_summary": {
                    "batch_report": {
                        "source": "Web",
                        "side": "A",
                        "path_ids": [],
                        "type_outcomes": {"txt": {"total": 2, "completed": 2}},
                    }
                },
                "errors": [],
                "warnings": [],
            }

    import io
    import json
    from contextlib import redirect_stdout

    import services.jobs.manager as manager_mod
    original = manager_mod.JobManager.get_instance
    manager_mod.JobManager.get_instance = FakeManager.get_instance
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = cli_main(["--report-job", "job-1", "--json", "--quiet"])
    finally:
        manager_mod.JobManager.get_instance = original
    assert code == 0
    payload = json.loads(buf.getvalue())
    assert payload["success"] is True
    assert payload["report"]["identity"]["source"] == "Web"
    assert payload["report"]["identity"]["side"] == "A"
    assert payload["report"]["counts"]["files_total"] == 2
