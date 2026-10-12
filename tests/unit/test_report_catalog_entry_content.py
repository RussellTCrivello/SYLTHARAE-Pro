"""Full Entry Report: registered dossier over stored file content."""

from core.reporting import REGISTRY
from core.reporting.datasets import (
    ENTRY_CONTENT_CHAR_LIMIT,
    ENTRY_CONTENT_COUNT_V1,
    ENTRY_CONTENT_ENTRIES_V1,
)
from core.reporting.definitions import ENTRY_CONTENT_V1


class TestRegistered:
    def test_entry_content_is_active_with_the_path_unit(self):
        report = REGISTRY.report("entry_content")
        assert report.status == "active" and report.version == 1
        assert report.unit == "path"
        assert report.layout == "entry_dossier"

    def test_criteria_is_the_only_parameter(self):
        report = REGISTRY.report("entry_content")
        assert [p.name for p in report.parameters] == ["criteria"]
        assert report.datasets == (
            "entry_content.entries@1", "entry_content.count@1")

    def test_the_registry_still_validates(self):
        assert REGISTRY.validate() == []

    def test_help_topic_declared_and_used(self):
        topics = {t.topic for t in REGISTRY.help_topics}
        assert ENTRY_CONTENT_V1.help_topic in topics

    def test_every_reader_role_may_run_it(self):
        report = REGISTRY.report("entry_content")
        for key in report.datasets:
            assert set(REGISTRY.dataset(key).roles) >= set(report.roles)


class TestDatasetContract:
    def test_entries_are_capped_and_ordered(self):
        ds = ENTRY_CONTENT_ENTRIES_V1
        assert ds.semantics == "capped" and ds.row_limit == 100
        assert "ORDER BY p.file_name, p.id" in ds.sql
        assert [c.name for c in ds.columns] == [
            "path_id", "file_name", "file_path", "file_type", "file_size",
            "file_status", "file_date", "date_creation", "source_name",
            "side_name", "coordinates", "analyst_categories", "extracted_text",
            "content_chars", "content_truncated",
        ]

    def test_extracted_text_is_nullable_and_truncation_is_stated(self):
        cols = {c.name: c for c in ENTRY_CONTENT_ENTRIES_V1.columns}
        assert cols["extracted_text"].nullable is True
        assert cols["content_chars"].nullable is True
        assert cols["content_truncated"].nullable is False
        assert cols["content_truncated"].type == "boolean"
        assert str(ENTRY_CONTENT_CHAR_LIMIT) in ENTRY_CONTENT_ENTRIES_V1.sql
        assert "contents_raw" in ENTRY_CONTENT_ENTRIES_V1.sql
        assert "analyst_file_categories" in ENTRY_CONTENT_ENTRIES_V1.sql

    def test_count_is_exact(self):
        ds = ENTRY_CONTENT_COUNT_V1
        assert ds.semantics == "exact" and ds.row_limit == 1
        assert [c.name for c in ds.columns] == ["matched"]
