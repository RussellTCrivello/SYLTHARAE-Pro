"""Unit tests for catalog profile analyses (horizon / place / keyword / category)."""

from __future__ import annotations

from core.analytics.kinds import MEASURED, NOT_MEASURABLE
from core.reporting import REGISTRY


def _ds(key, rows, *, truncated=False, semantics="capped", columns=None):
    cols = columns or []
    return {
        "dataset_key": key,
        "semantics": semantics,
        "truncated": truncated,
        "columns": [{"name": c} for c in cols],
        "rows": rows,
    }


def test_horizon_profile_speaks_five_voices_over_bucket_counts():
    analysis = REGISTRY.analysis("horizon_profile@1")
    rows = [
        {"signal_id": 1, "bucket": "week", "event_date": "2026-10-05"},
        {"signal_id": 2, "bucket": "week", "event_date": "2026-10-06"},
        {"signal_id": 3, "bucket": "overdue", "event_date": "2026-09-01"},
    ]
    result = analysis.compute(
        {"horizon.signals@1": _ds(
            "horizon.signals@1", rows,
            columns=["bucket", "event_date", "signal_id"])},
        {})
    assert result["state"] == MEASURED
    assert result["measures"]["signals"] == 3
    assert result["measures"]["week"] == 2
    assert result["measures"]["top_bucket"] == "week"
    voices = {v["voice"] for v in result["narrative"]["voices"]}
    assert voices == {"measure", "finding", "confidence", "consequence", "caveat"}
    from core.analytics.narrative import render, source_ngettext
    lines = render(result["narrative"], lambda s: s, ngettext=source_ngettext)
    joined = " ".join(line["text"] for line in lines)
    assert "week" in joined and "overdue" in joined


def test_horizon_profile_empty_listing_is_not_measurable():
    analysis = REGISTRY.analysis("horizon_profile@1")
    result = analysis.compute(
        {"horizon.signals@1": _ds(
            "horizon.signals@1", [],
            columns=["bucket", "event_date", "signal_id"])},
        {})
    assert result["state"] == NOT_MEASURABLE
    assert result["reason"] == "none"


def test_place_profile_keeps_ambiguity_separate():
    analysis = REGISTRY.analysis("place_profile@1")
    rows = [{
        "place_label": "Tripoli", "feature_type": "city",
        "identified_contents": 2, "identified_occurrences": 4,
        "ambiguous_contents": 1, "ambiguous_occurrences": 3,
    }]
    result = analysis.compute(
        {"entity_place.mentions@1": _ds(
            "entity_place.mentions@1", rows,
            columns=["place_label", "feature_type", "identified_contents",
                     "identified_occurrences", "ambiguous_contents",
                     "ambiguous_occurrences"])},
        {})
    assert result["state"] == MEASURED
    assert result["measures"]["identified"] == 4
    assert result["measures"]["ambiguous"] == 3
    assert result["measures"]["ambiguous_share"] == round(3 / 7 * 100, 2)


def test_keyword_profile_names_the_widest_keyword():
    analysis = REGISTRY.analysis("keyword_profile@1")
    rows = [
        {"label": "alpha", "category_name": "A", "contents": 3,
         "occurrences": 5, "corpus_contents": 10},
        {"label": "beta", "category_name": "B", "contents": 0,
         "occurrences": 0, "corpus_contents": 10},
    ]
    result = analysis.compute(
        {"keyword_intelligence.matches@1": _ds(
            "keyword_intelligence.matches@1", rows,
            columns=["label", "category_name", "contents", "occurrences",
                     "corpus_contents"])},
        {})
    assert result["state"] == MEASURED
    assert result["measures"]["present"] == 1
    assert result["measures"]["top_label"] == "alpha"


def test_category_profile_warns_on_overlap_in_caveat():
    analysis = REGISTRY.analysis("category_profile@1")
    rows = [{
        "category_name": "Security", "member_words": 4, "contents": 2,
        "occurrences": 6, "corpus_contents": 5,
    }]
    result = analysis.compute(
        {"category_analysis.summary@1": _ds(
            "category_analysis.summary@1", rows,
            columns=["category_name", "member_words", "contents",
                     "occurrences", "corpus_contents"])},
        {})
    assert result["state"] == MEASURED
    caveat = next(v for v in result["narrative"]["voices"] if v["voice"] == "caveat")
    assert any("overlap" in s["key"] for s in caveat["sentences"])


def test_active_catalog_reports_carry_profiles():
    assert REGISTRY.report("horizon").analyses == ("horizon_profile@1",)
    assert REGISTRY.report("entity_place").analyses == ("place_profile@1",)
    assert REGISTRY.report("keyword_intelligence").analyses == ("keyword_profile@1",)
    assert REGISTRY.report("category_analysis").analyses == ("category_profile@1",)
