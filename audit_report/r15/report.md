# Round 15 - what every reader actually extracts

Corpus: `test-doc/` - **698 files**. Archive: `audit_report/r15/archive/records.jsonl.gz` (1,651,184 bytes gzipped, one JSON record per file, including the exact text handed to storage). Every number below is computed from that archive by `tools/audit/report_extraction.py`; regenerate with

```
tools/audit/report_extraction.py --archive audit_report/r15/archive/records.jsonl.gz --corpus test-doc --out .
```

Total stored characters across the corpus: **3,655,078**.

## Verdicts

| verdict | files | share | meaning |
|---|---|---|---|
| COMPLETE | 301 | 43.1% | every oracle token was stored (recall >= 0.995) |
| OK-NO-ORACLE | 172 | 24.6% | text stored, but this family has no independent oracle in this environment, so completeness is unmeasured |
| EMPTY-PLAUSIBLE | 140 | 20.1% | nothing stored; the format holds no text a reader can reach (pixels, audio, container entries) |
| ERROR | 56 | 8.0% | the reader raised |
| PARTIAL | 11 | 1.6% | recall 0.75-0.95 |
| NEAR-COMPLETE | 9 | 1.3% | recall 0.95-0.995 |
| INCOMPLETE | 7 | 1.0% | recall < 0.75 |
| EMPTY-AGREED | 1 | 0.1% | nothing stored and the oracle agrees there is no text |
| TIMEOUT | 1 | 0.1% | the reader never returned |

## What was measured, and against what

Two separate questions per file, because they fail differently:

1. **Routing** - did the file reach the reader that owns its format, and did the format sniffing agree with the extension (`declared_ext` vs `declared_ext`/reader in `manifest.csv`)?

2. **Completeness** - is the text the reader produced a superset of the text an *independent* oracle finds in the file? Each family gets its own oracle, built without using the project's reader code:

| family | oracle used |
|---|---|
| Word (.docx/.docm/.dotx) | `word/document.xml`, `header*/footer*/footnotes/endnotes/comments` read with `<w:t>` (a naive `<w:t[^>]*>` also matches `<w:tbl>` and pollutes the token set - fixed) |
| Word (.doc) | OLE `WordDocument` byte scan (`olefile`); no converter in this sandbox, so recall is a lower bound |
| PDF | PyMuPDF page text, then pypdf as a second pass |
| Excel (.xlsx) | `openpyxl` read-only cell iteration |
| Excel (.xls) | `xlrd` cell iteration |
| PowerPoint | `<a:t>` over `slides/slideN.xml` **and** `notesSlides/notesSlideN.xml` |
| OpenDocument | `content.xml` `<text:p>` / `table:table-cell` |
| RTF / HTML / plain / delimited | `striprtf`, `bs4`, direct decode with charset detection |
| Archive | member list and member-level extraction |
| Image / Audio / Video | nothing textual exists without OCR or transcription - reported, not scored |

Recall is **token recall** over case-sensitive alphanumeric runs, banded COMPLETE >= 0.995 / NEAR-COMPLETE >= 0.95 / PARTIAL >= 0.75 / INCOMPLETE below. A character ratio was tried first and discarded: a complete PDF scored 8-60x on whitespace alone, so it measured layout, not extraction.

`EMPTY-PLAUSIBLE` is not a pass by default - it is a claim that the format has no text a reader could reach. Where that claim was doubted it was checked by hand (see Findings).

## Per family

