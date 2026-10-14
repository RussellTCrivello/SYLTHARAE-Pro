# Component Library

The shared vocabulary of screens: which components exist, what each one
implements, which states it can be in, and which classes it renders. The number
that matters is not the size of the library but how much markup the templates
still hand-roll. "Nine templates still write their own table markup" is a change
somebody can review; "we introduced shared components" is not. The generated
block at the end of this document holds the current count for every pattern -
nine is the table count today - and the audit is what produces it, so the number
is checkable rather than remembered.

## What a component declares

Each file in `templates/components` starts with a `{# component: ... #}`
declaration: the name, what it is for, the states it implements and the classes
it owns. The audit reads those declarations rather than a list maintained
elsewhere, so a component cannot exist without stating what it is.

The states a component answers for are fixed (`core/frontend/component_audit.py`,
`STATES`): loading, empty, error, disabled, success, partial and stale. A
component implements the states that apply to it; every state must be
implemented by *something*, or the state does not exist in the product and the
guardrail fails. A state this project still owes is listed as **not yet**, with
the component that will own it - never implied as covered.

## Presentation only

The rule the components are held to is **Presentation only**: a component
renders what it is given. It does not query the database, it does not decide
who may see something, and it does not decide which state is true - the page
does that and passes the answer in. That boundary is tested, not promised: a
component that reaches past its inputs for a query or an authorization decision
fails, and the error state a component can render is checked for internals
(a stack trace, a path, a query) that must never reach a reader.

The same rule applies to the migration itself: moving a page onto a component
is **not a redesign**. The markup changes shape, the behaviour does not - the
page keeps its own selection logic, its own calls and its own outcome.

## Which classes may be used

Three answers, and only three:

* **OWNED** - styled by a stylesheet this project maintains (`static/css`).
  This is the product's own vocabulary.
* **THIRD_PARTY** - defined by a bundled dependency (Bootstrap, Bootstrap
  Icons). Using one is a decision to depend on it, not a decision of our own.
* **UNKNOWN** - nobody styles it. This is the failure the audit exists for: a
  class that looks meaningful and does nothing, or a typo that silently removes
  styling.

A component may also *declare* a class it intentionally does not style, because
scripts hook behaviour onto it. Those are reported separately, as a decision
somebody made on purpose.

## How this document is generated

The block below is produced by `core/frontend/component_audit.py` and compared
with the templates by `tests/unit/test_component_library.py`. Regenerate:

```
python3 -m core.frontend.component_audit docs/COMPONENT_LIBRARY.md
```

The prose carries no counts on purpose - a number typed here goes stale, and
the generated block is where the numbers live. Components are consumed by the
screens described in `docs/SCREEN_INSPECTOR_EVIDENCE.md`, and the actions they
carry are audited in `docs/ACTION_SURFACE_AUDIT.md`.

<!-- BEGIN GENERATED COMPONENT AUDIT -->

### Components

Read from the `{# component: … #}` declaration at the top of each file in `templates/components/`. A file without one has no declared purpose or states, and is listed as such.

