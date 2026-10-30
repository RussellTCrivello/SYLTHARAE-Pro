"""Unit tests for structured identifier detection."""

from core.detection import identifiers_intel as ii


def test_detects_email_phone_ipv4_and_links_to_sentence():
    text = "Contact alice@example.org or +1 (415) 555-0199. Server 192.168.0.1."
    result = ii.detect(text)
    # The detector reports one signal_type - "identifier" - and carries the
    # kind of identifier in its evidence (core/detection/identifiers_intel.py,
    # SIGNAL_EMAIL..SIGNAL_URL vs SIGNAL_IDENTIFIER). Selecting by kind is what
    # the explorer's identifier presets do; the old assertions selected by
    # signal_type, which this detector stopped using.
    by_kind = {s.evidence["kind"]: s for s in result.signals}
    assert set(by_kind) == {"email", "phone", "ipv4"}
    assert {s.signal_type for s in result.signals} == {"identifier"}
    assert by_kind["email"].value == "alice@example.org"
    assert by_kind["email"].surface == "alice@example.org"
    assert "alice@example.org" in (by_kind["email"].sentence or "")
    assert by_kind["ipv4"].value == "192.168.0.1"
    assert (by_kind["phone"].value.replace("+", "").endswith("4155550199")
            or "4155550199" in by_kind["phone"].value)


def test_email_not_double_counted_as_ipv4_fragment():
    text = "Write to user@mail.co.uk today."
    signals = ii.detect(text).signals
    # One signal, of kind "email", not an email plus an "ipv4" read out of the
    # domain's "co.uk". The single detected span is the property under test;
    # the old assertion compared signal_type values, which conflated "how many
    # things were found" with "what type they are".
    assert [s.evidence["kind"] for s in signals] == ["email"]
    assert {s.signal_type for s in signals} == {"identifier"}


def test_empty_and_deterministic():
    assert ii.detect("").signals == ()
    a = [s.to_dict() for s in ii.detect("Call 0033 1 42 86 82 00.").signals]
    b = [s.to_dict() for s in ii.detect("Call 0033 1 42 86 82 00.").signals]
    assert a == b
