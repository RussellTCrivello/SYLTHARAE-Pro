# Decision: ffmpeg stays an optional binary (not a pinned wheel)

Round 22 wrap-up, item C. Decided 2026-10-30. Labels: **measured** (a command in
this branch), **inferred**, **unverified**.

## What was decided

`requirements.lock` **does not** gain a binary-providing wheel. ffmpeg stays an
**optional external binary**, documented, and the 14 tests that need it stay
skipped in the locked environment and are run explicitly with a binary on
`PATH`.

## The two options, and what each costs

| | option 1: pin `imageio-ffmpeg==0.7.0` in the lock | option 2: keep ffmpeg external (chosen) |
|---|---|---|
| skip pin | 29 → **15** (measured: the 14 media ids pass) | stays **29** |
| media coverage by default | 14 more ids run in every locked run | 14 ids run only where a binary is provided |
| bytes per install | **+28.1 MB** wheel (measured, `imageio_ffmpeg-0.7.0-py3-none-manylinux2014_x86_64.whl`, sha256 `4e1f36be…4408`) | none |
| determinism | one bundled ffmpeg build for everyone | the host's build, or none |
| platform story | 6 platform wheels in the release; pip picks one, so the pinned *version* is portable | already handled: the project installs ffmpeg per platform |
| licensing | the wheel's metadata says **BSD-2-Clause**, but the binary it carries is a **GPLv3** static build (johnvansickle/iOS-style static); shipping it needs a notice entry and an owner decision about redistribution | no bundled binary, no new obligation |
| consistency with the deployment model | adds a media engine the project deliberately documents as an external dependency | matches `requirements.txt`'s own `[WIN-BINARY]` instruction: "Install a Windows FFmpeg build, put ffmpeg.exe/ffprobe.exe on `PATH`" |
| lock hash | every recorded set hash in the workbook becomes historical and must be re-recorded | unchanged: 117 packages, `6d1421ae…` |

## Why option 2

Three reasons, in order of weight:

1. **The project already answers this question, and answers it "external".**
   `requirements.txt` lists ffmpeg under native runtime requirements that pip
   cannot supply, with instructions per platform. Adding a wheel would make the
   lock disagree with the product's own deployment documentation - and would
   only cover the platforms whose wheels exist.
2. **The licensing obligation is real and is the owner's to accept.** The wheel
   declares BSD-2 and carries a GPLv3 static binary. Pinning it puts a GPL binary
   inside every install of an AGPL application, which needs a `THIRD_PARTY_NOTICES`
   entry and a redistribution decision that no test can make.
3. **The coverage is recoverable without touching the lock - measured.** With a
   static ffmpeg unpacked onto `PATH` (not installed into the venv, so the set
   hash is unchanged), the full unit suite is **3779 passed, 6 failed, 11
   skipped** against **3765 / 6 / 25** without it: the same 14 ids, the same six
   failures. A CI step that provides a binary therefore buys exactly what
   pinning would buy, and buys it without changing what the lock means.

The cost, stated plainly: **a default run does not exercise media reading**, and
"skips are not passes" is a rule this choice accepts a documented exception to.
That exception is pinned by id (below), counted in the pin, and reversible in one
line if the owner decides the 28 MB and the GPL notice are worth 14 ids.

## The 14 ids that need a binary — measured, by id

| module | ids |
|---|---|
| `tests/unit/test_audio_metadata_fallback.py` | `test_a_refused_tag_parse_still_yields_container_metadata[testAAC.aac]`, `[testAACid3.aac]`, `[testMP4_drm.m4a]`, `[testMP4_truncated.m4a]`, `test_a_successful_tag_read_also_states_no_speech`, `test_the_recovered_metadata_is_stored`, `test_the_tag_reader_failure_is_kept_on_the_record` (7) |
| `tests/unit/test_video_metadata_only.py` | `test_a_decoder_failure_falls_back_to_the_container`, `test_container_tags_are_stored_when_present`, `test_media_metadata_is_in_provenance_not_only_in_text`, `test_no_decoder_states_that_no_speech_was_extracted`, `test_no_decoder_still_returns_metadata`, `test_the_stored_text_says_that_speech_was_not_extracted`, `test_video_metadata_reaches_the_stored_text` (7) |

The eighth id in `test_video_metadata_only` (`test_the_opencv_path_also_says_no_speech_was_extracted`)
needed `cv2` rather than ffmpeg and no longer skips - the lock's OpenCV fix
covered it.

## How to run them

```bash
# a static build, not installed into the venv
python3 -c "import imageio_ffmpeg, shutil; print(imageio_ffmpeg.get_ffmpeg_exe())"
PATH="<dir containing ffmpeg>:$PATH" /tmp/rv/bin/python -m pytest \
    tests/unit/test_video_metadata_only.py tests/unit/test_audio_metadata_fallback.py
```

Measured this round: **16 / 16 and 8 / 8 pass** with a binary on `PATH`.

## If the owner reverses this

One line in `requirements.lock` (`imageio-ffmpeg==0.7.0` in sorted position),
then `tools/audit/rebuild_lock_env.py --venv /tmp/rv` (the set hash changes),
then re-record the pin. The 14 ids above are the acceptance criteria: they must
stop skipping. The licence entry for the bundled binary is the part that needs a
person.
