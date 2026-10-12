"""Guards for the advanced-search results viewport and page-size control.

* The page-size selector offers 20 / 50 / 100 / 200 / 500, starts on 20, and the
  page script starts from the same value and accepts only those sizes.
* The server accepts the largest offered size (search API and the
  "Current page only" export), so the selector cannot ask for rows that are
  silently cut to 200.
* The render path must not force ``display: block`` on the results section.
  The desktop layout depends on the section being a flex column, and a forced
  inline value would silently defeat it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEMPLATE = PROJECT_ROOT / "templates" / "Search" / "search_advanced.html"
PAGE_JS = PROJECT_ROOT / "static" / "js" / "pages" / "search-advanced-page.js"
STYLES = PROJECT_ROOT / "static" / "css" / "search-advanced.css"
SEARCH_ROUTE = PROJECT_ROOT / "Api" / "routes" / "search.py"

EXPECTED_SIZES = [20, 50, 100, 200, 500]


def _select_block(html: str) -> str:
    start = html.index('id="resultsPerPage"')
    return html[start:html.index("</select>", start)]


def test_page_size_selector_offers_the_documented_sizes_and_starts_on_20():
    html = TEMPLATE.read_text(encoding="utf-8")
    block = _select_block(html)
    values = [int(v) for v in re.findall(r'<option value="(\d+)"', block)]
    assert values == EXPECTED_SIZES
    selected = re.findall(r'<option value="(\d+)"[^>]*\bselected\b', block)
    assert selected == ["20"]
    assert 'data-on-change="changeResultsPerPage(this.value)"' in block


def test_page_script_default_and_allowed_sizes_match_the_selector():
    js = PAGE_JS.read_text(encoding="utf-8")
    assert re.search(r"resultsPerPage:\s*20\b", js), "initial page size must be 20"
    allowed = re.search(r"const RESULTS_PAGE_SIZES = \[([\d, ]+)\];", js)
    assert allowed, "page script must declare the allowed page sizes"
    assert [int(v) for v in allowed.group(1).split(",")] == EXPECTED_SIZES


def test_page_size_handler_is_exposed_to_declarative_events():
    js = PAGE_JS.read_text(encoding="utf-8")
    assert "window.changeResultsPerPage = changeResultsPerPage;" in js


def test_lucky_search_restores_the_users_page_size_instead_of_20():
    js = PAGE_JS.read_text(encoding="utf-8")
    body = js[js.index("async function feelingLucky()"):]
    body = body[:body.index("\n}\n")]
    assert "const chosenPerPage = searchState.resultsPerPage;" in body
    assert "searchState.resultsPerPage = chosenPerPage;" in body
    assert "searchState.resultsPerPage = 20;" not in body


def test_render_path_clears_inline_display_instead_of_forcing_block():
    js = PAGE_JS.read_text(encoding="utf-8")
    assert "section.style.display = 'block'" not in js
    assert "section.style.display = '';" in js


def test_search_api_accepts_the_largest_offered_page_size():
    source = SEARCH_ROUTE.read_text(encoding="utf-8")
    match = re.search(
        r"per_page = min\(max\(1, int\(data\.get\('per_page', 50\) or 50\)\), (\d+)\)",
        source,
    )
    assert match, "api_search per_page clamp not found"
    assert int(match.group(1)) >= max(EXPECTED_SIZES)


def test_export_parse_keeps_the_largest_offered_page_size():
    from Api.services.search_export import parse

    assert parse({"query": "x", "per_page": 500}).per_page == 500
    assert parse({"query": "x", "per_page": 100000}).per_page == 500
    assert parse({"query": "x", "per_page": 20}).per_page == 20


def test_results_viewport_is_scoped_to_the_search_page_and_desktop_width():
    css = STYLES.read_text(encoding="utf-8")
    viewport = css[css.index("Fixed results viewport"):]
    assert "@media (min-width: 1200px)" in viewport
    assert 'body[data-page-type="search-advanced"] #mainContent' in viewport
    assert "#resultsContainer.results-container" in viewport
    # The list is the only region that scrolls in the fixed layout.
    list_rule = viewport[viewport.index("#resultsContainer.results-container {"):]
    list_rule = list_rule[:list_rule.index("}")]
    assert "overflow-y: auto" in list_rule


def test_wrappers_the_layout_relies_on_exist_in_the_template():
    html = TEMPLATE.read_text(encoding="utf-8")
    for marker in ('class="search-page-shell"', 'class="search-page-top"',
                   'id="searchResultsSection"', 'id="resultsContainer"',
                   'id="pagination"'):
        assert marker in html, marker
