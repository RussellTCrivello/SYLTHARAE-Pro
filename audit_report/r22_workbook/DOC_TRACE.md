# Every claim in `docs/ARCHITECTURE.md` and `docs/DOMAIN_MODEL.md`, and what proves it

Round 22, item C. Written 2026-10-29. Labels: **measured** (a test derives it
from the code and the suite runs it), **inspected** (read out of the code by
hand this round, no test derives it), **unverified** (kept, with no evidence).

Both documents were 129 lines of prose that the suite touched in exactly one
place: the job state diagram. Everything else was written once and never read
back. Two of those sentences were false. They are corrected in the documents
and named as corrections below.

## `docs/ARCHITECTURE.md`

### Opening paragraph

| sentence | code | evidence | label |
|---|---|---|---|
| "the diagrams are checked against the code they depict" | `tests/unit/test_architecture_diagrams.py`, `tests/unit/test_architecture_claims.py` | 22 tests, all pass | measured |
| "the job state machine is compared with `services.jobs.job_state.TRANSITIONS` on every run" | `services/jobs/job_state.py` | `test_job_state_diagram_matches_transitions` | measured |
| "a state the code gains or loses without the diagram following fails the suite" | same | same test: edge sets compared as sets, both directions | measured |

### Request path (flowchart)

| edge / node | code | evidence | label |
|---|---|---|---|
| `Browser --> Flask[apps/web/app.py]` | `apps/web/app.py` | `test_every_path_the_document_names_exists` | measured |
| `Flask --> Auth[core.security.init_auth]` | `apps/web/app.py:488` `init_auth(app)` | inspected (line read this round); path existence measured | inspected |
| `Auth --> Blueprint[Api/routes, Api/blueprints]` | `app.register_blueprint(...)` ×~10 in `apps/web/app.py` | inspected | inspected |
| `Blueprint --> Service[Api/services, services]` | `Api/routes/analysis.py` etc. import `Api.services`; `Api/blueprints/files.py` too | inspected; the same import graph is a measured input of `test_the_pinned_layer_violations_are_the_only_ones` | inspected |
| `Service --> DB[PostgreSQL]` | `Api.utils.execute_query` | inspected | inspected |
| `Blueprint --> Templates[templates]` | `render_template` is used only in `Api/` and `apps/` | `services/render_template` = 0, measured by the same test file | measured (absence) |
| `Blueprint --> Pipeline[IntegratedFileReader, Api/routes/analysis.py]` | `Api/routes/analysis.py:92,262` | `test_the_pinned_layer_violations_are_the_only_ones` pins the two imports | measured |
| `Pipeline --> DB` | `pipeline/storage_pipeline.py:160-195` import `database.*` | inspected | inspected |

### "A read of stored text answers from the database and reads no file"