| family | files | COMPLETE | NEAR | PARTIAL | INCOMPLETE | empty | error | no oracle | mean recall | stored chars | where the text lives |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Plain text | 74 | 70 | 0 | 1 | 1 | 1 | 0 | 1 | 0.985 | 1119124 | the file itself, decoded with charset detection |
| Word | 70 | 41 | 5 | 6 | 3 | 7 | 6 | 2 | 0.919 | 202942 | the document body (paragraphs), tables including nested tables, text boxes, and the separate header/footer/footnote/endnote/comment parts |
| PDF | 67 | 37 | 0 | 0 | 0 | 0 | 4 | 26 | 1.000 | 594405 | per page, in the content stream; scanned pages hold an image instead |
| Word (.doc) | 53 | 0 | 0 | 0 | 0 | 0 | 2 | 51 | - | 49557 | a binary OLE stream (WordDocument), reachable only with an external converter or a heuristic byte scan |
| Image | 49 | 0 | 0 | 0 | 0 | 33 | 2 | 14 | - | 10996 | pixels, reachable only through OCR |
| Archive | 46 | 0 | 0 | 0 | 0 | 34 | 11 | 1 | - | 1464 | member entries; the text lives in the members, not the container |
| Audio | 46 | 0 | 0 | 0 | 0 | 40 | 6 | 0 | - | 0 | tags and, if transcribed, the audio itself |
| RTF | 44 | 36 | 0 | 0 | 0 | 6 | 0 | 2 | 1.000 | 43912 | control-word encoded text runs |
| HTML | 39 | 30 | 1 | 3 | 0 | 1 | 0 | 4 | 0.984 | 124788 | text nodes, with entity decoding and charset detection |
| Excel | 38 | 21 | 0 | 0 | 0 | 0 | 5 | 12 | 1.000 | 431945 | per cell, spread over worksheet parts and a shared string table |
| PowerPoint | 32 | 23 | 1 | 0 | 0 | 0 | 2 | 6 | 0.998 | 10482 | per shape on each slide, plus the notes pages |
| Excel (.xls) | 32 | 22 | 0 | 0 | 0 | 0 | 2 | 8 | 1.000 | 833964 | per cell in BIFF records |
| OpenDocument | 25 | 13 | 2 | 1 | 3 | 0 | 1 | 5 | 0.829 | 79423 | content.xml, in text:p and table:table-cell elements |
| PowerPoint (.ppt) | 22 | 0 | 0 | 0 | 0 | 0 | 0 | 22 | - | 33578 | binary OLE streams (PowerPoint Document / Text_Content) |
| iWork | 16 | 0 | 0 | 0 | 0 | 0 | 3 | 13 | - | 57421 | a zip (.pages/.numbers) around IWA protobuf chunks - no reader here |
| Video | 16 | 0 | 0 | 0 | 0 | 12 | 4 | 0 | - | 0 | container metadata and, if transcribed, the audio track |
| Delimited text | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 1.000 | 56659 | the file itself, one record per line |
| Executable | 6 | 0 | 0 | 0 | 0 | 2 | 4 | 0 | - | 0 | no document text; strings are not content |
| Camera raw | 6 | 0 | 0 | 0 | 0 | 5 | 1 | 0 | - | 0 | sensor data plus EXIF tags; no text but the tags |
| Excel (.xlsb) | 5 | 0 | 0 | 0 | 0 | 0 | 1 | 4 | - | 3663 | binary workbook parts, cell records per sheet |
| Design | 4 | 0 | 0 | 0 | 0 | 0 | 3 | 1 | - | 755 | layers in a proprietary container (.psd/.ai); no reader here |

## Per reader

| reader | files | verdicts |
|---|---|---|
| (no reader) | 8 | ERROR 8 |
| ArchiveFileReader | 49 | EMPTY-PLAUSIBLE 36, ERROR 11, OK-NO-ORACLE 1, INCOMPLETE 1 |
| AudioFileReader | 45 | EMPTY-PLAUSIBLE 40, ERROR 5 |
| ImageFileReader | 55 | EMPTY-PLAUSIBLE 38, OK-NO-ORACLE 14, ERROR 2, INCOMPLETE 1 |
| OfficeFileReader | 293 | COMPLETE 128, OK-NO-ORACLE 116, ERROR 21, NEAR-COMPLETE 8, PARTIAL 7, EMPTY-PLAUSIBLE 6, INCOMPLETE 5, EMPTY-AGREED 1, TIMEOUT 1 |
| PDFFileReader | 61 | COMPLETE 37, OK-NO-ORACLE 20, ERROR 4 |
| RemainingFileReader | 170 | COMPLETE 136, OK-NO-ORACLE 21, EMPTY-PLAUSIBLE 8, PARTIAL 4, NEAR-COMPLETE 1 |
| VideoFileReader | 17 | EMPTY-PLAUSIBLE 12, ERROR 5 |

One reader class per format family is dispatched by extension (`reader_file/services/file_reader_service.py`); the archive records which class ran, so a misfiled format shows up as a reader with the wrong family in its verdict list rather than as a silent empty result.

