# Environment record — Round 22 closeout

Two environments, both rebuilt from files in this repository, both with their
installed set hashed by `tools/audit/env_lock.py`. A run is only compared with
another run that carries the same hash, and `tools/audit/r22_baseline.py`
**refuses** to classify a run whose set does not match `requirements.lock`
(exit 2) unless the run is explicitly labelled.

Paths are written `{tmp}` for the scratch root, because
`tools/audit/check_artifact_portability.py` treats a literal temp directory in a
committed artefact as a leak.

## The locked environment — every published number comes from here

| item | value | command |
|---|---|---|
| python | 3.11.2 | `python -V` |
| virtualenv | `{tmp}/rv`, built from **`requirements.lock` alone** | `python3.11 -m venv {tmp}/rv && {tmp}/rv/bin/pip install -r requirements.lock` |
| packages | 118 | `{tmp}/rv/bin/python tools/audit/env_lock.py --report` |
| installed-set hash | `1353dba7e052f925f0ae967601c24eae17a398a7335228ed0231d82adabf6814` | same command |
| lock file hash | identical to the installed-set hash | `tools/audit/env_lock.py --check` |
| rebuild proven | yes: `{tmp}/rv_prov` was built from the lock alone and reported the same set before it was modified | 2026-10-29 |

`requirements.lock` is a `pip freeze` of the resolved set, sorted, with a header
naming the four things it cannot capture:

| not captured by the lock | consequence | where it is handled |
|---|---|---|
| native libraries (`libGL.so.1` and friends) | `import cv2` fails although OpenCV is installed | recorded below; the failing ids are classified ENV-OCR |
| the `tesseract` binary | `pytesseract` imports but no OCR engine is available | the OCR modules skip with a reason; proven to pass in the provisioned environment |
| the `ffmpeg` binary | the container-metadata reader has no fallback | same: skipped in the lock, passing when present |
| `pgserver`'s PostgreSQL build | the crash-recovery tests need a server | the suite probes and skips with the attempts listed |

### Engines the lock environment actually has

| engine | state | why |
|---|---|---|
| `cv2` | **fail**: `libGL.so.1` missing | the GUI `opencv-python` wheel, pulled in by `rapidocr-onnxruntime`, owns the shared `cv2/` files and needs `libGL` |
| `rapidocr_onnxruntime` | **fail**: same import | it imports `cv2` |
| `pytesseract` | ok (module) | the `tesseract` binary is absent, so it cannot read anything |
| `tesseract` | absent | not a Python package |
| `ffmpeg` | absent | not a Python package |
| `fitz`, `docx`, `pptx`, `openpyxl`, `mutagen` | ok | — |

## The provisioned environment — what the four skipped tests need

| step | command |
|---|---|
| base | `python3.11 -m venv {tmp}/rv_prov && {tmp}/rv_prov/bin/pip install -r requirements.lock` |
| make `cv2` usable | `{tmp}/rv_prov/bin/pip uninstall -y opencv-python` then `pip install --force-reinstall --no-deps opencv-python-headless==5.0.0.93` (headless must be installed **last**: the two wheels write the same `cv2/` files) |
| give the readers a binary | `pip install imageio-ffmpeg` (0.7.0) and symlink its ffmpeg onto `PATH` |
| server for crash recovery | `pip install pgserver` |

**Delta against the lock, printed by the tool, not asserted:**

| direction | package |
|---|---|
| missing from this environment (in the lock) | `opencv-python==5.0.0.93` |
| extra in this environment (not in the lock) | `imageio-ffmpeg==0.7.0` |

`opencv-python-headless==5.0.0.93` is present in both, so the only version-level
change is the package that owns `cv2/`. The set hash is
`e1c90bc3fc0671011a4e63574b05f3b56552f2678a98cd92cd23827cde327c3a`, and every
number from it is labelled with that fact. Engines: `cv2` 5.0.0 (ok), numpy
2.4.6, `rapidocr_onnxruntime` (ok), engine `RapidOcrEngine`, `ffmpeg` present,
`tesseract` still absent — the OCR path used is the RapidOCR wheel, not
tesseract.

### What the provisioned run proves

| module | locked env (skips) | provisioned env |
|---|---|---|
| `test_archive_lineage` | 8 skipped (no OCR engine) | passes |
| `test_archive_nesting` | 19 skipped | passes |
| `test_email_lineage` | 16 skipped | passes |
| `test_file_details_api` | 10 skipped | passes |
| `test_ocr_searchable` | 6 skipped | passes |
| `test_provenance_persisted` | 8 skipped | passes |
| `test_universal_recursion` | 13 + 4 skipped | passes |
| `test_resume_real_database` | 1 documented skip | 25 pass, the same 1 skip |
| `test_video_metadata_only` | 7 skipped / 3 unguarded readers | all pass |
| `test_audio_metadata_fallback` | skipped without ffmpeg | passes |

Run: 160 tests, **159 passed, 0 failed, 1 skipped** (the moved-duplicate known
gap). So the skips in the locked environment are the environment, not the code:
the four tests this round moved from "failing" to "skipped" pass as soon as an
ffmpeg binary and a working `cv2` exist.

## Why the earlier numbers were measured in a different environment

The Round 21 closeout ran with `rapidocr_onnxruntime` + `opencv` installed. The
Round 22 baseline runs were made after a re-clone rebuilt the venv from
`requirements.txt` alone. The two were not comparable, and "34 pre-existing, then
67 pre-existing" is the symptom of that, not a code change. Every number in this
workbook now names its environment hash, and the classifier refuses a run that
does not match the lock.
