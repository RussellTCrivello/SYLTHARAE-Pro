"""Dedicated Full Entry Report HTML template."""

from core.reporting.entry_template import render_entry_dossier
from core.reporting.i18n import reader_for
from core.reporting.render import render as render_artifact


def _document(**overrides):
    run = {
        "report_key": "entry_content@1", "id": 9, "report_id": "entry_content",
        "report_version": 1, "definition_fingerprint": "f" * 64,
        "parameters_fingerprint": "a" * 64, "criteria_fingerprint": "b" * 64,
        "saved_search_id": None, "requester_username": "u", "requester_role": "analyst",
        "snapshot": "0/1", "snapshot_at": "2026-01-01T00:00:00+00:00",
        "isolation_level": "repeatable read, read only", "generator_version": "runner/2",
        "requested_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:00+00:00",
    }
    run.update(overrides.get("run", {}))
    rows = overrides.get("rows", [{
        "path_id": 11,
        "file_name": "briefing.txt",
        "file_path": "/inbox/briefing.txt",
        "file_type": "txt",
        "file_size": 120,
        "file_status": "Read",
        "file_date": "2026-01-02",
        "date_creation": "2026-01-01",
        "source_name": "Alpha",
        "side_name": "North",
        "coordinates": None,
        "analyst_categories": "Priority",
        "extracted_text": "The full stored body of this entry.\nSecond line.",
        "content_chars": 48,
        "content_truncated": False,
    }])
    return {
        "report": {
            "id": "entry_content", "version": 1, "title": "Full Entry Report",
            "unit": "path",
            "description": "A printable dossier of every matched file: the identity "
                           "and classifications entered or assigned for that entry, "
                           "and the full extracted text stored for it. Each entry is "
                           "its own section. When the listing or a single text is "
                           "shortened, the report says so.",
            "help_summary": "Produces a printable dossier of the files your criteria "
                            "select: each entry's stored identity, the source and side "
                            "and analyst categories assigned to it, and the full "
                            "extracted text. The readable HTML uses a dedicated "
                            "template with one section per entry, ready to print. A "
                            "shortened listing or a shortened text is stated, never "
                            "hidden.",
            "layout": "entry_dossier",
        },
        "run": run,
        "datasets": [{
            "dataset_key": "entry_content.entries@1",
            "dataset_fingerprint": "c" * 64, "query_fingerprint": "d" * 64,
            "semantics": "capped", "row_limit": 100,
            "row_count": len(rows), "truncated": overrides.get("truncated", False),
            "columns": [{"name": "extracted_text"}, {"name": "file_name"}],
            "rows": rows,
        }, {
            "dataset_key": "entry_content.count@1",
            "dataset_fingerprint": "e" * 64, "query_fingerprint": "g" * 64,
            "semantics": "exact", "row_limit": 1,
            "row_count": 1, "truncated": False,
            "columns": [{"name": "matched"}],
            "rows": [{"matched": overrides.get("matched", len(rows))}],
        }],
        "analyses": [],
        "preview": overrides.get("preview", False),
    }


class TestDedicatedTemplate:
    def test_each_entry_is_its_own_section_with_full_text(self):
        html = render_entry_dossier(_document(), reader_for("en"))[0].decode("utf-8")
        assert 'class="entry-dossier"' in html
        assert 'id="entry-1"' in html
        assert "briefing.txt" in html
        assert "/inbox/briefing.txt" in html
        assert "Priority" in html
        assert "The full stored body of this entry." in html
        assert "Second line." in html
        assert "@media print" in html
        assert "window.print" not in html, "artifacts must not embed scripts"

    def test_html_is_escaped(self):
        doc = _document(rows=[{
            "path_id": 1, "file_name": "<script>x</script>", "file_path": "a",
            "file_type": "txt", "file_size": 1, "file_status": "Read",
            "file_date": "2026-01-01", "date_creation": "2026-01-01",
            "source_name": "S", "side_name": "T", "coordinates": None,
            "analyst_categories": None,
            "extracted_text": "<img src=x onerror=alert(1)>",
            "content_chars": 10, "content_truncated": False,
        }])
        html = render_entry_dossier(doc, reader_for("en"))[0].decode("utf-8")
        assert "<script>x</script>" not in html
        assert "&lt;script&gt;x&lt;/script&gt;" in html
        assert "<img src=x" not in html
        assert "&lt;img src=x" in html

    def test_shortened_text_is_stated(self):
        doc = _document(rows=[{
            "path_id": 1, "file_name": "long.txt", "file_path": "p",
            "file_type": "txt", "file_size": 1, "file_status": "Read",
            "file_date": "2026-01-01", "date_creation": "2026-01-01",
            "source_name": "S", "side_name": "T", "coordinates": None,
            "analyst_categories": None,
            "extracted_text": "prefix",
            "content_chars": 400000, "content_truncated": True,
        }])
        html = render_entry_dossier(doc, reader_for("en"))[0].decode("utf-8")
        assert "Content shortened" in html
        assert "400000" in html

    def test_interactive_preview_adds_print_control(self):
        html = render_entry_dossier(
            _document(preview=True), reader_for("en"),
            interactive=True, auto_print=True,
        )[0].decode("utf-8")
        assert "window.print" in html
        assert "dossier-toolbar" in html
        assert "Provenance" not in html

    def test_the_artifact_renderer_selects_the_dossier_layout(self):
        out = render_artifact(_document(), "html", None, "en")
        text = out.content.decode("utf-8")
        assert 'class="entry-dossier"' in text
        assert "The full stored body of this entry." in text
        assert "<table><thead>" not in text, (
            "the dossier must not fall back to the generic dataset table")

    def test_search_results_html_is_unchanged_table_layout(self):
        from tests.unit.test_report_rendering_languages import _document as search_doc

        text = render_artifact(search_doc(), "html", None, "en").content.decode("utf-8")
        assert "entry-dossier" not in text
        assert "Provenance" in text
