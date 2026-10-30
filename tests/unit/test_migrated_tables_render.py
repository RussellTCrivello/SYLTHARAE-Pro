"""The three migrated tables render what the browser saw.

Round 22 item D moved three hand-written tables onto `data_table`
(`templates/components/table.html`): the Monitoring scenarios list, the Reports
file-type table and the translation selection panel. Item A of the wrap-up
required that move to be *looked at*, not inferred: the pages were captured in
a real browser at the parent commit and at the commit that migrated them
(`audit_report/r22_workbook/tables/`), and the screenshots came back
byte-identical.

This module is the part of that capture that can live in the suite. Every
expectation below was read out of the browser (the table's id, its classes, its
column headers, and the wrapper it sits in) and is asserted against a full-page
render of the same template. A change that moves a column, drops an id or adds
a class fails here, without a browser.

The DOM was compared, not only the pixels: the migrated markup differs from the
hand-written markup in whitespace alone, which is why the screenshots are
identical and why the assertions here are on structure.
"""
from __future__ import annotations

import json
import pathlib
import re

import jinja2
import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
TEMPLATES = PROJECT_ROOT / "templates"
CAPTURES = PROJECT_ROOT / "audit_report" / "r22_workbook" / "tables"


# --------------------------------------------------------------------------- #
# Rendering a whole page without a request
# --------------------------------------------------------------------------- #
class _Loose(jinja2.Undefined):
    """Anything the page asks for that this test does not supply.

    The point of the test is the table markup, not the page's data. An
    undefined that answers every lookup lets the page render as a shell, the
    same way `test_component_library.py` renders single components.
    """

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return self

    def __getitem__(self, key):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 0

    def __bool__(self):
        return False

    def __str__(self):
        return ""


@pytest.fixture(scope="module")
def render():
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=_Loose,
    )
    environment.globals["_"] = lambda text: text
    environment.globals["csrf_token"] = lambda: "test-token"
    # `<script type="application/json">{{ x|tojson }}</script>` must not fail
    # on a page shell; the payload is not what this module checks.
    environment.filters["tojson"] = lambda value, **kwargs: json.dumps(value, default=str)

    context = {
        "page_data": {},
        "report": None,
        "totals": {},
        "query_suffix": "",
        "filter_options": {"sources": [], "sides": []},
        "reports": [],
    }

    def render_template(name: str) -> str:
        relative = name.split("templates/", 1)[-1]
        return environment.get_template(relative).render(**context)

    return render_template


# --------------------------------------------------------------------------- #
# What the browser measured, before and after the migration
# --------------------------------------------------------------------------- #
#: `(template, table id, class attribute, column headers)` - the values the
#: capture script read from `#scenariosTable`, `#reportByType` and the
#: selection panel's table on `/search`, at both commits.
EXPECTED = {
    "templates/Monitoring/monitoring.html": {
        "id": "scenariosTable",
        "classes": ["table", "table-hover", "align-middle"],
        "headers": ["Name", "Version", "Status", "Last Evaluated", "Actions"],
        "wrapper": "table-responsive",
        "tbody_id": "scenariosTableBody",
    },
    "templates/Reports/reports.html": {
        "id": "reportByType",
        "classes": ["table", "table-sm", "table-hover", "align-middle", "mb-0"],
        "headers": ["File type", "Total", "Processed", "Failed", "Success Rate"],
        "wrapper": "table-responsive",
        "tbody_id": None,
    },
    "templates/Translation/_selection_panel.html": {
        "id": None,
        "classes": ["table", "table-sm", "align-middle", "mb-0"],
        "headers": ["Original", "Translation", "Accept translation"],
        "wrapper": "table-responsive",
        "tbody_id": None,
    },
}


def _table_attributes(html: str) -> dict:
    match = re.search(r"<table\b([^>]*)>", html)
    assert match, "the page rendered no table at all"
    attributes = match.group(1)
    identifier = re.search(r'id="([^"]*)"', attributes)
    classes = re.search(r'class="([^"]*)"', attributes)
    return {
        "id": identifier.group(1) if identifier else None,
        "classes": (classes.group(1).split() if classes else []),
    }


def _headers(html: str) -> list:
    head = re.search(r"<thead>(.*?)</thead>", html, re.S)
    assert head, "the table rendered no <thead>"
    return [re.sub(r"<[^>]+>", "", cell).strip()
            for cell in re.findall(r"<th\b[^>]*>(.*?)</th>", head.group(1), re.S)]


