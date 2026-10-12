# Productization Map

What "productized" means for this codebase, what is finished, and what is
knowingly left as legacy. It is a map, not a ledger: the numbers live in the
generated sources it points at, because a count typed into a document goes
stale silently - an earlier revision of this file carried three different
endpoint counts (57, 40 and 41) for the same application.

| Question | Answered by |
| --- | --- |
| What does the product offer, and who owns each page? | `core/interfaces/registry.py`, rendered in `docs/INTERFACE_REGISTRY.md` |
| Does the running application match it? | `docs/REGISTRY_EVIDENCE.md` (generated from a live app) |
| Which routes exist, and how is each classified? | `docs/endpoint_inventory.json` (generated from the URL map) |
| What does each interface promise the reader? | `core/experience/contracts.py`, rendered in `docs/EXPERIENCE_CONTRACT.md` |
| Which components exist, and which templates still hand-roll them? | `core/frontend/component_audit.py`, rendered in `docs/COMPONENT_LIBRARY.md` |
| Which actions exist, and what governs each? | `core/experience/action_registry.py`, rendered in `docs/ACTION_SURFACE_AUDIT.md` |

## Finished

* **Interface registry.** Every user-facing page is declared once, with its
  domain, role, default state, dependencies, help topic and shortcuts. The
  registry is checked against a live application: a page that is served but not
  declared, or declared but not served, fails the integration suite.
* **Endpoint inventory.** Every route the application serves is classified and
  attributed to an owner, generated deterministically so a new page shows up as
  a readable diff.
* **Navigation.** The sidebar, the command palette and the interface pickers
  render from the registry rather than from a hand-written list.
* **Experience contract.** Columns, filters, actions, states and help for each
  interface are declared, with the declarative checks (no SQL, no imports, no
  authorisation decisions inside a contract) enforced by tests.
* **Action surface.** Every action a user can trigger is registered with its
  kind, its confirmation requirement and its permission, and the audit checks
  the rendered toolbars against the registry.
* **Translation plumbing.** Four catalogs (Arabic, Hebrew, Persian and - kept
  maintained but not selectable - Croatian) plus the client packs, with the
  server catalog winning where both carry a string, and a test that pins the
  two together.
* **Search performance work.** The indexed-vocabulary short circuit, the
  literal-path decisions and the `OR`-fanout regression are documented with
  their measurements in `docs/search/` and `docs/perf/`.

## Legacy, deliberately kept

* `INTERFACE_METADATA` and `LEGACY_INTERFACE_IDS` in
  `core/interfaces/registry.py` still describe settings keys and interface IDs
  from earlier revisions. They are read so a settings file written by an older
  version keeps working, and they are reported in `docs/REGISTRY_EVIDENCE.md`
  so nobody mistakes them for the current vocabulary.
* Retired interfaces are marked `DEPRECATED` rather than deleted: the page is
  still served for anyone who has it bookmarked, but it is no longer offered in
  navigation.
* The `test-doc/` corpus is a fixture for the extraction tests, not
  documentation and not part of the product.
* The performance slices under `docs/perf/slices/` record investigations that
  ended either in a change or in a decision not to change; they are kept as
  evidence, not as instructions.

## Open work

The work tracker (`docs/project/SYLTHARAE_work_tracker.xlsx`) is the live list.
At the time of writing the open items are: wiring the export-surface smoke into
continuous integration, running the full table-export and database suites
there, and a manual browser regression pass over the export menu, map
soft-navigation and the right-to-left languages. Nothing in this document
substitutes for it.
