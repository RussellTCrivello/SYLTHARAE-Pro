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
