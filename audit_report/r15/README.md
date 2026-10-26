# Round 15 — readers and extraction, all 698 corpus files

**Question.** For every file type in `test-doc/`: which reader takes it, where
does its text live, does the text arrive complete, and what evidence proves it?

**Answer files, in reading order**

| file | what it is |
|---|---|
| `report.md` | the written report: verdicts, per-family and per-reader tables, every non-COMPLETE file with its cause, the three repairs made, and the defects still open |
| `manifest.csv` | 698 rows, one per corpus file: reader, verdict, recall, oracle token count, stored characters, located units, elapsed ms, lone surrogates, error, `sha256` |
| `family_summary.csv` | 21 format families: completeness counts, mean/min recall, stored characters, the located-unit kinds seen |
| `reader_summary.csv` | 6 reader classes and the verdict mix each produced |
| `findings.json` | the 75 flagged files with the missing-token sample; for Word, recall **per OOXML part** (document / header / footer / footnotes / endnotes / comments) and per text box |
| `archive/records.jsonl.gz` | the primary evidence: one JSON record per file, including the exact text handed to storage — the report is a pure function of this file |
| `text/<Reader>/*.txt` | the stored text itself, per reader class |

**Corpus result.** 698 files, 3.6M stored characters. COMPLETE 301,
OK-NO-ORACLE 172, EMPTY-PLAUSIBLE 140, ERROR 56, PARTIAL 11, NEAR-COMPLETE 9,
INCOMPLETE 7, EMPTY-AGREED 1, TIMEOUT 1.

**Reproduce.** Nothing in the report re-runs a reader; it is computed from the
archive, so the numbers and the evidence cannot drift apart:

```
tools/audit/report_extraction.py \
    --archive audit_report/r15/archive/records.jsonl.gz \
    --corpus test-doc --out /tmp/r15-check
```

Refilling the archive itself (needs `test-doc/` and the reader dependencies):

```
python tools/audit/archive_extraction.py \
    --corpus test-doc --out /tmp/arch --timeout 100 --resume
```

**How completeness is decided.** Against an oracle that never touches the
project's reader code: `<w:t>` over every WordprocessingML part
(`mc:Fallback` excluded, since it repeats the DrawingML block) for Word;
`<a:t>` over slides *and* notes slides for PowerPoint; `openpyxl` / `xlrd`
cells for spreadsheets; PyMuPDF/pypdf for PDF; `content.xml` for ODF;
`striprtf` / `bs4` / charset-decoded reads for RTF, HTML and text. Scoring is
token recall (COMPLETE ≥ 0.995, NEAR ≥ 0.95, PARTIAL ≥ 0.75, INCOMPLETE below).

**Repairs made (FIXED+TEST).** Three DOCX losses were measured, reproduced as
failing tests, fixed, and re-measured with the same oracle:

| defect | before | after | test |
|---|---|---|---|
| nested-table cells read as empty | `testInstrLink.docx` 0.000, `017097.docx` 0.024 | 1.000, 0.999 | `tests/unit/test_docx_nested_table_cell.py` |
| text boxes (DrawingML and VML) never read | `testWORD_text_box.docx` 0.702, `testHoverAndVml.docx` 0.800, `testWORD_sdtInTextBox.docx` 0.118 | 1.000, 1.000, 1.000 | `tests/unit/test_docx_nested_table_cell.py` |
| block-level content controls (`w:sdt`) skipped | `testWORD_template.docx` 0.130, `testWORD_2006ml.docx` 0.490 | 0.986, 0.926 | `tests/unit/test_docx_content_control.py` |

Word family COMPLETE 29 → 41 of 70; whole corpus COMPLETE 289 → 301 of 698.
The reader changes are in `reader_file/readers/read_office.py`
(`_docx_iter_blocks`, `_docx_text_boxes`, `_docx_cell_text`,
`_docx_table_rows`).

**Evidence grade.** Every number is **verified**: recomputable from the
committed archive, which records the `sha256` of each corpus file it read. Two
caveats are stated in the report rather than hidden: recall is a lower bound on
loss (an oracle can miss text the reader legitimately finds), and the 172
`OK-NO-ORACLE` files are stored-but-unmeasured, not proven complete.

**Still open** (with evidence in `report.md`): the ODF `mimetype`-ordering
routing loss, `.docm`/`.dotx`/`.ppsx` content-type rejection, header/footer text
reaching storage only through the forensic pass, `.psd` with no reader, `.doc`
byte-scrape, `.xls` column order, RTF lone surrogates, protected DOCX raising,
and the non-interruptible oversized XLSX.
