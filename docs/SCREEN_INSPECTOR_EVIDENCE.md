# Screen inspector evidence

What the Screen Inspector can answer today, measured rather than described. The
Inspector answers one question - *what is this element?* - and its worth is that
the answer is derived from the interface registry, the action registry, the
binding scan and the component library rather than inferred from what the
element looks like.

Nothing in this document is typed by hand. The block at the end is produced by

```
python3 -m core.experience.audit docs/SCREEN_INSPECTOR_EVIDENCE.md
```

and a test compares the file with the generator, so a count cannot drift.

Two things the measurement refuses to do, on purpose:

* Permission metadata is not turned into a yes/no answer. The Inspector reports
  the permission *name* an action declares and the authorization decision the
  server returned for that request, and keeps them apart: a name is not a
  decision, and there is no server-side "may this account run this action"
  answer to show yet, because authorization is decided where the operation runs.
  A field the product cannot determine reads as not determined instead of a
  guess.
* The Inspector is read-only. It explains a control and where its metadata comes
  from; it is not a configuration editor and it does not perform the action it
  describes.

Per element, per action, per component and per binding, the generated block
below says how much of that answer the product can supply today, and the gap
list that closes it names the code proving each question that cannot be answered
honestly yet - so a solved question disappears from the list instead of
lingering.

<!-- BEGIN GENERATED: experience audit -->
## What the product can say about an element

Measured from the interface registry, the action registry, the binding
scan and the component library. Nothing on this page was typed by hand:
`python3 -m core.experience.audit` writes it, and the test compares the
document with what it writes.

| Measurement | Count |
| --- | --- |
| Interfaces | 34 |
| Navigable interfaces | 33 |
| Interfaces with a described screen | 5 |
| Interfaces declaring no help topic | 2 |
| Interfaces declaring no keyboard shortcut | 16 |
| Registered actions | 34 |
| Actions bound to a control | 6 |
| Presented actions nothing binds | 28 |
| Actions declared and not built | 1 |
| Actions named in markup and never registered | 0 |
| Actions no described screen presents | 1 |
| Declared components | 22 |
| Components an element cannot resolve to | 0 |
| Classes rendered in the product | 424 |
| Classes the project owns | 165 |
| Classes that are third-party | 259 |
| Classes belonging to nobody | 0 |
| Bindings the scan found | 13 |

### How far each action's binding reaches

| Status | Actions |
| --- | --- |
| bound to a control | 5 |
| declared, not built | 1 |
| presented, nothing binds it | 28 |

`bound to a control` means the product names the action where a control
comes from - a shared component, a page script, or the Python that
prepares the surface. Everything else is an action a reader can meet that
the architecture cannot yet account for, and each one is listed below
with the evidence.

### The actions the product cannot account for

| Action | Status | Where | Shared surface it uses |
| --- | --- | --- | --- |
| `files.reprocess` | declared, not built | Api/blueprints/files.py:125 | the shared record action surface |
| `files.analyze_selected` | presented, nothing binds it | file_library | the shared record action surface |
| `files.delete_selected` | presented, nothing binds it | file_library | the shared record action surface |
| `files.export_selected` | presented, nothing binds it | file_library | the shared record action surface |
| `files.open_record` | presented, nothing binds it | file_library | the shared record action surface |
| `files.select_all` | presented, nothing binds it | file_library | the shared record action surface |
| `files.select_none` | presented, nothing binds it | file_library | the shared record action surface |
| `files.upload` | presented, nothing binds it | file_library | the shared record action surface |
| `keywords.delete_selected` | presented, nothing binds it | keywords | the shared action toolbar |
| `keywords.edit_selected` | presented, nothing binds it | keywords | the shared action toolbar |
| `keywords.merge_duplicates` | presented, nothing binds it | keywords | the shared action toolbar |
| `keywords.select_all` | presented, nothing binds it | keywords | the shared action toolbar |
| `keywords.select_none` | presented, nothing binds it | keywords | the shared action toolbar |
| `keywords.update` | presented, nothing binds it | keywords | the shared action toolbar |
| `sides.edit_selected` | presented, nothing binds it | sides | the shared action toolbar |
| `sides.export_selected` | presented, nothing binds it | sides | the shared action toolbar |
| `sides.select_all` | presented, nothing binds it | sides | the shared action toolbar |
| `sides.select_none` | presented, nothing binds it | sides | the shared action toolbar |
| `sources.edit_selected` | presented, nothing binds it | sources | the shared action toolbar |
| `sources.export_selected` | presented, nothing binds it | sources | the shared action toolbar |
| `sources.select_all` | presented, nothing binds it | sources | the shared action toolbar |
| `sources.select_none` | presented, nothing binds it | sources | the shared action toolbar |
| `words.delete` | presented, nothing binds it | words | the shared action toolbar |
| `words.delete_selected` | presented, nothing binds it | words | the shared action toolbar |
| `words.edit` | presented, nothing binds it | words | the shared action toolbar |
| `words.edit_selected` | presented, nothing binds it | words | the shared action toolbar |
| `words.open` | presented, nothing binds it | words | the shared action toolbar |
| `words.select_all` | presented, nothing binds it | words | the shared action toolbar |
| `words.select_none` | presented, nothing binds it | words | the shared action toolbar |

### Interfaces the Inspector describes

