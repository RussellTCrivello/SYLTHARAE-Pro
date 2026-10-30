# Final run versus baseline (generated)

- Files: baseline 698, final 698
- Stored characters: baseline 13,555,354, final 13,558,676
- Files only in the baseline: 0
- Files only in the final run: 0
- Recall regressions: 0

| Verdict | Baseline | Final |
|---|---|---|
| COMPLETE | 328 | 331 |
| EMPTY-AGREED | 1 | 1 |
| EMPTY-PLAUSIBLE | 143 | 140 |
| ERROR | 50 | 52 |
| NEAR-COMPLETE | 6 | 5 |
| OK-NO-ORACLE | 148 | 148 |
| PARTIAL | 2 | 1 |
| UNVERIFIABLE | 20 | 20 |

## Verdict changes

| file | baseline | final | recall before | recall after |
|---|---|---|---|---|
| `Documents/protected_normal_case.docx` | EMPTY-PLAUSIBLE | ERROR | None | None |
| `Documents/protected_upper_case.docx` | EMPTY-PLAUSIBLE | ERROR | None | None |
| `Documents/testWORD_2006ml.docx` | NEAR-COMPLETE | COMPLETE | 0.9863 | 1.0 |
| `Documents/testWORD_protected_passtika.docx` | EMPTY-PLAUSIBLE | ERROR | None | None |
| `Other/testWORD_template.dotx` | PARTIAL | COMPLETE | 0.8387 | 1.0 |
| `Spreadsheets/testRecordSizeExceeded.xlsx` | ERROR | COMPLETE | None | 1.0 |

## Recall changes (more than 0.0005)

| file | before | after | delta |
|---|---|---|---|
| `Other/testWORD_template.dotx` | 0.8387 | 1.0 | +0.1613 |
| `Documents/testWORD_2006ml.docx` | 0.9863 | 1.0 | +0.0137 |

## Storage changes (more than 2 %)

| file | chars before | chars after | change |
|---|---|---|---|
| `Documents/testWORD_tableInRunInsideParagraph.docx` | 939 | 1,291 | +37.5 % |
| `Other/testWORD_template.dotx` | 1,159 | 1,437 | +24.0 % |
| `Documents/testWORD_template.docx` | 1,177 | 1,364 | +15.9 % |
| `Documents/testWORD_formattingFlipUnderlineOrder.docx` | 10,197 | 11,790 | +15.6 % |
| `Documents/testWORD_missing_text.docx` | 272 | 294 | +8.1 % |
| `Documents/testWORD_2006ml.docx` | 2,996 | 3,230 | +7.8 % |
| `Documents/testWORD_numbered_list.docx` | 2,142 | 2,286 | +6.7 % |
