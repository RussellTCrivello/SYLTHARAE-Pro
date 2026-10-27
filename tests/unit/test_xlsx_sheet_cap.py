"""Round 18, task 3c: the cell cap must count cells, not the padded rectangle.

`CVLKRA-KYC_Download_File_Structure_V3.1.xlsx` scored 0.9947 with 34 missing
tokens, all from one sheet. The sheet was marked ``truncated`` after 245,760
cells - 15 rows - while the same sheet declares 376,832 cells. That is exactly
16384 x 15: the sheet's dimension spans the full XLSX column width, so the cap
was consumed by empty padding 15 rows into a longer table. Nothing about the
data was too big; the accounting was wrong.

Two consequences, both tested here:

* a sheet whose used range is padded wide must still be read to its last
  populated row;
* a sheet that really is too big must still stop, and must say so with the
  reason and the amount kept, so the shortfall is visible downstream.

The caps are also readable from the environment now, because "too big" is a
deployment question (a 4 GB workstation and a 512 MB container do not have the
same answer) and a cap that cannot be raised is a silent ceiling.
"""
import os

import pytest


def _xlsx_with_wide_padding(path, rows=40, populated=4, pad_to=16384):
    """A sheet whose declared width is ``pad_to`` but whose data is narrow.

    openpyxl writes a dimension from the cells that exist, so the wide padding
    is created the way real exporters create it: a single styled cell at the
    far edge of the sheet, plus a narrow data block.
    """
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Company Type"
    for row in range(1, rows + 1):
        for col in range(1, populated + 1):
            ws.cell(row=row, column=col, value=f"r{row}c{col}")
    # The marker that stretches the dimension, exactly as a stray format does.
    ws.cell(row=1, column=pad_to, value=None).number_format = "General"
    wb.save(str(path))
    return path


def _read(path):
    from reader_file.readers.read_office import OfficeFileReader

    result = OfficeFileReader().read_file({"path": str(path), "extension": ".xlsx"})
    return result.get("content", result)


def test_a_wide_padded_sheet_is_read_to_its_last_row(tmp_path):
    path = _xlsx_with_wide_padding(tmp_path / "wide.xlsx")
    content = _read(path)
    sheet = content["sheets"]["Company Type"]
    assert not sheet.get("truncated"), sheet.get("truncated_reason")
    assert len(sheet["data"]) == 40, len(sheet["data"])
    assert sheet["data"][-1][:4] == ["r40c1", "r40c2", "r40c3", "r40c4"]


def test_padding_is_not_stored_as_empty_cells(tmp_path):
    """Trailing empties are not content; storing them is what ate the cap."""
    path = _xlsx_with_wide_padding(tmp_path / "narrow.xlsx")
    sheet = _read(path)["sheets"]["Company Type"]
    assert all(len(row) <= 4 for row in sheet["data"]), [len(r) for r in sheet["data"][:3]]
    assert sheet["cells_read"] == 40 * 4, sheet["cells_read"]


def test_a_genuinely_oversized_sheet_still_stops_and_says_why(tmp_path, monkeypatch):
    from reader_file.readers import read_office

    monkeypatch.setattr(read_office, "MAX_SHEET_CELLS", 50)
    path = _xlsx_with_wide_padding(tmp_path / "capped.xlsx", rows=40, pad_to=8)
    sheet = _read(path)["sheets"]["Company Type"]
    assert sheet.get("truncated") is True
    assert sheet.get("truncated_reason")
    assert "MAX_SHEET_CELLS" in sheet["truncated_reason"] or "cap" in sheet["truncated_reason"]
    assert sheet["cells_read"] <= 50


def test_the_caps_can_be_raised_without_editing_code(monkeypatch):
    from reader_file.readers import read_office

    monkeypatch.setenv("SYLTHARAE_MAX_SHEET_CELLS", "12345")
    monkeypatch.setenv("SYLTHARAE_MAX_WORKBOOK_CELLS", "67890")
    assert read_office.sheet_cell_cap() == 12345
    assert read_office.workbook_cell_cap() == 67890


def test_a_bad_environment_value_falls_back_to_the_default(monkeypatch):
    from reader_file.readers import read_office

    monkeypatch.setenv("SYLTHARAE_MAX_SHEET_CELLS", "not-a-number")
    assert read_office.sheet_cell_cap() == read_office.MAX_SHEET_CELLS


def test_the_corpus_sheet_is_not_truncated_by_padding():
    corpus = os.path.join(os.path.dirname(__file__), "..", "..", "test-doc",
                          "Spreadsheets",
                          "CVLKRA-KYC_Download_File_Structure_V3.1.xlsx")
    if not os.path.exists(corpus):
        pytest.skip("corpus file missing")
    sheet = _read(corpus)["sheets"]["Company Type"]
    assert not sheet.get("truncated"), sheet.get("truncated_reason")
    # 23 data rows + a header in the source; the padded read used to stop at 15.
    assert len(sheet["data"]) >= 16
