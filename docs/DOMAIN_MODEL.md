# Domain Model

What the product talks about, in the words the rest of the codebase uses. The
tables named here are the ones `docs/reference/DATABASE_SCHEMA.md` lists (it is
generated from the migrated database, so it is never out of date); this
document explains what they mean and how they relate.

## The core nouns

* **Source** (`sources`) - where a file came from: a folder, an archive, an
  upload batch or a mail store. A source has a *side* on which it sits.
* **Side** (`sides`) - the standing answer to "which half of the material is
  this": inbound and outbound for a mail corpus, or the equivalent pair a
  different corpus needs. Sides are what the sources list is grouped by.
* **Path** (`paths`) - one file at one location, with its size, timestamps and
  the revision history in `path_revisions`. A path is re-read many times; its
  content hash is what identifies a *version*.
* **Content** (`contents`, `contents_raw`) - a stored file version. The raw
  bytes live in `contents_raw`; `contents` carries the extracted text and the
  provenance of how it was obtained.
* **Word** (`words`) - a tokenised term from a content, with its language,
  counts and the punctuation stripped around it (`punctuation`). Words are
  what search and the word lists operate on.
* **Hash** (`hashs`) - a content digest, used to detect the same file seen
  twice and to skip re-extraction. `hash_contexts` records what the digest was
  taken over, so a change of algorithm is visible rather than silent.
* **Keyword** (`keywords`, linked through `keywords_hashs`) - a term an analyst
  marked as interesting, as opposed to every word that happens to occur.
* **Category** (`categorys`, `words_categorys`) - an analyst's own grouping of
  words and files. `analyst_categories` and `analyst_file_categories` are the
  analyst-facing side of the same idea, with `analyst_categorization_log`
  recording who assigned what and when.
* **Signal** (`content_signals`, `content_signal_runs`, `content_signal_places`)
  - something a *rule* found in a content: a detection, a temporal signal, a
  place mention. A signal is always traceable to the run that produced it and
  to the rule version that was in force.
* **Rule and scenario** (`monitoring_rules`, `monitoring_rule_versions`,
  `rule_evaluations`, `scenarios`, `scenario_versions`, `scenario_outcomes`,
  `scenario_evaluations`) - the detection logic and the sequence logic built on
  top of it, both versioned: an evaluation records the version it used, so
  changing a rule never rewrites history.
* **Place** (`geo_places`, `geo_place_names`, `path_geo_mentions`,
  `geo_gazetteer_loads`) - a resolved geographic entity, the names that resolve
  to it, and the mentions found in a path. The gazetteer load records which
  release of the name data produced them.
* **Job and schedule** (`jobs`, `job_events`, `job_schedules`) - long-running
  work and its event stream. A job has a state machine
  (`services/jobs/job_state.py`); `job_events` is the audit trail the progress
  views read.
* **Report** (`report_runs`, `report_run_datasets`, `report_run_analyses`,
  `report_artifacts`, `report_baselines`) - a generated report, the dataset it
  was run over, the analyses inside it and the files it produced.
* **User, session, audit** (`users`, `sessions`, `audit_log`) - accounts,
  sign-ins and the append-only record of who did what. The audit log is the
  authority on activity: the UI never infers it.
* **Settings and navigation** (`user_navigation_prefs`, `saved_searches`,
  `saved_search_imports`, `translation_overrides`, `schema_migrations`) - what
  a user chose, what they saved, and the migration ledger that says which
  schema version is in place.

## Text extraction and provenance

Every content records how its text was obtained. Hand-written text, a text
layer in a PDF and text read from an image by OCR are not the same evidence,
and the difference is kept rather than flattened: `extraction_provenance` is
where it lives, and `pipeline/storage_pipeline.py` is the only writer.

For OCR, `extraction_provenance.ocr` holds the fields below. They are read
straight out of the pipeline's own output - the unit test for this paragraph
runs the pipeline for an image and a PDF and compares both directions, so a
field added to the code without being described here fails, and a field
described here but never stored fails too.

* `engine` and `engines`: the OCR engine that ran, and every engine that
  contributed when more than one did.
* `engine_version`: the version string the engine reported; evidence is not
  reproducible without it.
* `derived`: whether the text in the record came from OCR at all.
* `attempted` and `successful`: whether OCR was tried, and whether it produced
  text. A failed attempt is recorded, not discarded - "no text" and "could not
  read" are different answers.
* `confidence`: the mean confidence when the engine reports one; it is `null`
  when it does not.
* `confidence_error`: why no confidence figure exists, when the engine failed
  to produce one.
* `language`: the language(s) OCR was told to expect.
* `input_variant`: whether the image OCR ran on was the `original` or a
  `preprocessed` one, so the reader knows what was actually read.
* `rotation`: the rotation applied to the image before OCR, in degrees.
* `rotated_pages`: for a multi-page document, which pages needed that.
* `missing_languages`: expected languages whose trained data was absent. This
  is how a silent accuracy loss becomes visible.
* `ocr_pages` and `total_pages`: how much of the document was read by OCR, so
  a mostly-text PDF with one scanned page reads differently from a scan.

## Where this is enforced

* **Rules and scenarios** are declarative: `core/` holds the models and the
  engines, and a definition that cannot be satisfied is rejected at save time
  rather than producing an empty evaluation.
* **Signals** carry their rule version; `services/detection/` is the only
  writer, and re-detection supersedes rather than rewrites.
* **Anything user-visible** is declared in `core/interfaces/registry.py` - see
  `docs/INTERFACE_REGISTRY.md`.
