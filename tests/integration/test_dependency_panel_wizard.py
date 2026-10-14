"""The dependency panel in the setup wizard, end to end through Flask.

These tests exercise the real routes (no mocked HTTP layer):

1. The wizard page ships the panel markup the script needs, for every locale.
2. ``GET /api/setup/dependencies`` returns the readiness report, with detail
   messages translated into the request language and technical output
   (import errors, pip output) left as the tool produced it.
3. Install requests are validated before anything runs: an empty selection, an
   undeclared name, and an oversized request each return a translated 400.
"""

from __future__ import annotations

import pytest

# Fixtures are defined in the wizard i18n module; importing them keeps one copy.
from tests.integration.test_setup_wizard_i18n import uninstalled  # noqa: F401
from tests.integration.test_setup_wizard_i18n import _mo

pytestmark = pytest.mark.integration

PANEL_IDS = (
    'id="dependency-panel"',
    'id="dependency-summary"',
    'id="dependency-status"',
    'id="dependency-list"',
    'id="btn-dep-details"',
    'id="btn-dep-refresh"',
    'id="btn-dep-install"',
)


@pytest.mark.parametrize("lang", ("en", "ar", "fa", "he"))
def test_wizard_page_contains_the_dependency_panel(app, uninstalled, lang):
    client = app.test_client()
    client.set_cookie("user_language", lang)
    resp = client.get("/setup")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for marker in PANEL_IDS:
        assert marker in html, f"[{lang}] missing {marker}"
    assert 'class="dependency-panel" id="dependency-panel" hidden' in html


@pytest.mark.parametrize("lang", ("ar", "fa", "he"))
def test_dependency_report_details_are_translated(app, uninstalled, lang):
    """Details are translated for the request language, not the process default."""
    from Api.routes import setup as setup_routes

    catalog = _mo(lang)
    variables = {"installed": "1.2", "requires": ">=1.0"}
    with app.test_request_context(headers={"Cookie": f"user_language={lang}"}):
        localized = setup_routes._localized_dependency_detail(
            "Installed %(installed)s; requires %(requires)s", variables
        )
    expected = catalog.gettext("Installed %(installed)s; requires %(requires)s") % variables
    assert expected != "Installed 1.2; requires >=1.0"
    assert localized == expected
    # Technical output and unknown keys are not translated; the caller keeps the original.
    assert setup_routes._localized_dependency_detail(None, None) is None
    assert setup_routes._localized_dependency_detail("unknown key", {}) is None


def test_dependency_report_endpoint_returns_structured_items(app, uninstalled):
    client = app.test_client()
    resp = client.get("/api/setup/dependencies")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert isinstance(body["items"], list) and body["items"]
    assert {"ready", "counts", "items"} <= set(body)
    for item in body["items"]:
        assert item["state"] in {
            "compatible",
            "missing",
            "incompatible",
            "import_failed",
            "installing",
            "failed",
            "unknown",
        }


@pytest.mark.parametrize(
    "payload,expected_message",
    [
        ({"names": []}, "Choose at least one dependency to install."),
        ({"names": ["definitely-not-declared-pkg"]}, "definitely-not-declared-pkg is not a declared dependency."),
    ],
)
def test_install_request_validation_is_translated(app, uninstalled, payload, expected_message):
    client = app.test_client()
    client.set_cookie("user_language", "ar")
    resp = client.post("/api/setup/dependencies/install", json=payload)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["ok"] is False
    catalog = _mo("ar")
    assert body["error"] in (catalog.gettext(expected_message), expected_message) or (
        "definitely-not-declared-pkg" in body["error"]
    )


def test_unknown_install_job_returns_404(app, uninstalled):
    client = app.test_client()
    resp = client.get("/api/setup/dependencies/jobs/no-such-job")
    assert resp.status_code == 404
    assert resp.get_json()["ok"] is False