| claim | advice | label |
|---|---|---|
| the file-content endpoints return stored text | `Api/blueprints/files.py:1022` `load_text_content(file_id)` | inspected |
| no route or blueprint imports a reader | 0 imports of `reader_file` in `Api/routes` + `Api/blueprints` | measured (`test_the_layer_rules_that_hold_are_measured_and_hold`) |
| no route imports `StoragePipeline` | 0 imports of `storage_pipeline` in `Api/routes` + `Api/blueprints` | measured (same test's blanket statement + the pinned table) |

### Ingestion sequence

| message | code | label |
|---|---|---|
| `C->>P: ingest a path` | `apps/cli/main.py` is the only production caller of `IntegratedFileReader(...)` outside `Api/routes/analysis.py` | measured (entry point exists: `test_every_method_the_sequence_names_exists_on_its_class`) |
| `P->>D: main_specify_method_of_reading_the_file(file_info)` | `pipeline/integrated_reader.py:16,649` | measured |
| `D->>O: OCR only when no usable text layer was found` | `reader_file/readers/read_img_fast.py:15`, `read_pdf.py:39` import `core.ocr` | measured (`test_ocr_is_attributed_to_the_readers_that_call_it`) |
| `O-->>D` | `core/ocr/__init__.py` exports `get_ocr_engine`, `recognize_best` | measured (imports resolve) |
| `D-->>P: text, metadata, read errors` | reader return dicts | inspected |
| `P->>S: _store_file_sync(file_info, content)` | `pipeline/integrated_reader.py:696,1908,1949` | measured (`test_the_storage_call_the_sequence_names_exists`) |
| `S->>DB: store the occurrence and its extraction_provenance` | `pipeline/storage_pipeline.py:1498,1612`, `paths.extraction_provenance JSONB` | measured (`test_the_provenance_column_exists_on_the_occurrence`) |
| `S-->>P: path_id, outcome` | `_store_file_sync` returns `path_id` | inspected |

### Corrections made this round

| was | is | why |
|---|---|---|
| `R->>P: extract(file)`, i.e. a web route calling `StoragePipeline.extract` | the request flowchart and the ingestion sequence are two diagrams | no route or blueprint imports `StoragePipeline`, and the class has no method `extract` (`test_every_method_the_sequence_names_exists_on_its_class` asserts both) |
| `P->>O: OCR only when no text layer was found` (pipeline drives OCR) | `D->>O` (the readers call `core.ocr`) | `_import_edges("pipeline", ("core.ocr",))` is empty; the two readers import it |
| "core may import the standard library and its own subpackages" with no exception | the row keeps the rule and carries an exceptions table of 6 files / 12 import statements | measured; pinned by name so a new one fails |
| "routes may not import the pipeline" was implied by the layer row | stated as held-for-readers, not-held-for-the-pipeline, with the file named | `Api/routes/analysis.py` imports `IntegratedFileReader` twice |

### Layers table

| row | rule | evidence | label |
|---|---|---|---|
| templates | read no database, decide no access | no Python import in any template; access decisions live in `core/security` | inspected |
| routes | may not import a reader | 0 imports of `reader_file` in `Api/` | measured |
| services | may not render markup | 0 `render_template` in `services/` | measured |
| readers | may not write to the database | 0 imports of `database` in `reader_file/readers` | measured |
| core | may not import a route or a service | 6 pinned exceptions, 12 statements | measured |

## `docs/DOMAIN_MODEL.md`

### The record

| concept | sentence | code | label |
|---|---|---|---|
| file | "one object in the collection, identified by its path and hash" | `paths.file_path`, `paths.context_id → hash_contexts.hash_id → hashs.hash` | measured (`test_a_file_is_identified_by_its_path_and_hash`) |
| logical file | "one work, however many copies of it exist (content identity)" | `hashs.hash CHAR(64) UNIQUE`; `hash_contexts` is the (hash × source × side) join | measured (same test) |
| occurrence | "one place a logical file was seen" | a `paths` row carries its own `context_id` | measured (table + FK) |
| archive | "a container read as a tree, with lineage from container to member" | `paths.parent_path_id`, `paths.hierarchy_path`; **there is no `archives` table** | measured (`test_an_archive_is_lineage_not_a_table`) |
| source / side | "where an item came from, and which party it belongs to" | `sources`, `sides`, `hash_contexts.source_id/side_id` | measured (table + FK) |
| term, keyword, category | "the vocabulary the collection is described with" | `categorys`, `keywords`, `words`, `term_names` (`m0005`) | measured for `keywords`/`categorys`; `term_names` is on `words`, not `keywords` — the document says "term", which is `words` + `term_names`, `measured` only as table existence |

### Extraction provenance

| sentence | code | label |
|---|---|---|
| "every stored item carries `extraction_provenance`" | `paths.extraction_provenance JSONB NULL` - nullable, so "every" is "every item the pipeline stored" | measured (column exists); the quantifier is **weakened in the document** to "every item the pipeline stores" |
| the OCR field list (`attempted` … `total_pages`) | `StoragePipeline._ocr_provenance` | measured, bidirectionally, by `test_ocr_provenance_docs.py` |
| "a single image read reports the flat fields; a PDF read reports the page counts as well" | same function: `pages` in → `ocr_pages`/`rotated_pages`/`total_pages` out | measured (the two branches are the two fixtures of the OCR test) |
| "a field that is absent means not measured, never measured as zero" | a convention across the pipeline | **unverified** - no test derives it |
| "an attempt that failed is stored as a failed attempt, with its error" | `confidence_error`, `ocr_blocks_error` | measured for the OCR block error (OCR test fixture); the general statement is **unverified** |

### Media

| sentence | code | label |
|---|---|---|
| "a media read that cannot transcribe speech still stores what the container says" | `read_video.py` container/stream metadata | inspected |
| "the record states that speech was not extracted" | `read_video.py` writes `speech_extracted: False` (lines 338, 387, 414) | measured (`test_a_media_read_records_that_speech_was_not_extracted`) |
| "duration, geometry, codec, stream counts and tags" | `probe_container_metadata` / `_container_metadata_fallback` | inspected (field names present); no fixture asserts all five |

## Untraceable or unverified, and what was done

| claim | action |
|---|---|
| "a field that is absent means not measured" | kept, listed in `test_architecture_claims.py::UNVERIFIED_CLAIMS` |
| "an attempt that failed is stored as a failed attempt" (general) | kept as the OCR case only; the general form is in `UNVERIFIED_CLAIMS` |
| "templates decide no access" | kept, `UNVERIFIED_CLAIMS`: asserted by absence of Python imports, not by reading every template |
| "readers write only what a container has to be unpacked into" | kept, `UNVERIFIED_CLAIMS`: the email reader is inspected, not exercised |
| "geometry, stream counts and tags" | kept, `UNVERIFIED_CLAIMS`: the field names exist, no fixture covers all five |
| "every stored item carries `extraction_provenance`" | **corrected** to "every item the pipeline stores", because the column is nullable |
| `StoragePipeline.extract` | **removed** (never existed) |
| pipeline-driven OCR | **moved** to the reader |
| core imports only the standard library | **corrected** to a rule plus 6 named, counted exceptions |

Owner: the repository owner is the reviewing owner of both documents; that is
the same owner holding the four translation ids and the decision on whether
these two authored documents stay (due 2026-11-05). Both documents now carry a
`Reviewed by:` line, and `test_each_document_names_its_reviewer` fails if it is
removed.

## What still cannot be proved from the tree

| claim | why |
|---|---|
| the diagrams render as intended | Mermaid is not executed here; the *edges* are compared with the code, the *rendering* is not |
| "the web application answers a request from the database" as a whole | the endpoints were read; no test issues a request and traces it |