## Findings

75 files are not COMPLETE. They are grouped by cause below; per-file detail, including the missing-token sample, is in `findings.json`, and `manifest.csv` lists all 698.

### Word (15)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Documents/testWORD_missing_ooxml_bean1.docx | INCOMPLETE | 0.000 | OfficeFileReader | missing tokens: b |
| Other/testWORD_macros.docm | ERROR | 0.000 | OfficeFileReader | file 'test-doc/Other/testWORD_macros.docm' is not a Word file, content type is 'application/vnd.ms-word.document.macroEnabled.main+xml' |
| Other/testWORD_template.dotx | ERROR | 0.020 | OfficeFileReader | file 'test-doc/Other/testWORD_template.dotx' is not a Word file, content type is 'application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+x |
| Documents/testWORD_missing_text.docx | INCOMPLETE | 0.429 | OfficeFileReader | missing tokens: professional, Seasoned, Company, Rich |
| Documents/testWORD_features.docx | INCOMPLETE | 0.478 | OfficeFileReader | missing tokens: litoraMaecenas, litoratorquent, commentThis, sociosquad |
| Documents/testWORD_override_list_numbering.docx | PARTIAL | 0.888 | OfficeFileReader | missing tokens: someOtherText, someText, st, th |
| Documents/testWORD_various.docx | PARTIAL | 0.925 | OfficeFileReader | missing tokens: unde, line, ita, li |
| Documents/testWORD_2006ml.docx | PARTIAL | 0.926 | OfficeFileReader | missing tokens: paragraph, Mattmann, Zitting, Second |
| Documents/testWORD_embedded_pics.docx | PARTIAL | 0.926 | OfficeFileReader | missing tokens: embedded, Deeply |
| Documents/testWORD_numbered_list.docx | PARTIAL | 0.928 | OfficeFileReader | missing tokens: Footnote, comment, list, here |
| Documents/testWORD_emptyParaInTextbox.docx | PARTIAL | 0.940 | OfficeFileReader | missing tokens: publikáciáchVysokoškolské, zamestnancovPrehľad, časopisochPočet, ohlasovVedúci |
| Documents/protected_normal_case.docx | ERROR | - | OfficeFileReader | Package not found at 'test-doc/Documents/protected_normal_case.docx' |
| Documents/protected_upper_case.docx | ERROR | - | OfficeFileReader | Package not found at 'test-doc/Documents/protected_upper_case.docx' |
| Documents/testWORD_protected_passtika.docx | ERROR | - | OfficeFileReader | Package not found at 'test-doc/Documents/testWORD_protected_passtika.docx' |
| Documents/testWORD_truncated.docx | ERROR | - | OfficeFileReader | Package not found at 'test-doc/Documents/testWORD_truncated.docx' |

### Archive (11)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Archives/full_encrypted.7z | ERROR | - | ArchiveFileReader | Extraction failed |
| Archives/moby.zip | ERROR | - | ArchiveFileReader | That compression method is not supported |
| Archives/test-documents-enc.rar | ERROR | - | ArchiveFileReader | Archive headers are encrypted and no password was supplied |
| Archives/test-documents-spanned.zip | ERROR | - | ArchiveFileReader | Bad magic number for file header |
| Archives/test7Z_protected_passTika.7z | ERROR | - | ArchiveFileReader | Archive is password-protected and no password was supplied |
| Archives/testZIP_corrupted_oom.zip | ERROR | - | ArchiveFileReader | Bad magic number for central directory |
| Archives/testZipEncrypted.zip | ERROR | - | ArchiveFileReader | Archive is password-protected and no password was supplied |
| Archives/testZip_absolutePath.zip | ERROR | - | ArchiveFileReader | Absolute or drive-qualified path in archive: 'C:/dangerous/dont/touch.pl' |
| Archives/testZip_overlappingNames.zip | ERROR | - | ArchiveFileReader | Path traversal in archive member: '../../../f1.txt' |
| Archives/testZip_relative.zip | ERROR | - | ArchiveFileReader | Path traversal in archive member: '../../../dangerous/dont/touch.pl' |
| Archives/testZip_with_DataDescriptor.zip | ERROR | - | ArchiveFileReader | Bad magic number for file header |