| Interface | Domain | Route | Help topic | Shortcut | Actions |
| --- | --- | --- | --- | --- | --- |
| `dashboard` | WORK | `index` | work/dashboard | g w | 0 |
| `file_library` | DISCOVER | `files.files_list` | discover/file-library | g f | 12 |
| `search` | DISCOVER | `search_page` | discover/search | g s | 0 |
| `sources` | DISCOVER | `sources_list` | discover/sources | Not declared | 4 |
| `sides` | DISCOVER | `sides_list` | discover/sides | Not declared | 4 |
| `keywords` | DISCOVER | `keywords_list` | discover/keywords | Not declared | 6 |
| `words` | DISCOVER | `words_list` | discover/words | Not declared | 7 |
| `categories` | DISCOVER | `categories_list` | discover/categories | Not declared | 0 |
| `email_words` | DISCOVER | `email_words` | discover/email-words | Not declared | 0 |
| `analyst_categorization` | CLASSIFY | `analyst_categorization_page` | classify/analyst-categories | Not declared | 0 |
| `notifications` | DISCOVER | `notifications_page` | discover/notifications | g n | 0 |
| `signal_horizon` | DISCOVER | `signals_page` | discover/signals | g h | 0 |
| `monitoring` | DISCOVER | `monitoring_page` | discover/monitoring | g m | 0 |
| `input_ingestion` | INGEST | `operations_input_page` | ingest/input | g i | 0 |
| `import_center` | INGEST | `operations_import_page` | ingest/import-center | Not declared | 0 |
| `archives` | ANALYZE | `archives_page` | analyze/archives | g a | 0 |
| `path_analysis` | ANALYZE | `path_analysis_page` | analyze/path-analysis | g p | 0 |
| `map_viewer` | ANALYZE | `map_viewer_page` | analyze/map-viewer | g g | 0 |
| `batch_analysis` | ANALYZE | `analysis_batch` | analyze/batch | g b | 0 |
| `classification` | CLASSIFY | `file_classification_page` | classify/classification | Not declared | 0 |
| `comprehensive_dashboard` | REPORT | `comprehensive_dashboard` | report/detailed-dashboard | Not declared | 0 |
| `reports` | REPORT | `reports_page` | report/reports | g r | 0 |
| `reports_dashboard` | REPORT | `reports_dashboard_page` | report/dashboard | Not declared | 0 |
| `retention` | ADMINISTRATION | `retention_page` | operate/retention | Not declared | 0 |
| `schedules` | REPORT | `schedules_page` | report/schedules | Not declared | 0 |
| `charts_dashboard` | REPORT | `charts_dashboard` | report/charts | Not declared | 0 |
| `detection` | OPERATE | `detection_page` | operate/detection | g d | 0 |
| `jobs` | OPERATE | `operations_jobs_page` | operate/jobs | g j | 0 |
| `import_export_console` | OPERATE | `import_export_page` | Not declared | Not declared | 0 |
| `users` | ADMINISTRATION | `users_page` | administration/users | g u | 0 |
| `audit_log` | ADMINISTRATION | `audit_page` | administration/audit | g l | 0 |
| `settings` | SETTINGS | `settings_page_direct` | settings/overview | g , | 0 |
| `translation_manager` | SETTINGS | `translations.translation_management_page` | settings/translations | g t | 0 |
| `concurrency_monitor` | INTERNAL | `concurrency.dashboard` | Not declared | Not declared | 0 |

### Fields, and how many actions declare them

| Field | Declared | Of |
| --- | --- | --- |
| action | 34 | 34 |
| binding | 6 | 34 |
| component | 22 | 22 |
| execution | 29 | 34 |
| help | 32 | 34 |
| interface | 34 | 34 |
| permission | 34 | 34 |
| scope | 34 | 34 |
| state | 34 | 34 |
| translation | 34 | 34 |

A field nobody declares is not a defect in the Inspector: it is why the
panel says *Not declared*, and the number is here so filling the metadata
in is visible progress rather than a matter of opinion.

### The questions the Inspector cannot answer yet

**Actions with no operation: `execution` is empty and no job exists** — The registry can say 'declared, not built' and the surface honours it - the button is hidden, nothing is drawn, and no route is bound - but four actions (`files.reprocess`, `sources.export_selected`, `sources.edit_selected`, and the bulk export and edit of the same family) have no operation to name, so the Inspector can only report the absence. Building one means giving it a persistent job and a path policy first, which the action vocabulary has no room for.

Evidence: `core/experience/action_registry.py`, `Api/blueprints/files.py`, `pipeline/storage_pipeline.py`

**An action's help topic and shortcut** — Every interface declares a help topic and five of six navigable screens declare no keyboard shortcut, and an action declares neither. The Inspector therefore shows the screen's help and nothing for the action's own, rather than borrowing one: a help topic is a promise that a page answers that question, and the action vocabulary has no field for it.

Evidence: `core/interfaces/registry.py`, `core/experience/inspector.py`

**What a control is bound to, when it is wired by a page function** — The frozen toolbar renders buttons that call a page function by name (`data-sequence-action`), not from the registry, so for most actions the only honest answer is 'hand-written button, not registry-bound'. The Inspector cannot trace a click to its operation for those screens until each screen renders its toolbar from the registry, which the freeze defers on purpose.

Evidence: `templates/components/action_toolbar.html`, `static/js/pages/keywords-list-page.js`, `static/js/pages/sources-list-page.js`

**Whether the reader is permitted to run the action** — The Inspector reports the permission *name* the action declares and the authorization decision the server gave for that request, and keeps them apart on purpose: a name is not a decision, and a browser must never be shown one as a boolean. There is no server-side 'may this account run this action' answer to show yet, because authorization today is decided where the operation runs - so the field reads 'Not determined' rather than a guess.

Evidence: `core/experience/inspector.py`, `core/security/flask_ext.py`
<!-- END GENERATED: experience audit -->
