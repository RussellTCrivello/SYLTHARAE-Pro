# Round 16 — the pipeline audit: what every file stores, what it drops

**Question.** For all 698 files in `test-doc/`: which reader takes the file,
where does its text live, is the text that reaches storage complete, and what
evidence proves it?

**One command reproduces the archive; one more renders this report from it.**
Nothing in `REPORT.md` is typed by hand — it is a function of
`archive/records.jsonl.gz` and `registers/r16.json`.

```bash
python tools/audit/archive_extraction.py --corpus test-doc \
    --out audit_report/r16 --timeout 120
python tools/audit/build_audit_report.py \
    --records audit_report/r16/archive/records.jsonl.gz \
    --register tools/audit/registers/r16.json --out audit_report/r16
```

## Results at a glance (measured)

| measure | value |
|---|---|
| files | 698 |
| with an independent oracle | 332 |
| complete (token recall ≥ 0.995) | 318 (95.8 %) |
| mean recall where measurable | 0.9943 |
| text stored | 13 556 019 characters |
| verdicts | COMPLETE 318 · OK-NO-ORACLE 152 · EMPTY-PLAUSIBLE 150 · ERROR 44 · UNVERIFIABLE 20 · NEAR 7 · PARTIAL 6 · INCOMPLETE 1 |

Verbatim before/after on the files that were wrong:

| file | before | after |
|---|---|---|
| `Presentations/testODP_NPE.odp` | 0.031 | **1.000** |
| `Spreadsheets/test-columnar.ods` | 0.863 | **1.000** |
| `Documents/testODTStyles3.odt` | 0.000 (archive reader) | **0.983** |
| `Text/testBMPfp.txt` | 0.000 (image reader) | **1.000** |
| `Presentations/testPPT_groups.pptx` | 0.333 | **1.000** |
| `Other/testPPT.ppsx` | error + 0.756 | **1.000, no error** |
| `Documents/testPDF_childAttachments.pdf` p1 | 1 566 chars (OCR replaced the layer) | **2 503 of 2 510** |
| `Documents/testODFwithOOo3.odt` | 0.717 | **0.943** |
| `Spreadsheets/testRecordSizeExceeded.xlsx` | 181 MB of text for one artifact | **10 MB, capped and marked** |

## What was wrong, in one paragraph

Almost nothing was a parser bug. The losses were *locations*: text inside a
shape the library does not model (a PowerPoint group, a `draw:custom-shape`, a
DOCX header), a run one level below the node the reader inspected
(`text:span` under `text:p`), a package routed to a reader that cannot read it
(a valid ODF whose `mimetype` is not the first ZIP entry; a text file whose
first two bytes are `BM`), a document type the library refuses to open
(`.ppsx`, `.docm`, `.dotx`), and a page whose good text layer was thrown away in
favour of a shorter OCR reading. None of them raised. All of them stored short
text silently.

## Files

| file | what it is |
|---|---|
| `REPORT.md` | the report: method, environment, per-file table (698 rows), every non-COMPLETE file with its evidence, read-vs-ignored matrix, findings register, validation table, per-family summary, backlog |
| `per_file.csv` | the same per-file table as data |
| `findings.json` | the 201 flagged files with the proxy or missing-token evidence |
| `verdict_counts.json` | verdict distribution |
| `archive/records.jsonl.gz` | **the evidence**: one JSON record per file — routing decision, reader, full stored text, located units, recall, oracle reading, runtime, peak RSS (process high-water) |
| `tools/audit/registers/r16.json` | the prose that cannot be derived: root causes, intentional exclusions, validation commands, backlog |

## Caveats that stay caveats

- **OCR is UNVERIFIABLE**, not complete: 20 files, 69 of 204 PDF pages. Proxies
  (coverage, chars/page, confidence, engine) are recorded; nothing claims more.
- **Peak RSS is a process high-water mark**, so the per-file figure is an upper
  bound. A true attribution needs one child process per file.
- **Optional dependencies decide some verdicts.** 40 files that were ERROR in
  the first pass were missing packages (mutagen, rarfile, py7zr, pyxlsb,
  olefile, msoffcrypto, oletools, moviepy); installing each and re-running only
  those files changed the verdicts. The environment table in `REPORT.md` lists
  what was present.
- **`test-doc/` was not modified.** Destructive checks ran on copies.