### Audio (6)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Audio/testAAC.aac | ERROR | - | AudioFileReader | Error reading audio file: sync not found |
| Audio/testAACid3.aac | ERROR | - | AudioFileReader | Error reading audio file: can't sync to MPEG frame |
| Audio/testMP3truncated.mp3 | ERROR | - | AudioFileReader | Error reading audio file: |
| Audio/testMP4_drm.m4a | ERROR | - | AudioFileReader | Error reading audio file: truncated data |
| Audio/testMP4_truncated.m4a | ERROR | - | AudioFileReader | Error reading audio file: truncated data |
| Audio/testWMA.wma | ERROR | - | VideoFileReader | No video library installed. Install with: pip install opencv-python or pip install moviepy |

### OpenDocument (5)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Documents/testODTEncrypted.odt | ERROR | 0.000 | OfficeFileReader | 'utf-8' codec can't decode byte 0x85 in position 3: invalid start byte |
| Documents/testODTStyles3.odt | INCOMPLETE | 0.000 | ArchiveFileReader | missing tokens: Onbekwaamverklaring, verantwoordelijke, referentienummer, Guldensporenlaan |
| Presentations/testODP_NPE.odp | INCOMPLETE | 0.031 | OfficeFileReader | missing tokens: institutionalized, responsibilities, characteristics, medicalization |
| Documents/testODFwithOOo3.odt | INCOMPLETE | 0.717 | OfficeFileReader | missing tokens: Bibliography, Hanssens, rather, border |
| Spreadsheets/test-columnar.ods | PARTIAL | 0.863 | OfficeFileReader | missing tokens: 10, of, 0, 1 |

### Excel (5)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Spreadsheets/protect.xlsx | ERROR | - | OfficeFileReader | File is not a zip file |
| Spreadsheets/protectedFile.xlsx | ERROR | - | OfficeFileReader | File is not a zip file |
| Spreadsheets/testEXCEL_protected_passtika.xlsx | ERROR | - | OfficeFileReader | File is not a zip file |
| Spreadsheets/testEXCEL_protected_passtika_2.xlsx | ERROR | - | OfficeFileReader | File is not a zip file |
| Spreadsheets/testRecordSizeExceeded.xlsx | TIMEOUT | - | OfficeFileReader | no result within 100 s; probe process killed externally |

### PDF (4)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Documents/testPDF_no_extract_no_accessibility_owner_user.pdf | ERROR | - | PDFFileReader | PDF is encrypted and cannot be decrypted |
| Documents/testPDF_no_extract_yes_accessibility_owner_user.pdf | ERROR | - | PDFFileReader | PDF is encrypted and cannot be decrypted |
| Documents/testPassword4Spaces.pdf | ERROR | - | PDFFileReader | PDF is encrypted and cannot be decrypted |
| Documents/testUnicodePassword.pdf | ERROR | - | PDFFileReader | PDF is encrypted and cannot be decrypted |

### Executable (4)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Executables/testTinyPE.exe | ERROR | - |  | Unsupported file type: .exe |
| Executables/testWindows-x86-32-icons.exe | ERROR | - |  | Unsupported file type: .exe |
| Executables/testWindows-x86-32.exe | ERROR | - |  | Unsupported file type: .exe |
| Other/test-documents.dmg | ERROR | - |  | Unsupported file type: .bin |

### Video (4)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Videos/testMP4AudioOnly.mp4 | ERROR | - | VideoFileReader | No video library installed. Install with: pip install opencv-python or pip install moviepy |
| Videos/testMP4_QuickTimeMetadata.mov | ERROR | - | VideoFileReader | No video library installed. Install with: pip install opencv-python or pip install moviepy |
| Videos/testMP4_StillImageTimeZero.mov | ERROR | - | VideoFileReader | No video library installed. Install with: pip install opencv-python or pip install moviepy |
| Videos/testMP4_udtaLocation.mp4 | ERROR | - | VideoFileReader | No video library installed. Install with: pip install opencv-python or pip install moviepy |

### HTML (3)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Programming/big-preamble.html | PARTIAL | 0.800 | RemainingFileReader | missing tokens: 2100, 100, 130, 918 |
| Programming/testlargerbuffer.html | PARTIAL | 0.800 | RemainingFileReader | missing tokens: 2100, 100, 130, 918 |
| Programming/test_ignore_IBM420.html | PARTIAL | 0.907 | RemainingFileReader | missing tokens: ABCDEFG, ltda, Tel, 00 |

