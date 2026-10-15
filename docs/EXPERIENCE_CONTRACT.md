# Experience contract

Every screen this product exposes declares what it presents: which columns and
filters it carries, what its actions do, which states it can be in, and which
help key explains it. Those declarations live in `core/experience/` and are
validated by `core/experience/validation.py`. The interface registry
(`core/interfaces/registry.py`) stays the authority for which interfaces exist;
the experience layer only adds the presentation contract on top of it, and a
contract that disagrees with the registry is reported as a problem instead of
being served.

## How the contract is served

The API is read-only:

* `GET /api/experience/contracts` - every contract, with the counts this build
  declares
* `GET /api/experience/contracts/<interface_id>` - one contract, its problems,
  and the keys that are still keyed by source
* `GET /api/experience/actions` and `/api/experience/actions/<action_id>` - the
  action surface and what each action requires
* `GET /api/experience/permissions` - the permission vocabulary the actions use

Write methods are not accepted on these paths. An unknown interface is a clear
not-found rather than an empty contract.

## Where the numbers come from

The generated block below is produced by

```
python3 -m core.experience.docgen docs/EXPERIENCE_CONTRACT.md
```

from the contract modules themselves, and a test compares the file with the
generator's output, so the counts here cannot drift from the product. The
hand-written half of this document deliberately contains no counts: they belong
in the generated block, where they are checkable.

## Reading the block

The first table lists every interface with its domain, whether its screen was
declared or derived, and how many columns, filters, actions and states it
carries. The coverage section reports how much of the language surface is
translated and which screens still lack an experience contract - that list is
the work queue for making the surface complete, and it is expected to shrink
rather than being explained away.

<!-- BEGIN GENERATED EXPERIENCE CONTRACT -->
### What this build declares

- Contracts: **34** (described: **5**, derived from the registry only: **29**)
- Definitions: **34** actions, **27** columns, **6** filters, **0** fields, **5** states
- Translation keys the screens need: **250**
- With help: **32**; with a shortcut: **18**; with a navigation entry: **34**

### Every screen

| Interface | Domain | Declared | Title key | Columns | Filters | Actions | States | Help |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dashboard` | WORK | derived | `screen.dashboard.title` | — | — | — | — | yes |
| `file_library` | DISCOVER | yes | `screen.file_library.title` | 7 | 4 | 12 | 1 | yes |
| `search` | DISCOVER | derived | `screen.search.title` | — | — | — | — | yes |
| `sources` | DISCOVER | yes | `screen.sources.title` | 8 | — | 4 | 1 | yes |
| `sides` | DISCOVER | yes | `screen.sides.title` | 5 | — | 4 | 1 | yes |
| `keywords` | DISCOVER | yes | `screen.keywords.title` | 4 | 2 | 6 | 1 | yes |
| `words` | DISCOVER | yes | `screen.words.title` | 3 | — | 7 | 1 | yes |
| `categories` | DISCOVER | derived | `screen.categories.title` | — | — | — | — | yes |
| `email_words` | DISCOVER | derived | `screen.email_words.title` | — | — | — | — | yes |
| `analyst_categorization` | CLASSIFY | derived | `screen.analyst_categorization.title` | — | — | — | — | yes |
| `notifications` | DISCOVER | derived | `screen.notifications.title` | — | — | — | — | yes |
| `signal_horizon` | DISCOVER | derived | `screen.signal_horizon.title` | — | — | — | — | yes |
| `monitoring` | DISCOVER | derived | `screen.monitoring.title` | — | — | — | — | yes |
| `input_ingestion` | INGEST | derived | `screen.input_ingestion.title` | — | — | — | — | yes |
| `import_center` | INGEST | derived | `screen.import_center.title` | — | — | — | — | yes |
| `archives` | ANALYZE | derived | `screen.archives.title` | — | — | — | — | yes |
| `path_analysis` | ANALYZE | derived | `screen.path_analysis.title` | — | — | — | — | yes |
| `map_viewer` | ANALYZE | derived | `screen.map_viewer.title` | — | — | — | — | yes |
| `batch_analysis` | ANALYZE | derived | `screen.batch_analysis.title` | — | — | — | — | yes |
| `classification` | CLASSIFY | derived | `screen.classification.title` | — | — | — | — | yes |
| `comprehensive_dashboard` | REPORT | derived | `screen.comprehensive_dashboard.title` | — | — | — | — | yes |
| `reports` | REPORT | derived | `screen.reports.title` | — | — | — | — | yes |
| `reports_dashboard` | REPORT | derived | `screen.reports_dashboard.title` | — | — | — | — | yes |
| `retention` | ADMINISTRATION | derived | `screen.retention.title` | — | — | — | — | yes |
| `schedules` | REPORT | derived | `screen.schedules.title` | — | — | — | — | yes |
| `charts_dashboard` | REPORT | derived | `screen.charts_dashboard.title` | — | — | — | — | yes |
| `detection` | OPERATE | derived | `screen.detection.title` | — | — | — | — | yes |
| `jobs` | OPERATE | derived | `screen.jobs.title` | — | — | 1 | — | yes |
| `import_export_console` | OPERATE | derived | `screen.import_export_console.title` | — | — | — | — | — |
| `users` | ADMINISTRATION | derived | `screen.users.title` | — | — | — | — | yes |
| `audit_log` | ADMINISTRATION | derived | `screen.audit_log.title` | — | — | — | — | yes |
| `settings` | SETTINGS | derived | `screen.settings.title` | — | — | — | — | yes |
| `translation_manager` | SETTINGS | derived | `screen.translation_manager.title` | — | — | — | — | yes |
| `concurrency_monitor` | INTERNAL | derived | `screen.concurrency_monitor.title` | — | — | — | — | — |

### Translation coverage, measured

Counted from the catalogs the build ships - the Babel catalogs under `translations/` and the JavaScript UI packs under `static/js/i18n/locales` - against the strings in the message template. `translated` excludes strings that are identical to the source, which are counted as `fallback`.

| Language | Catalog entries | Source strings | Translated | Fallback | Missing | Coverage | Of which translated |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ar` | 4218 | 3713 | 3619 | 18 | 76 | 98.0% | 97.5% |
| `fa` | 3991 | 3713 | 3353 | 20 | 340 | 90.8% | 90.3% |
| `he` | 3991 | 3713 | 3351 | 22 | 340 | 90.8% | 90.3% |
| `hr` | 3779 | 3713 | 3604 | 27 | 82 | 97.8% | 97.1% |

