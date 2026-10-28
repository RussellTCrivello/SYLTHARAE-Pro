# Environment record — Round 22 follow-up baseline (A1)

Measured 2026-10-27, `6cf97f3`, in the sandbox after a re-clone.

Paths are written `{tmp}` for the scratch root, because
`tools/audit/check_artifact_portability.py` treats a literal temp directory in a
committed artefact as a leak — it caught this very file when it was first
written, which is the gate doing its job.

| item | value | command |
|---|---|---|
| python | 3.11 | `python -V` |
| virtualenv | `{tmp}/rv`, built from `requirements.txt` + `pytest` + `pgserver` | `python -m venv {tmp}/rv` |
| pip freeze | 118 packages, `sha256 e9092ad275237544a6a196704aac0938f18f41a23e4e6036bae6ed9dba4eb641` | `pip freeze \| sort \| sha256sum` |
| OCR engine | **absent**: no `tesseract` binary, no `rapidocr_onnxruntime`, no `cv2`, no `paddleocr`, no `easyocr` | `which tesseract`; import sweep |
| `pytesseract` | 0.3.13 installed, unusable (no binary) | import sweep |
| readers | `pymupdf(fitz)` 2.0, `python-docx` 1.2.0, `python-pptx` 1.0.2, `openpyxl` 3.1.5 | import sweep |
| optional readers | `pandas`, `reportlab`, `pdfplumber` **missing** | import sweep |
| scheduler dep | `apscheduler` 3.11.3 present | import sweep |
| leaked `pgserver` dirs | **0** | `ls -d {tmp}/pgdata_* \| wc -l` |
| free disk in the scratch root | 18 G of 21 G (3% used) | `df -h {tmp}` |
| memory | 3 GB total, ~2 GB free | `free -g` |
| cpu | 2 | `nproc` |

## Why the earlier numbers were measured in a different environment

The Round 21 closeout ran with `rapidocr_onnxruntime` + `opencv` installed in the
venv (the OCR matrix, embedded-image and rotated-PDF modules pass there). The
Round 22 runs were made after a re-clone rebuilt the venv from
`requirements.txt` alone, which has no OCR engine. **The two runs are therefore
not comparable**, and the "34 pre-existing, then 67 pre-existing" pair is the
symptom, not a code change.

The comparison in `audit_report/r22_workbook/baseline_ids.csv` is made with both
commits in *this* environment, which is the environment these numbers are
published from.