| Component | File | States | Macros | Purpose |
| --- | --- | --- | --- | --- |
| `action_toolbar` | `templates/components/action_toolbar.html` | `selected`, `loading` | `action_toolbar`, `action_group`, `select_toggle_button`, `action_button`, `bulk_action_button`, `selection_summary` | The bar of actions on a list: the groups, the buttons, and the one state the server can know for certain - nothing is selected yet. |
| `analyst_classify` | `templates/components/analyst_classify.html` | `normal`, `editing`, `saving`, `success`, `error`, `unauthorized` | `analyst_classify` | The analyst-category control for the record being read, usable from wherever that record is displayed. |
| `breadcrumbs` | `templates/components/breadcrumbs.html` | `normal` | `breadcrumbs` | Where the reader is, rendered from the interface registry: a page says what it is about, the registry supplies the words and icons. |
| `confirm_dialog` | `templates/components/confirm_dialog.html` | `normal`, `saving`, `error`, `unauthorized` | `confirm_dialog` | One way to ask "are you sure?" before something irreversible. The component renders the question; it never performs the operation and never knows what the operation is. The page decides - and it says which action it is asking about, by id, so the dialog and the action registry agree on what is happening. |
| `documents_panel` | `templates/components/documents_panel.html` | `normal`, `loading`, `empty` | `documents_panel` | The side panel of one owner's documents - a file type, a keyword, a category. One markup for every host page; the body is the shared file-library table fragment, adopted in place by static/js/modules/ui/documents-panel.js. Openers anywhere on the page declare data-panel-open + data-panel-url. |
| `file_library_table` | `templates/components/file_library_table.html` | `normal`, `empty`, `filtered` | `file_library_table` | The File Library's table - the one rendering of the library's rows, shared by the File Library page and by the documents panels (a file type's, a keyword's, a category's documents). Ten columns, sortable headers, the Type/Size/Date column filters, Load More, the per-row action menu, selection. |
| `file_nav` | `templates/components/file_nav.html` | `normal`, `empty` | `file_nav`, `file_nav_dock` | Previous/next through the records the reader is working through, and where this one sits in that set. |
| `filter_bar` | `templates/components/filter_bar.html` | `normal`, `filtered`, `empty` | `filter_section`, `filter_grid`, `filter_bar`, `filter_group`, `search_group`, `hidden_filter` | The controls above a list that decide which records it shows: a search box and the filters that narrow it, in the arrangement fifteen pages currently rebuild by hand. |
| `operations_widget` | `templates/components/operations_widget.html` | `normal`, `loading`, `empty`, `error` | — | What the ingestion and processing system is doing right now: active jobs, throughput, and the shortcuts into Operations. |
| `page_data` | `templates/components/analyst_classify_page_data.html` | `normal` | `analyst_classify_page_data` | The translated strings and the write permission the analyst classification module needs, so nothing is hard-coded in JavaScript and a language switch reaches it. |
| `page_tips` | `templates/components/page_tips.html` | `normal`, `empty` | `page_tips` | The explanatory tips at the top of a page: what this page is for, what the elements on it do, how to add data here. |
| `pagination` | `templates/components/unified_pagination.html` | `normal`, `filtered` | `load_more_control`, `unified_pagination` | Moving through a long list: where you are, how much there is, and how to get to a page you know the number of. |
| `pagination_cursor` | `templates/components/cursor_pagination.html` | `normal`, `filtered` | `cursor_pagination` | Moving through a list that has no page numbers - only "next" and "back" - and saying honestly what is known about how much is left. |
| `record_actions` | `templates/components/record_actions.html` | `normal`, `loading`, `success`, `error`, `unauthorized` | `record_action_button`, `record_action_surface` | The actions a single record offers. The buttons come from the Action Definition layer - id, label, icon, scope, destructiveness, confirmation key - joined with the screen's own bindings by core/experience/presentation.py, so a page cannot invent an action and two pages cannot render one action two ways. |
| `record_header` | `templates/components/record_header.html` | `normal`, `empty`, `loading`, `unavailable`, `archived` | `record_header` | The top of a record: what this record is, what state it is in, and the one action that matters most. The same header for a file, a source, a side, a category, an analysis or a report - it knows nothing about what kind of record it is describing. |
| `screen_inspector` | `templates/components/screen_inspector.html` | `normal`, `loading`, `empty`, `error`, `unavailable` | `inspector_field`, `screen_inspector` | The panel that answers what an element on this screen is: which interface owns it, which component renders it, which action it presents, what scope and permission metadata that action declares, where it is bound, and what it currently is. A diagnostic tool for a developer or an operator, not a configuration editor. |
| `search_input` | `templates/components/search_input.html` | `normal`, `loading`, `filtered`, `unavailable` | `search_input` | The one search box: label, icon, placeholder, value, clear action, a place for the loading state, and the ARIA that makes it a search box rather than an empty text field. |
| `sidebar_nav` | `templates/components/sidebar_nav.html` | `normal`, `empty` | — | The product navigation, grouped by domain, rendered from the navigation model the application prepares. |
| `states` | `templates/components/states.html` | `loading`, `empty`, `filtered`, `success`, `warning`, `error`, `unauthorized`, `unavailable`, `archived` | `state_panel`, `empty_state`, `filtered_state`, `loading_state`, `success_state`, `warning_state`, `error_state`, `unauthorized_state`, `unavailable_state`, `archived_state` | The states a region can be in, in one place, so a page never invents its own wording for "nothing here yet" or its own markup for "this failed". |
| `status_badge` | `templates/components/status_badge.html` | `success`, `warning`, `error`, `unavailable`, `archived` | `status_badge`, `_chip`, `status_badge_with_icon` | One way to show a status word, so the same state is not green on one page and grey on the next. An application status is looked up in the vocabulary - `core/frontend/status_vocabulary.py` - which maps it to one of a few presentation states; the component only turns that state into classes. |
| `table` | `templates/components/table.html` | `normal`, `empty`, `filtered`, `selected`, `loading`, `error` | `data_table`, `table_empty_row`, `table_loading_row`, `table_error_row`, `select_all_checkbox`, `export_menu`, `column_filter`, `columns_menu`, `sort_header`, `record_table` | The frame a list of records is read in, and the rows that stand in for a list that is empty, still loading or failed. Ten tables in this application were written with ten different class combinations; this is the one they become. `record_table` is the complete unit - toolbar, sortable headers, body, states - that every list interface renders through; `data_table` is the bare frame the older pages still call. |
| `toast` | `templates/components/toast.html` | `success`, `warning`, `error`, `loading`, `unavailable` | `toast_region` | One place where the application tells the reader that something happened. Every action ends visibly - success, information, warning, failure - and every message passes through here, so no page invents its own notification and no failure goes silent. |

### States (§63)

Every state in the vocabulary is answered by at least one component; a state nobody implements does not exist in the product, however often it is referred to.

| State | Meaning | Implemented by |
| --- | --- | --- |
| `loading` | Work is in progress; the reader is told what is being waited for. | `action_toolbar`, `documents_panel`, `operations_widget`, `record_actions`, `record_header`, `screen_inspector`, `search_input`, `states`, `table`, `toast` |
| `empty` | Nothing exists here yet, and the reader is told how to start. | `documents_panel`, `file_library_table`, `file_nav`, `filter_bar`, `operations_widget`, `page_tips`, `record_header`, `screen_inspector`, `sidebar_nav`, `states`, `table` |
| `normal` | The ordinary case: content is present and usable. | `analyst_classify`, `page_data`, `breadcrumbs`, `confirm_dialog`, `pagination_cursor`, `documents_panel`, `file_library_table`, `file_nav`, `filter_bar`, `operations_widget`, `page_tips`, `record_actions`, `record_header`, `screen_inspector`, `search_input`, `sidebar_nav`, `table`, `pagination` |
| `filtered` | Something exists, but not under the filters applied. | `pagination_cursor`, `file_library_table`, `filter_bar`, `search_input`, `states`, `table`, `pagination` |
| `selected` | A row or record is chosen; actions that need a choice appear. | `action_toolbar`, `table` |
| `editing` | A value is being changed, and the change is not saved yet. | `analyst_classify` |
| `saving` | A change is on its way to the server. | `analyst_classify`, `confirm_dialog` |
| `success` | The last action worked. | `analyst_classify`, `record_actions`, `states`, `status_badge`, `toast` |
| `warning` | Something needs attention but is not broken. | `states`, `status_badge`, `toast` |
| `error` | Something failed, with a next step rather than a stack trace. | `analyst_classify`, `confirm_dialog`, `operations_widget`, `record_actions`, `screen_inspector`, `states`, `status_badge`, `table`, `toast` |
| `unauthorized` | The server refused this for this account. | `analyst_classify`, `confirm_dialog`, `record_actions`, `states` |
| `unavailable` | It needs something this installation does not have. | `record_header`, `screen_inspector`, `search_input`, `states`, `status_badge`, `toast` |
| `archived` | Kept and readable, but out of the working set. | `record_header`, `states`, `status_badge` |

### Markup pages still write by hand

Counted by scanning `templates/**`. These are the places a shared component has not reached yet - the number goes down as components are adopted, and it is the measure of this phase rather than an impression of it.

| Markup | Component that replaces it | Templates |
| --- | --- | --- |
| Hand-written empty state | `states` | 3 templates |
| Hand-written loading indicator | `states` | 9 templates |
| Hand-written inline error | `states` | 10 templates |
| Hand-written table | `table` | 9 templates |
| Hand-written pagination markup | `pagination` | 0 templates |
| Pagination mount (filled by the shared renderer) | `pagination` | 8 templates |
| Hand-written search input | `search_input` | 10 templates |
| Hand-written filter control | `filter_bar` | 7 templates |
| Browser confirm() dialog | `confirm_dialog` | 0 templates |
| Hand-written status badge | `status_badge` | 0 badges, in 0 templates |
| Hand-written badge chip (count, id, method) | — | 32 badges |
| Hand-written action bar | `action_toolbar` | 2 templates |

### Adoption

How much of the repeated markup has moved onto its component. Standardized counts the templates that read through the component; hand-written counts what is still done by hand; the rate is the completion criterion for this phase, not an impression of it.

| Markup | Standardized | Hand-written | Adoption |
| --- | --- | --- | --- |
| Hand-written empty state | 5 | 3 | 62% |
| Hand-written table | 17 | 9 | 65% |
| Hand-written pagination markup | 11 | 0 | 100% |
| Hand-written search input | 8 | 10 | 44% |
| Hand-written filter control | 7 | 7 | 50% |
| Browser confirm() dialog | 3 | 0 | 100% |
| Hand-written status badge | 6 | 0 | 100% |
| Hand-written action bar | 5 | 2 | 71% |

**Declared exceptions.** Not everything that looks similar is the same thing, and overloaded components stop being usable. An exception is a decision with an owner:

| Area | Reason | Owner |
| --- | --- | --- |
| analysis relationship matrix | A matrix of relationships between records is not a list of records: its rows and columns are both entities, and its cells are computed pairs. Forcing it into the table component would give the component a second meaning. | analysis workspace |

### CSS ownership of the classes components render

Every class a component renders has exactly one owner. **OWNED** means an SYLTHARAE stylesheet defines it, or the component declares it in its own `classes:` header. **THIRD_PARTY** means a bundled dependency defines it - Bootstrap and Bootstrap Icons are expected dependencies, and using them is not a finding. **UNKNOWN** means nobody does, and an unknown class is how a component invents a style: it fails the guardrail test rather than being reported and forgotten.

| Ownership | Classes |
| --- | --- |
| OWNED (SYLTHARAE) | 164 |
| THIRD_PARTY (Bootstrap, Bootstrap Icons) | 259 |
| UNKNOWN | 0 |

Third-party stylesheets bundled with the application: `static/css/bootstrap.min.css`, `static/icons/bootstrap-icons.css`.

Owned by declaration rather than by a stylesheet - the component states these are its own hooks, and no rule styles them (which is a decision, not an accident):

* `select-toggle-icon` (action_toolbar.html)
* `select-toggle-label` (action_toolbar.html)
* `cursor-pagination-container` (cursor_pagination.html)
* `documents-panel` (documents_panel.html)
* `file-checkbox` (file_library_table.html)
* `ut-row-check` (file_library_table.html)
* `search-input-spinner` (search_input.html)
* `ut-body` (table.html)
* `ut-check-all` (table.html)
* `ut-columns` (table.html)
* `ut-columns-btn` (table.html)
* `ut-columns-check` (table.html)
* `ut-export-scope-check` (table.html)
* `ut-filter-check` (table.html)
* `ut-head` (table.html)

<!-- END GENERATED COMPONENT AUDIT -->