### Coverage per screen

The strings a screen's contract asks for, and how many of them a language actually translates. Looked up by semantic key first and by the English source string second, because the catalogs still key by source string today; `by key` is the part of the migration that has happened.

| Interface | Keys | ar | fa | he | hr |
| --- | --- | --- | --- | --- | --- |
| `dashboard` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `file_library` | 32 | 90.6% (0 by key) | 78.1% (0 by key) | 78.1% (0 by key) | 90.6% (0 by key) |
| `search` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `sources` | 19 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `sides` | 16 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `keywords` | 21 | 76.2% (0 by key) | 76.2% (0 by key) | 76.2% (0 by key) | 76.2% (0 by key) |
| `words` | 19 | 84.2% (0 by key) | 78.9% (0 by key) | 78.9% (0 by key) | 78.9% (0 by key) |
| `categories` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `email_words` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `analyst_categorization` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `notifications` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `signal_horizon` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `monitoring` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `input_ingestion` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `import_center` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `archives` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `path_analysis` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `map_viewer` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `batch_analysis` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `classification` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `comprehensive_dashboard` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `reports` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `reports_dashboard` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `retention` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `schedules` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `charts_dashboard` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `detection` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `jobs` | 7 | 85.7% (0 by key) | 85.7% (0 by key) | 85.7% (0 by key) | 85.7% (0 by key) |
| `import_export_console` | 3 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `users` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `audit_log` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `settings` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `translation_manager` | 5 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |
| `concurrency_monitor` | 3 | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) | 100.0% (0 by key) |

### Screens nobody has described yet

These have a contract derived from the registry, so they work: they have an identity, a navigation entry, a lifecycle and a help topic. What they do not have is a description of what they offer - columns, filters, actions, states - because nobody has decided it. The list is the remaining work, not a defect.

`dashboard`, `search`, `categories`, `email_words`, `analyst_categorization`, `notifications`, `signal_horizon`, `monitoring`, `input_ingestion`, `import_center`, `archives`, `path_analysis`, `map_viewer`, `batch_analysis`, `classification`, `comprehensive_dashboard`, `reports`, `reports_dashboard`, `retention`, `schedules`, `charts_dashboard`, `detection`, `jobs`, `import_export_console`, `users`, `audit_log`, `settings`, `translation_manager`

### Contract validation

Every contract passes the declarative checks: no SQL, no imports, no calls, no authorisation decisions, destructive actions carry a confirmation, bulk actions require a selection, and no key holds two different source strings.

_Generated from 34 contracts, 3713 source strings and 5 catalogs._
<!-- END GENERATED EXPERIENCE CONTRACT -->
