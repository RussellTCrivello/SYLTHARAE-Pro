# test-doc / reader pipeline — completion snapshot

**Date:** 2026-10-09  
**Corpus:** `test-doc/` (~708 files)  
**Harness:** `tools/perf/extraction_matrix_testdoc.py`, `tools/perf/office_deep_audit_testdoc.py`

## Delivered in this effort

| Area | Outcome |
|------|---------|
| Jobs UI | Live errors/warnings via `JobIssueRegistry`; API facade fields; job polling rate limit 600/min |
| Legacy `.doc` | LO→DOCX pipeline, `elements` promotion, storage text fallback |
| `.xlsb` | `read_xlsb_file` + pyxlsb; LO fallback when parser fails |
| Apple `.pages` / `.numbers` | iWork routing (not plain ZIP); index.xml / IWA / QuickLook PDF / LO |
| Legacy `.ppt` | LO → COM → **OLE text extraction** (22/22 `.ppt` GREEN in office audit) |
| Nested archives | Skip `__MACOSX`, `._*`, `*.iwa` shards |
| HTML | Charset-aware decode for non–UTF-8 fixtures |
| ODT | `extractText`; `content.xml` fallback when odfpy rejects external DTDs |
| OOXML routing | Word main part wins over embedded spreadsheet content types |
| Images | `no_text_extracted` → completed read; `.avif` on image reader |
| Audio/video | `.m4a` pinned to audio; `video_fps` → audio fallback |
| Metrics | `read_result_utils` normalizes reader payloads for storage-shaped text |

## Office audit (latest)

Run: `python tools/perf/office_deep_audit_testdoc.py`

| Tier | Count (approx.) |
|------|-----------------|
| GREEN | 297 |
| YELLOW | 12 |
| RED | 29 |

**RED buckets (expected / environmental):**

- Password-protected or corrupt OOXML/XLS (`protect.xlsx`, `protected*.docx`, `password.xls`)
- Non-OLE `.doc` (WordPerfect-style fixtures)
- One `.xlsb` where pyxlsb throws and LibreOffice is not installed
- Encrypted ODT, truncated packages, specialty RTF (1 cp932 edge if striprtf still chokes)
- Protected `.pages`

## Full corpus matrix

```bash
python tools/perf/extraction_matrix_testdoc.py --out docs/perf/runs/extraction_testdoc.jsonl
```

Non-office failures (archives, DRM media, RAW without decoder, Android binary XML, `.bin` app bundles) are **corpus stress cases**, not regressions in the office path.

## Operator checklist

1. Restart the application after pulling these changes.
2. Re-run ingestion on `test-doc` (old DB rows are not backfilled).
3. Optional: install **LibreOffice** for full `.ppt` / stubborn `.xlsb` / maximum `.doc` fidelity.
4. Optional: `pip install pyxlsb` (already in `requirements.txt`).

## Key tests

```bash
python -m pytest tests/unit/test_job_issue_registry.py tests/unit/test_job_api_facade.py ^
  tests/unit/test_legacy_office_readers.py tests/unit/test_iwork_pages_reader.py ^
  tests/unit/test_ppt_legacy_read.py tests/unit/test_ppt_ole_extraction.py ^
  tests/unit/test_nested_extract_skip.py tests/unit/test_spreadsheet_by_content.py ^
  tests/unit/test_format_detection.py -q
```
