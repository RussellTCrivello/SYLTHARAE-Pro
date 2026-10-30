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

## Rebuilt in this round, and both full suites run in both environments

Both virtualenvs were destroyed with the sandbox and rebuilt from
`requirements.lock` alone; the installed-set hashes came back identical
(`1353dba7…` locked, `e1c90bc3…` provisioned), which is what makes the two
environments reproducible rather than remembered.

| suite | environment | tests | passed | failed | errors | skipped |
|---|---|---|---|---|---|---|
| unit | locked | 3749 | 3670 | 38 | 0 | 41 |
| unit | locked + `ffmpeg` on `PATH` | 3749 | 3684 | 38 | 0 | 27 |
| unit | provisioned | 3749 | 3729 | 7 | 0 | 13 |
| integration | locked | 1487 | 1395 | 4 | 0 | 88 |
| integration | provisioned | 1487 | 1479 | 4 | 0 | 4 |

Per id: **38 of 38** ids classed ENV-OCR (31) or ENV-FFMPEG (7) pass in the
provisioned runs; in the locked environment 31 fail and 7 skip. The `ffmpeg`
column exists to answer a narrower question and is not a separate class: with a
runnable binary the locked environment passes the same 14 media ids the
provisioned one does.

What the provisioned environment still does not fix, and why it is not an
environment question: the 4 translation-coverage ids (they read `.po` files),
the 3 NEEDS-DECISION ids and the 2 licensing ids (they read metadata), and the 2
`test_no_machine_paths` ids (they read committed historical evidence).

## Final pass — the lock itself carries working OCR (supersedes the section above)

Measured 2026-10-29/30 at commit `8a81a69`, python 3.11.2, sandbox with no
system `ffmpeg` and no system `tesseract`.

**What was wrong.** `requirements.lock` listed both `opencv-python==5.0.0.93`
(the GUI build) and `opencv-python-headless==5.0.0.93`. Both wheels unpack
into the same `cv2/` directory, and a plain `pip install -r requirements.lock`
lets the resolution win for the GUI build, so `import cv2` raised
`ImportError: libGL.so.1: cannot open shared object file`. That single fact
produced the 31 ENV-OCR failures and the 84 OCR skips recorded above.

**What changed.** The GUI build is out of the lock, and the lock states how it
must be installed - `pip install --no-deps -r requirements.lock`, because the
file is a complete freeze and re-resolving it reintroduces rapidocr's GUI
dependency. Three guards, all measured:

| guard | behaviour |
|---|---|
| `tools/audit/rebuild_lock_env.py` | builds the venv from the lock, refuses unless exactly `opencv-python-headless` owns `cv2/` **and** `import cv2` works, then runs `env_lock.py --check` |
| `tools/audit/env_lock.py --check` | reports `opencv usable <version> (owners: …)` and exits **3** when the lock carries OpenCV that cannot be imported - a lock whose OpenCV cannot load now fails loudly instead of quietly skipping 84 tests |
| `tools/audit/r22_baseline.py` | refuses to classify a run whose environment carries unusable OpenCV |

| property | value |
|---|---|
| packages | 117 (was 118: the GUI OpenCV build) |
| installed-set hash | `6d1421aeb8dd44ffd012d1a059553b0cd23bd901601fe526d8be9ecae7b2fe93` |
| `cv2` | 5.0.0, imports, owner `opencv-python-headless` |
| engines usable | rapidocr_onnxruntime, pytesseract, fitz, docx, pptx, openpyxl, mutagen |
| engines absent | `tesseract` binary, `ffmpeg` binary |
| `env_lock.py --check` | match yes, exit 0 |

**The provisioned venv is retired as a category.** It is not reproducible in
this sandbox any more (it was destroyed with the sandbox and is not rebuilt
here), and it is no longer needed: the 31 ids that only passed in it now pass
in the lock, per id. What it provided beyond the lock was an `ffmpeg` binary.
That is measured separately and honestly, by putting a static ffmpeg on `PATH`
(unpacked from the `imageio-ffmpeg` wheel into `/tmp/ffbin`, **not** installed
into the venv, so the lock's set hash is unchanged):

| suite | environment | tests | passed | failed | errors | skipped |
|---|---|---|---|---|---|---|
| unit | lock, `8a81a69` | 3796 | 3765 | 6 | 0 | 25 |
| unit | same lock + `ffmpeg` on `PATH` | 3796 | 3779 | 6 | 0 | 11 |
| integration | lock, `8a81a69` | 1487 | 1479 | 4 | 0 | 4 |

Both runs cover the same commit, `8a81a69`. The `ffmpeg` column differs by
exactly the 14 media ids (`test_video_metadata_only` 7, `test_audio_metadata_fallback`
7) and by no failure: putting a binary on `PATH` fixes skips, not failures.
The one EXTERNAL-BINARY skip left in both is `test_deploy_nginx` (no `nginx`,
no `openssl`).

Against the previous record in this file:

| suite | before | now | delta |
|---|---|---|---|
| unit passed | 3670 | 3765 | +95 |
| unit failed | 38 | 6 | −32 |
| unit skipped | 41 | 25 | −16 |
| integration passed | 1395 | 1479 | +84 |
| integration failed | 4 | 4 | 0 |
| integration skipped | 88 | 4 | −84 |
| skips, both suites (the pin) | 129 | 29 | −100 |

**Every failing id at `8a81a69`, classified.** Unit (6):

| id | class | evidence |
|---|---|---|
| `test_identifiers_intel::test_detects_email_phone_ipv4_and_links_to_sentence` | NEEDS-DECISION (owner) | the detector sets `signal_type="identifier"` for every hit and carries the kind in `evidence["kind"]` (`core/detection/identifiers_intel.py:24-35`); the test asserts the kind as the signal type. Carried from the previous round under D-4 (do not edit the test) |
| `test_identifiers_intel::test_email_not_double_counted_as_ipv4_fragment` | NEEDS-DECISION (owner) | same |
| `test_licensing::test_installed_dependencies_are_agpl_compatible` | ENVIRONMENT | two PyMuPDF sub-distributions publish no licence metadata, so the checker reports `unknown` for them |
| `test_licensing::test_checker_cli_exits_zero_on_this_environment` | ENVIRONMENT | same finding, via the CLI |
| `test_no_machine_paths::test_no_file_contains_the_checkout_path` | portability gate | the gate scans the checkout path and the committed audit artefacts; documented as permanently red in this round's report |
| `test_no_machine_paths::test_no_machine_specific_paths_or_hosts` | portability gate | same |

Integration (4): `test_translation_coverage::test_no_catalog_entry_is_empty_or_fuzzy[ar|he|fa|hr]` - the four owner-reserved translation ids, decision due 2026-11-05; they read the `.po` catalogues, not the database, so no environment changes them.

Nothing on this list is unexplained, and no id changed class because the
environment changed: the six unit ids fail identically with `ffmpeg` on `PATH`.
