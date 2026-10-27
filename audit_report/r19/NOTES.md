# Round 19 — two reported defects

Branch `arena/d19d9293-syltharae-pro`, commits `031b145` (Bug A), `ccc27ea`
(Bug B), `d6f5ad5` (audit tooling + probe sweeps), `67ab01c` (round-18 record).

Every number below was produced in this session by the artefact named next to
it. The `junit_*.xml` files are the raw runs; `suite_summary.csv` is generated
from them by `tools/audit/suite_summary.py`.

## Bug A — `/signals` IP preset rejected by the API

| what | artefact | result |
| --- | --- | --- |
| browser, before | `bug_a_browser_before.json` | `GET /api/signals?identifier_kind=ipv4%2Cipv6&…` → **400**, `identifier_kind must be one of: email, phone, ipv4, ipv6, url (got 'ipv4,ipv6')`, banner shows it |
| browser, after | `bug_a_browser_after.json` | `identifier_kind=ipv4&identifier_kind=ipv6&…` → **200**, twice |
| API matrix, after | measured with `requests` against the dev stack | `ipv4,ipv6` 200 · `ipv4` 200 · `ipv4,ipv4` 200 · `ipv4,,ipv6` 200 · `ipv4,fax` **400**, names `fax` |
| tests | `tests/unit/test_identifier_kind_csv.py` | 11 tests, passing |

The hidden field `#fIdentifierKind` still holds the joined string; the page
splits it into repeated parameters in `filterParams()`. The server-side change
(`services/detection/signal_query.py`, `split_commas`) means a client that
sends the joined value keeps working.

## Bug B — `POST /api/places` → 500 on a missing revision

| what | artefact | result |
| --- | --- | --- |
| browser, before | `bug_b_browser_before.json` | Settings → Places → Add → Save: **500** `{"correlation_id":"ERR-20261027-000001","error":"An internal error occurred"}`, modal shows it |
| failing tests first | `tests/integration/test_places_missing_revision.py` | **4 failed / 3 passed**, `TypeError: 'NoneType' object is not subscriptable` at `places.py:400` and `places.py:674` |
| browser, after | `bug_b_browser_after.json` | **503** `GAZETTEER_UNAVAILABLE`, `the gazetteer has no category for feature_type 'city'; load the gazetteer seed before adding places` |
| tests, after | same file | **7 passed** |
| related tests | `pytest tests -k "places or gazetteer or place_name"` | 44 tests, 0 failures, 2 skipped |

Root cause: `do_create()` returned `(None, "category not found", None)` for a
feature type with no row in `categorys` — the state of a database whose
gazetteer seed was never applied — and the route only special-cased
`error == "conflict"`, so the third value reached `revision["fingerprint"]`.

### Partial write: what was measured

In the reproduced scenario **no place row exists after the 500** — the category
lookup returns before the `INSERT`, so the transaction had nothing to commit.
Verified by querying the dev-stack database after two identical failing
submissions (`geo_places` count 0, and `categorys` count 0).

The crash did sit *after* `_write()` had committed, so a missing revision on a
path that had already inserted would have committed and then answered 500, with
a retry answering 409. That is why the fix has two halves: the 503 for the
missing precondition, and the null-safe `_revision_payload()` for every
response line that reads a revision (create, update, delete, place-name
create/update/delete).

## Re-run at this HEAD

| sweep | rows | findings |
| --- | --- | --- |
| malformed bodies (`tools/audit/probe_malformed.py`) | 3,030 | 0 |
| hostile query strings (`tools/audit/probe_query_params.py`) | 6,560 | 0 |
| parameterised routes (`tools/audit/probe_param_routes.py`) | 680 | 0 (9 declared 501s, 65 NO-FIXTURE = not tested) |

Their CSV output is committed at `audit_report/findings/{malformed_bodies,
query_params,param_routes}.csv`.

## Two-part suite (this environment, fresh database)

| part | tests | failures | errors | skipped |
| --- | --- | --- | --- | --- |
| unit (`junit_unit.xml`) | 3,493 | 31 | 11 | 11 |
| integration (`junit_integration.xml`) | 1,198 | 7 | 0 | 29 |

Failure groups, generated (`suite_summary.csv`, `*_failing_ids.txt`):

* **generated-document drift** — `test_interface_docs` (13),
  `test_component_library` (4), `test_experience_contract` (2),
  `test_action_lifecycle_components` (2), `test_action_surface_audit` (2),
  `test_screen_inspector` (2), `test_architecture_diagrams` (2),
  `test_content_vs_identity` (2), `test_ocr_provenance_docs` (2),
  `test_reference_docs` (1), `test_interface_lifecycle` (2),
  `test_interface_coverage` (1). **NEEDS-DECISION** — no document is written
  just to satisfy a test.
* **frozen translation catalogs** — `test_translation_coverage[ar|he|fa|hr]`
  (4). Schema-freeze rule: no catalog entries are machine-translated.
* **licence metadata of optional packages** — `test_licensing` (2),
  `pymupdf-layout` / `pymupdf4llm` report no licence. Environment/dependency
  question, not code.
* **this sandbox's checkout path** — `test_no_machine_paths` (2): the path
  `/home/user/SYLTHARAE-Pro` appears in `audit_report/r14/*` artefacts, which
  are records of earlier runs and are not rewritten. Environment artefact.
* **reader core, open** — `test_cell_locations_and_recipients` (2):
  `Sheet1 - B3` reported where `B4` is expected, and a row the oracle expects
  to be empty is not. **DEFECT-OPEN**, pre-existing, unrelated to the files
  changed here.
* **misc** — `test_identifiers_intel` (2, expects `email` where `identifier`
  is produced), `test_install_cli_config` (1), `test_windows_offline_kit` (1).

The skipped count (40 in total) is far below the round-17 baseline (1,535)
because this environment now has the optional readers installed (`rarfile`,
`oletools`, `extract-msg`, `py7zr`, `ebooklib`, `mobi`, `RTFDE`, …): tests that
used to skip here now run. The failure count is therefore **not** comparable to
the round-17 record without that qualifier — 5,020 tests were reported then,
4,691 run here.

## Not measured

* The 100k-row pagination and `EXPLAIN` checks were not re-run this round (no
  change to the query paths of `places`); the round-12 numbers stand.
* No clean-clone reproduction of the suite: the run above is on this working
  tree at `67ab01c`'s parent, before the record commits.
* The `test_identifiers_intel` pair was not triaged to a conclusion; it is
  recorded as failing, not as understood.