@pytest.mark.parametrize("template", sorted(EXPECTED))
def test_the_table_keeps_the_identity_the_browser_saw(template, render):
    expected = EXPECTED[template]
    html = "..." + render(template)
    attributes = _table_attributes(html)
    assert attributes["id"] == expected["id"]
    assert attributes["classes"] == expected["classes"]


@pytest.mark.parametrize("template", sorted(EXPECTED))
def test_the_table_keeps_its_columns_in_order(template, render):
    expected = EXPECTED[template]
    assert _headers(render(template)) == expected["headers"]


@pytest.mark.parametrize("template", sorted(EXPECTED))
def test_the_table_is_still_inside_its_responsive_wrapper(template, render):
    expected = EXPECTED[template]
    html = render(template)
    wrapper = re.search(r'<div class="([^"]*table-responsive[^"]*)">\s*<table\b', html)
    assert wrapper, "the table lost its .table-responsive wrapper"
    assert expected["wrapper"] in wrapper.group(1).split()


@pytest.mark.parametrize("template", sorted(EXPECTED))
def test_the_migrated_tables_call_the_component(template):
    """The reason the markup is now identical everywhere: it is one macro."""
    source = (PROJECT_ROOT / template).read_text(encoding="utf-8")
    assert "{% call data_table(" in source
    assert "{% from 'components/table.html' import data_table %}" in source
    assert not re.search(r"^\s*<table\b", source, re.M), (
        "the template hand-writes a table frame again")


def test_the_tbody_ids_the_scripts_fill_are_preserved(render):
    """JS selects these by id; a migration that renamed one breaks it silently."""
    monitoring = render("templates/Monitoring/monitoring.html")
    assert 'id="scenariosTableBody"' in monitoring
    panel = (PROJECT_ROOT / "templates/Translation/_selection_panel.html").read_text()
    assert "data-translation-rows" in panel
    assert 'data-translation-rows' in render("templates/Translation/_selection_panel.html")


# --------------------------------------------------------------------------- #
# The capture itself, so the evidence and the test cannot drift apart
# --------------------------------------------------------------------------- #
def test_the_before_and_after_captures_agree_on_every_field():
    """The committed capture, re-read: if it is ever re-taken and differs, this
    test is the one that says so instead of a reviewer's memory."""
    before = json.loads((CAPTURES / "before" / "capture.json").read_text())
    after = json.loads((CAPTURES / "after" / "capture.json").read_text())
    assert [row["name"] for row in before] == [row["name"] for row in after]
    for old, new in zip(before, after):
        assert old["status"] == new["status"] == 200, old["name"]
        for field in ("id", "classes", "headers", "columns", "wrapper", "box", "rows"):
            assert old["table"][field] == new["table"][field], (
                f"{old['name']}.{field} changed between the parent commit and "
                "the migration")
        assert old["table"]["found"] and new["table"]["found"], old["name"]


def test_the_captures_were_taken_at_two_different_commits():
    """A before/after with the same commit proves nothing.

    The capture says which commits it covers; this checks they are real, that
    they differ, and - with git - that the migration sits between them.
    """
    import subprocess

    provenance = json.loads((CAPTURES / "provenance.json").read_text())
    before = provenance["before"]["commit"]
    after = provenance["after"]["commit"]
    migrated = provenance["migrated_by"]
    assert before != after

    def git(*arguments) -> bool:
        result = subprocess.run(["git", *arguments], cwd=str(PROJECT_ROOT),
                                capture_output=True, text=True)
        return result.returncode == 0

    if not git("rev-parse", "--git-dir"):
        pytest.skip("not a git checkout: the commits cannot be verified here")
    assert git("cat-file", "-e", f"{before}^{{commit}}"), before
    assert git("cat-file", "-e", f"{after}^{{commit}}"), after
    assert git("merge-base", "--is-ancestor", before, migrated), (
        "the 'before' capture is not an ancestor of the migration")
    assert git("merge-base", "--is-ancestor", migrated, after), (
        "the 'after' capture predates the migration")


def test_the_screenshots_exist_for_both_runs():
    for label in ("before", "after"):
        for name in ("monitoring", "reports", "translation_panel"):
            path = CAPTURES / label / f"{name}.png"
            assert path.is_file(), path
            assert path.stat().st_size > 1000, path
