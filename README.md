# SYLTHARAE

SYLTHARAE is a multidimensional information intelligence platform. It
discovers, reads, extracts, classifies, indexes, analyses, preserves and
connects information across large, mixed collections of files: documents,
spreadsheets, e-mail and mailboxes, archives, images (with OCR), audio,
video, e-books, databases and diagrams.


## Import jobs are process-local

Batch and single-file imports run inside the web process. The registry is
`Api/task_manager.py` (`FileProcessingTaskManager._tasks`, a dictionary of live
`TaskProgress` objects), not a database table: an import writes nothing to
`jobs` or `job_events`, and `GET /api/jobs` therefore lists scheduled jobs
only - never imports.

Consequences, all measured in round 4
(`audit_report/findings/performance_measurements.md` §6, §7):

* A restarted or killed process loses the imports it had queued or running.
  Nothing resumes them and no row records that they existed; the files are
  simply not imported and must be submitted again.
* The number of imports that can run at once is capped (currently 5). With
  batch import, a file that finds no free slot is reported as `deferred` in the
  response (`accepted = queued + deferred`, `accepted + rejected = total`) and
  has to be resubmitted later - it is not queued anywhere that survives the
  request.
* Because the queue lives in one process, running the app behind multiple
  workers gives each worker its own queue and its own `GET /api/jobs` view.

Persisting import jobs so they survive a restart is a schema change and is
therefore not implemented; it is listed as a proposal in
`audit_report/R4_decisions.md` (M-2).

## Licence

SYLTHARAE is released under the **GNU Affero General Public License**,
version 3 or (at your option) any later version: `AGPL-3.0-or-later`. The full
text is in [`LICENSE`](LICENSE), the same expression the package metadata
declares (`license` in `pyproject.toml`).

The third-party components this software bundles and depends on are
enumerated by `tools/licenses/check_licenses.py` against the installed
environment; the bundled static assets and fonts carry their own licence
files next to them (for example `static/fonts/OFL-*.txt`).

Section 13 of the licence requires that users interacting with the software
over a network be offered its source. The interface shows a source link on
every page; its target is `SOURCE_CODE_URL` (see `.env.example`), defaulting to
`apps/web/app.py:DEFAULT_SOURCE_CODE_URL`.

**Open, not decided here:** a consolidated `THIRD_PARTY_NOTICES.md` (the file
`pyproject.toml` lists in `license-files`) has not been written, and the
licence metadata of the two optional PDF packages `pymupdf-layout` /
`pymupdf4llm` declares nothing usable. Both are recorded in
`audit_report/R4_decisions.md` under D-6 rather than guessed at.