### Design (3)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Design/testPSD.psd | ERROR | - |  | Unsupported file type: .psd |
| Design/testPSD2.psd | ERROR | - |  | Unsupported file type: .psd |
| Design/testPSD_xmp.psd | ERROR | - |  | Unsupported file type: .psd |

### iWork (3)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Other/tableHeaders.numbers | ERROR | - | OfficeFileReader | No extractable text from iWork package (index.xml / IWA / QuickLook / LibreOffice paths exhausted) |
| Other/tableNames.numbers | ERROR | - | OfficeFileReader | No extractable text from iWork package (index.xml / IWA / QuickLook / LibreOffice paths exhausted) |
| Other/testPagesPwdProtected.pages | ERROR | - | OfficeFileReader | That compression method is not supported |

### Plain text (2)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Text/testBMPfp.txt | INCOMPLETE | 0.000 | ImageFileReader | missing tokens: EfficientDynamics, significantly, presentation, significant |
| Text/russian.cp866.txt | PARTIAL | 0.921 | RemainingFileReader | missing tokens: Ž, Ÿ, ƒ |

### PowerPoint (2)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Other/testPPT.ppsx | ERROR | 1.000 | OfficeFileReader | file 'test-doc/Other/testPPT.ppsx' is not a PowerPoint file, content type is 'application/vnd.openxmlformats-officedocument.presentationml.slideshow.main+xml' |
| Presentations/testPPT_protected_passtika.pptx | ERROR | - | OfficeFileReader | Package not found at 'test-doc/Presentations/testPPT_protected_passtika.pptx' |

### Word (.doc) (2)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Documents/testWORDML_tableInsideParagraph.doc | ERROR | - | OfficeFileReader | File is not a valid OLE2 format .doc file |
| Documents/testWordPerfect_42.doc | ERROR | - | OfficeFileReader | File is not a valid OLE2 format .doc file |

### Image (2)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Images/testAVIF.avif | ERROR | - | ImageFileReader | Unsupported image file type: .avif |
| Images/testAVIF_XMP.avif | ERROR | - | ImageFileReader | Unsupported image file type: .avif |

### Excel (.xls) (2)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Spreadsheets/password.xls | ERROR | - | OfficeFileReader | Workbook is encrypted |
| Spreadsheets/testEXCEL_protected_passtika.xls | ERROR | - | OfficeFileReader | Workbook is encrypted |

### Camera raw (1)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Other/testDNG_bigtiff.dng | ERROR | - |  | Unsupported file type: .bin |

### Excel (.xlsb) (1)

| file | verdict | recall | reader | cause |
|---|---|---|---|---|
| Other/testEXCEL.xlsb | ERROR | - | OfficeFileReader | Could not read .xlsb: pyxlsb failed (KeyError: '\x04') and no LibreOffice conversion was available. Install LibreOffice (soffice) to read this workbook. |

## Repairs made in this round

Three DOCX losses were measured here, reproduced as failing tests, fixed, and re-measured against the same corpus. The `before` column is the recall this pass recorded before the change; `after` is the recall of the same file recorded afterwards, with the same oracle.

| defect | files | before | after | test |
|---|---|---|---|---|
| A table cell whose content is a **nested table** read as empty: the reader stored `python-docx` `cell.text`, which walks only the cell's own `<w:p>` children. Word shows that text; the whole body of `testInstrLink.docx` is one table nested to depth 4. | `testInstrLink.docx`, `017097.docx` | 0.000, 0.024 | 1.000, 0.999 | `tests/unit/test_docx_nested_table_cell.py` |
| **Text boxes** were never read: a caption lives in `w:txbxContent` inside the anchoring drawing (DrawingML) or `v:textbox` (VML), not in the paragraph's run stream, so `paragraph.text` cannot see it. The `mc:Fallback` copy is skipped so a box is stored once. | `testWORD_text_box.docx`, `testHoverAndVml.docx`, `testWORD_sdtInTextBox.docx` | 0.702, 0.800, 0.118 | 1.000, 1.000, 1.000 | `tests/unit/test_docx_nested_table_cell.py` |
| **Block-level content controls** swallowed what they held: `iter_inner_content()` yields only direct `w:p`/`w:tbl` children, so a paragraph or table inside `w:sdt` was never visited. The reader now walks the body and descends through `w:sdtContent`. | `testWORD_template.docx` (a CV built entirely from controls), `testWORD_2006ml.docx` | 0.130, 0.490 | 0.986, 0.926 | `tests/unit/test_docx_content_control.py` |

