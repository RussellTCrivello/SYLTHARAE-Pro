# Round 15 — readers and extraction, all 698 corpus files

**Question.** For every file type in `test-doc/`: which reader takes it, where
does its text live, did the text arrive complete, and what evidence proves it?

**Answer files, in reading order**

| file | what it is |
|---|---|
| `report.md` | the written report: verdicts, per-family and per-reader tables, every non-COMPLETE file with its cause, and the defects the pass supports |
| `manifest.csv` | 698 rows, one per corpus file: reader, verdict, recall, oracle token count, stored characters, located units, elapsed ms, lone surrogates, error, `sha256` |
| `family_summary.csv` | 21 format families: completeness counts, mean/min recall, stored characters, the located-unit kinds seen |
| `reader_summary.csv` | 6 reader classes and the verdict mix each produced |
| `findings.json` | the 90 flagged files with the missing-token sample; for Word, recall **per OOXML part** (document / header / footer / footnotes / endnotes / comments) and per text box |
| `archive/records.jsonl.gz` | the primary evidence: one JSON record per file, including the exact text handed to storage — the report is a pure function of this file |
| `text/<Reader>/*.txt` | the stored text itself, 505 files, per reader class |

**Reproduce.** Nothing in the report re-runs a reader; it is computed from the
archive, so the numbers and the evidence cannot drift apart:

```
tools/audit/report_extraction.py \
    --archive audit_report/r15/archive/records.jsonl.gz \
    --corpus test-doc --out /tmp/r15-check
```

Refilling the archive itself (needs `test-doc/` and the reader dependencies):

```
/tmp/rv/bin/python tools/audit/archive_extraction.py \
    --corpus test-doc --out /tmp/arch --timeout 100 --resume
```

**How completeness is decided.** Against an oracle that never touches the
project's reader code: `<w:t>` over every WordprocessingML part for Word;
`<a:t>` over slides *and* notes slides for PowerPoint; `openpyxl` / `xlrd`
cells for spreadsheets; PyMuPDF/pypdf for PDF; `content.xml` for ODF;
`striprtf` / `bs4` / charset-decoded reads for RTF, HTML and text. Scoring is
token recall (COMPLETE ≥ 0.995, NEAR ≥ 0.95, PARTIAL ≥ 0.75, INCOMPLETE below).

**Evidence grade.** All 698 numbers are **verified**: they are recomputable
from the committed archive, and the archive records the `sha256` of each corpus
file it read. Two caveats are stated in the report rather than hidden: recall
is a lower bound on loss (an oracle can miss text the reader legitimately
finds), and the 172 `OK-NO-ORACLE` files are stored-but-unmeasured, not proven
complete.

**Scope.** This pass measures and documents; it changes no reader. The defects
it supports — nested-table DOCX cells, VML text boxes, `.docm`/`.dotx`
rejection, the ODF `mimetype`-ordering routing loss, `.psd`, `.doc`, `.xls`
column order, lone surrogates, protected DOCX, the non-interruptible oversized
XLSX — are listed with their evidence in `report.md` and are open.
