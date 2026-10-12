# Database

The application stores everything in PostgreSQL. The schema is built by ordered,
transactional migrations - never by import-time DDL, and never by hand.

## Creating and upgrading the schema

`database/bootstrap.py` is the only supported way to create or upgrade the
application schema:

```python
ensure_database(cfg)     # create the database if missing (UTF8)
bootstrap_database(cfg)  # ensure database + run every pending migration
schema_status(cfg)       # report the migration state
```

Properties the module guarantees, and the reasons they matter:

* **No import-time DDL.** Nothing touches the database until a caller asks it
  to. The legacy `createsTables.py` executed at import and could not create a
  fresh schema; it is gone.
* **Ordered and transactional.** Migrations are numbered (`m0001`, `m0002`,
  ...) and applied in order; each one either completes or leaves the schema
  untouched.
* **Version tracking.** `schema_migrations` is the ledger. It is what makes a
  re-run idempotent and what a health check reads to report the current
  version.
* **Extension preflight.** `plpgsql` is required; `pg_trgm` is deliberately
  *not* required (m0004 removed the dependency on it).

On start-up the application applies any pending migration, so an upgrade path
from a database created by an earlier version is exercised by
`tests/integration/test_startup_upgrade_path.py` and
`tests/integration/test_migration_upgrade_path.py`.

## Configuration

Connection settings are resolved in one order (the precedence is documented in
`.env.example`, which is authoritative):

1. the process environment (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
   `DB_PASSWORD`),
2. `data/settings.json`,
3. `config/config.example.json`,
4. the dataclass defaults in `database/database/config.py`.

Pool sizing is read from `DB_POOL_MIN_CONNECTIONS` / `DB_POOL_MAX_CONNECTIONS`;
the earlier names (`DB_MIN_CONNECTIONS` / `DB_MAX_CONNECTIONS`) still win if
both are set, so an existing `.env` keeps behaving as it did. The environment
is honoured even after the settings object has been cached - a change made by
the installer must not require a restart to take effect.

## The schema itself

`docs/reference/DATABASE_SCHEMA.md` is generated from a migrated database by
`tools/docs/generate_schema.py` - columns, types, nullability, defaults, keys,
foreign keys and every index. It is compared with a freshly migrated test
database by `tests/integration/test_schema_reference.py`, so it cannot go
stale:

```
python3 tools/docs/generate_schema.py            # write
python3 tools/docs/generate_schema.py --check    # exit 1 if stale
```

What the tables mean, and how they relate, is in `docs/DOMAIN_MODEL.md`.

### What defines the current schema

`database/migrations/` plus the `schema_migrations` ledger. Nothing else.

`database/SYLTHARAE.sql` is a committed `pg_dump --schema-only` snapshot taken
at an earlier revision; it contains no data and nothing in the application or
the deployment reads it. It is **not** the deployment authority and must not be
used to answer "what indexes exist" - the audit found it already behind the
migrations (it lacks the m0035/m0036 `words_hashs` indexes and its
`content_signals.ck_content_signals_resolution` allows six values where the
migrations allow seven). Whether to regenerate it each release or retire it is
an open repository decision (DB-6 in `docs/database/DUPLICATION_REGISTER.md`);
until it is taken, treat the file as historical, and read
`docs/reference/DATABASE_SCHEMA.md` (generated from a migrated database) for the
current shape.

## Reading and writing

* `database/__init__.py` exposes the configured hub used by the application;
  `Api/utils/utils.py` keeps a module-level executor and query cache.
* Every query is parameterised. A migration, a query or a repair script that
  interpolates a value into SQL is a defect, not a style question.
* Bulk work goes through the job system (`jobs`, `job_events`) so a long import
  is observable and cancellable rather than a hung request.

## Operating notes

* **Backups.** `pg_dump` of the application database; `contents_raw` holds the
  file bytes, so a backup without it restores metadata but not content.
* **`geo_gazetteer_loads`** records which release of the place-name data
  produced the resolved places, so a gazetteer refresh is auditable.
* **Destructive operations** (dropping a table, deleting rows) are never part
  of a migration that has already shipped; a correction is a new migration.
* **Tests** never touch the configured application database: the suite creates
  a disposable PostgreSQL (or uses an explicitly named test database on
  `DB_HOST`) and asserts at bootstrap time that the database it writes to is a
  test one.