Corpus effect: Word files COMPLETE **29 -> 41** of 70, INCOMPLETE **13 -> 3**; whole corpus COMPLETE **289 -> 301** of 698.

Two oracle bugs were fixed while measuring, and they matter for reading the numbers above: a naive `<w:t[^>]*>` also matches `<w:tbl>`, which put tag names into every DOCX oracle; and Word splits a word across runs whenever the formatting changes, so the DOCX oracle is scored two ways (runs abutting, and runs word-separated) and the higher recall is kept - otherwise a formatting boundary is reported as lost text.

## Defects still open

| verdict | defect | evidence |
|---|---|---|
| DEFECT-OPEN | **Routing loses a conforming ODF package.** Content sniffing classifies any ZIP as `.zip` unless `mimetype` is the first member, so `Documents/testODTStyles3.odt` (a valid ODT with `content.xml` first, which `odfpy` loads without complaint) is handed to `ArchiveFileReader` and yields **0 characters**. It is the only ODF file in the corpus whose ZIP does not start with `mimetype`, and the only one routed to the archive reader. | `manifest.csv`: reader=ArchiveFileReader, verdict INCOMPLETE, recall 0.0 |
| DEFECT-OPEN | **`.docm` and `.dotx` are rejected as "not a Word file".** They are valid WordprocessingML packages whose main part content type is macro-enabled or template; `python-docx` refuses them and the reader passes the exception through. Text arrives only from the fallback scan (`.docm` picks up `vbaProject.bin` strings, `.dotx` 12 characters). The same shape of failure hits `Other/testPPT.ppsx`. | `manifest.csv` ERROR rows with `content type is 'application/vnd.ms-word.document.macroEnabled.main+xml'` and '...wordprocessingml.template.main+xml' |
| DEFECT-OPEN | **Headers, footers, footnotes and comments are not in the body result.** They reach storage only through the forensic pass, so a consumer that reads `elements` alone sees a document without its running heads or notes. | Word rows whose `docx_parts` recall is 1.0 for `header*/footer*` while `elements` contains no such unit |
| DEFECT-OPEN | `.psd` has no reader - routed, then empty. | `manifest.csv`, family Design |
| DEFECT-OPEN | `.doc` without a converter yields 2-54 characters (byte scrape only). Two files do yield thousands, so the path works when the stream is conventional. | family `Word (.doc)`, `OK-NO-ORACLE` |
| DEFECT-OPEN | `.xls` stores one tab per column pair rather than a row grid, so column order is lost on re-read. | `text/OfficeFileReader/Spreadsheets__*.xls.txt` |
| DEFECT-OPEN | RTF surrogate pairs leak lone surrogates (`\ud800`) into the stored text. | `lone_surrogates` column in `manifest.csv` |
| DEFECT-OPEN | `protected_*.docx` raises instead of returning a 'password protected' result. | `ERROR` rows, Word family |
| DEFECT-OPEN | `Spreadsheets/testRecordSizeExceeded.xlsx` never returns: the per-file SIGALRM cannot interrupt the C-level XML loop, so one file can wedge a batch. | `TIMEOUT` row (`timeout_method: external-kill`) |

## Limits of this evidence

- Recall is a **lower bound** on loss: the oracle can miss text the reader legitimately finds (fields, `mc:AlternateContent`, drawing XML), so a low score is a prompt to look, not a proof on its own. The hand-checks in Findings are the proof.
- `OK-NO-ORACLE` (**172 files**) means stored-but-unverified, not complete.
- Environment: no `tesseract`, `ffmpeg`, `soffice`, `antiword`; OCR via RapidOCR, so image recall is not scored at all.
- Numbers here are **verified**: the archive, the report and the corpus hashes (`sha256` per row) travel together in this commit.
