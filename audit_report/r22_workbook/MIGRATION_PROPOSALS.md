# Two migration proposals — written, **not applied**

Round 22 asked for the DDL that two decisions would need, with the downgrade, the
tests that must change with it, and what the user gains. **Nothing here has been
applied.** `database/migrations/` is untouched by this round: the freeze gate is
`git diff HEAD -- database/migrations`, and it is empty at the commit that
carries this file.

The counts below come from generated artefacts, not from prose:

* per-category membership loss — `audit_report/r22_workbook/SHARED_PHRASES.md`
  (314 shared phrases, 647 memberships, **333 not stored**, all 314 phrases
  decided in `_Keyword Owners`);
* the schedule vocabulary — `audit_report/r22_workbook/FIRST_BOOT_MATRIX.md` and
  `tests/integration/test_scheduler_wiring.py::test_the_database_and_the_vocabulary_agree_on_what_may_be_scheduled`,
  which reads the constraint out of the catalogue rather than trusting the code.

---

## Proposal A — per-category keyword uniqueness

### What is wrong today

```sql
CREATE TABLE keywords (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    keyword BYTEA UNIQUE NOT NULL,          -- one phrase, one category, globally
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categorys(id) ...
);
```

`keyword` is the packed list of word ids, and it is `UNIQUE` on its own. So a
phrase that 314 worksheets legitimately share can be stored exactly once, and
333 memberships in the committed workbook have nowhere to go. The workbook is
authoritative, and on this point the database cannot follow it.

### The change

```sql
-- m0006_keyword_uniqueness.py  (PROPOSED — DO NOT APPLY WITHOUT AUTHORISATION)
UP = [
    "ALTER TABLE keywords DROP CONSTRAINT IF EXISTS keywords_keyword_key",
    "ALTER TABLE keywords ADD CONSTRAINT keywords_keyword_category_key"
    " UNIQUE (keyword, category_id)",
]
DOWN = [
    "ALTER TABLE keywords DROP CONSTRAINT IF EXISTS keywords_keyword_category_key",
    # Cannot be restored if a phrase now sits in two categories: the data the
    # new constraint made legal is exactly what the old one forbids. The
    # downgrade therefore refuses rather than deleting:
    #   SELECT keyword, count(*) FROM keywords GROUP BY keyword
    #    HAVING count(*) > 1 LIMIT 5;
    "ALTER TABLE keywords ADD CONSTRAINT keywords_keyword_key UNIQUE (keyword)",
]
```

### What must change in the same commit

| thing | why |
|---|---|
| `services/importing/taxonomy_sync.py::build_plan` — `not_stored` list | it exists to explain the constraint; with per-category uniqueness every membership is stored and the list becomes empty |
| `apps/importing/validators/workbook_rules.py` — `KEYWORD_SHARED` decision violation and `owner_of` | the owners sheet stops being a workaround and becomes a duplicate-cleanup hint; the violation severity changes from "decision" to "informational" |
| `services/importing/taxonomy_sync.py::apply_plan` — the `ON CONFLICT DO NOTHING` on phrase insert | must become `ON CONFLICT (keyword, category_id) DO NOTHING` |
| `tests/integration/test_sync_taxonomy.py` — the shared-phrase tests | they assert the stored-once behaviour |
| `tests/unit/test_taxonomy_status_wording.py` — the not-stored sentence | the sentence must stop claiming a loss that no longer happens |
| `audit_report/r22_workbook/SHARED_PHRASES.md` regenerated | its "not stored" row becomes 0 |
| `docs/DATA_ENTRY.md` — "What an automatic run will and will not do" | the row "store a phrase in two categories" flips |

### What the user gains

Every membership the workbook lists is stored: 333 memberships in the committed
file stop being a documented loss. Search for a phrase finds all the categories
that claim it, which is what the workbook has always said.

### What it costs

* A semantic change to a public-ish table: anything that reads `keywords` and
  assumes one row per phrase (search ranking, the duplication register, hashes)
  must be re-read. `keywords_hashs` is keyed by `(hash_id, keyword_id)` and is
  unaffected structurally, but a phrase in two categories now has two rows and
  therefore two hash links.
* The downgrade can fail on data. That refusal is deliberate; a downgrade that
  deletes rows to satisfy a constraint is the kind of thing this repository has
  spent four rounds learning not to do.

---

## Proposal B — extend `job_schedules_schedule_type_check`

### What is wrong today

```sql
schedule_type VARCHAR(32) NOT NULL
    CHECK (schedule_type IN ('scenario_evaluation', 'retention'))
```

The workbook is the source of truth for the taxonomy, and the only unattended
routes to applying it are startup and `tools/i18n/sync_taxonomy.py --watch`.
There is no schedule type for it, so a deployment that wants "reconcile every
night" has to run a cron entry beside the application. The scheduler itself is
ready: it fires, it is observable, it takes one leader at a time.

### The change

```sql
-- m0007_schedule_type_taxonomy_sync.py  (PROPOSED — DO NOT APPLY)
UP = [
    "ALTER TABLE job_schedules DROP CONSTRAINT job_schedules_schedule_type_check",
    "ALTER TABLE job_schedules ADD CONSTRAINT job_schedules_schedule_type_check"
    " CHECK (schedule_type IN ('scenario_evaluation', 'retention', 'taxonomy_sync'))",
]
DOWN = [
    "DELETE FROM job_schedules WHERE schedule_type = 'taxonomy_sync'",   # or disable
    "ALTER TABLE job_schedules DROP CONSTRAINT job_schedules_schedule_type_check",
    "ALTER TABLE job_schedules ADD CONSTRAINT job_schedules_schedule_type_check"
    " CHECK (schedule_type IN ('scenario_evaluation', 'retention'))",
]
```

The downgrade is the risky half: a constraint cannot be restored while a row
names the new type. Disabling the rows preserves them; deleting them loses a
schedule definition. **Recommendation: `UPDATE job_schedules SET enabled = FALSE,
disabled_reason = 'paused' WHERE schedule_type = 'taxonomy_sync'` in the
downgrade, and leave the row to be cleaned up by a decision.**

### What must change in the same commit

| thing | why |
|---|---|
| `services/scheduling/model.py` — `SCHEDULE_TYPES`, `REQUIRED_ROLE`, `PAYLOAD_TARGET`, `validate_payload`, `describe` | the vocabulary is a tuple that the constraint is asserted against |
| `services/scheduling/scheduler.py` — `_schedule_one` and a `_run_taxonomy_sync` entry point | a type with no branch logs "unknown schedule type" and fires nothing |
| `services/jobs/manager.py` — a `taxonomy_sync` builtin in `_run_builtin` | the job type must exist before a schedule can enqueue it (it does exist as an API option today; it does not exist as a JobManager job) |
| `tests/integration/test_scheduler_wiring.py::test_the_database_and_the_vocabulary_agree_on_what_may_be_scheduled` | it asserts the constraint and the tuple are equal; both change together |
| `audit_report/r22_workbook/FIRST_BOOT_MATRIX.md` regenerated | a third row in the type table |
| `docs/DATA_ENTRY.md` — "On a schedule" section | currently says the type is not available |

### What the user gains

"Reconcile the workbook every night" becomes a schedule an administrator creates
on the page, with an owner whose role is re-checked at every fire, a job row that
says what it wrote, and the same shrink limit and rule validation in front of the
write. It also removes a crontab from the deployment story.

### What it costs

An additive CHECK change on a small table — cheap — but it must ship with the job
type, the runner branch and the vocabulary together, or the first fire enqueues a
job the manager refuses. That is the reason this is a proposal and not a commit.
