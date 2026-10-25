# RUNBOOK — install, upgrade, backup, restore, health, logs, limits

Round 10, Phase 8. Every command and every number below was executed in this
round on Linux (Debian 12, Python 3.11.2, PostgreSQL 16.2) against this
repository at the state it is committed in. Where a step was **not** executed,
it says so in those words. Nothing here is copied from a design document.

Placeholders: `$APP` is the checkout directory, `$DATA` is `APP_DATA_DIR`
(default `$APP/data`), and `psql`/`pg_dump`/`createdb` are PostgreSQL client
binaries — they are not on `PATH` in every environment, so each command below
takes `-h/-p/-U` explicitly.

---

## 1. Install

### 1.1 Clean install (verified end to end this round)

    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    export APP_ADMIN_PASSWORD='<at least 12 characters>'
    export DB_HOST=127.0.0.1 DB_PORT=5432 DB_USER=postgres DB_PASSWORD=''
    export DB_NAME=syltharae
    python install.py --non-interactive

What the run printed (fresh clone, fresh venv, empty database):

    ✓ python           3.11.2
    ✓ packages
    ✓ postgresql
    ✓ 50 packages importable
    ✓ config.json written
    ✓ Write configuration          .env created
    ✓ Database & schema            Created 'syltharae_p2fresh'; 3 migration(s) applied
    ✓ Administrator                'admin' created
    ✓ Runtime directories          7 directories ensured
    ✓ Finalize                     System marked as initialized
    ✓ flask_app            492 routes
    ✓ init_marker          present
    ✅ Installation completed successfully!

Exit code 0. Notes that matter:

* `APP_ADMIN_PASSWORD` (and every other key the installer asks for) is read
  from the **environment** and wins over `.env`. Without this an unattended
  install cannot create an administrator at all.
* The database must be **UTF8**. Bootstrap refuses anything else
  (`database/bootstrap.py: bootstrap_encoding_guard`) because the corpora are
  Arabic, Hebrew and Persian as well as Latin. A cluster initialised with
  `--locale=C` produces `SQL_ASCII` databases; create the database explicitly:

      createdb -h 127.0.0.1 -p 5432 -U postgres -T template0 -E UTF8 syltharae

* If the Administrator step fails, the installer stops **before** writing the
  initialization marker, so `/setup` still works. Re-run the installer or use
  the web wizard at `/setup`.
* The interactive wizard is the alternative: `python install.py` (no flag), or
  the browser flow at `/setup` on a fresh install.

### 1.2 Start

    bash start.sh                       # or: python run_web.py

Measured: `python run_web.py` serves 492 routes; `/health` answered 200 after
about 3 seconds.

### 1.3 A note the logs make at every start (current behaviour, by design of
this round's freeze)

    WARNING apps.web.app: Job scheduler not started: ImportError: cannot import name
    'Scheduler' from 'services.scheduling.scheduler'

The scheduler is **not wired**. `apscheduler` is declared in both manifests, but
`_start_scheduler()` never starts anything. This is a reported open decision,
not a defect this runbook can fix.

---

## 2. Upgrade

    bash stop.sh 2>/dev/null || pkill -f run_web.py
    git pull
    . .venv/bin/activate && pip install -r requirements.txt
    python install.py --non-interactive      # idempotent: applies pending migrations only

Measured: running the bootstrap twice on an already-migrated database printed

    run 1 -> {'database_created': False, 'applied_migrations': [], 'current_version': '0003'}
    run 2 -> {'database_created': False, 'applied_migrations': [], 'current_version': '0003'}

so re-running the installer is safe. The schema is at version `0003`
(`0001 baseline`, `0002 category_parent_id`, `0003 sources_attachments`).

**Back up before every upgrade** (section 3). Migrations are forward-only;
there is no down-migration.

---

## 3. Backup

Two things hold state that cannot be regenerated: the PostgreSQL database and
`APP_DATA_DIR` (translation memory, staged uploads, checkpoints, map registry,
logs).

    # 1. database - custom format, compressed
    pg_dump -h 127.0.0.1 -p 5432 -U postgres -Fc \
            -f /backup/syltharae-$(date +%F).dump syltharae

    # 2. application data
    tar czf /backup/appdata-$(date +%F).tar.gz -C "$DATA" .

    # 3. the two configuration files (they hold secrets)
    install -m 600 .env /backup/.env-$(date +%F)
    install -m 600 config.json /backup/config.json-$(date +%F)

Measured on a database with 40 tables / 6 251 rows / 300 ingested files:

    dump     498 KB, 0.12 s
    restore  0.31 s

**Stop the application before taking the pair**, or take the dump and the data
tar in quick succession: an import running between the two means the tar
describes a different moment than the dump. Individual file processing commits
per file, so a dump taken mid-import is *consistent*, just not *current*.

---

## 4. Restore

### 4.1 Database

    createdb -h 127.0.0.1 -p 5432 -U postgres -T template0 -E UTF8 syltharae_restored
    pg_restore -h 127.0.0.1 -p 5432 -U postgres -d syltharae_restored \
               --no-owner --no-privileges /backup/syltharae-YYYY-MM-DD.dump

Verify with the fingerprint tool (row counts **and** row-content checksums per
table, independent of physical order):

    python tools/db/db_fingerprint.py syltharae \
        /tmp/fp_source.json --host 127.0.0.1 --port 5432 --user postgres
    python tools/db/db_fingerprint.py syltharae_restored \
        /tmp/fp_restored.json --host 127.0.0.1 --port 5432 --user postgres
    diff /tmp/fp_source.json /tmp/fp_restored.json && echo IDENTICAL

Measured this round: 40 tables, 6 251 rows, `fingerprints identical: True`.
The two files differ in exactly one field — `database` (`syltharae_app` versus
`syltharae_restored`) — because the tool records which database it read. Compare
the `tables` and `total_rows` objects:

    diff <(jq -S .tables /tmp/fp_source.json) <(jq -S .tables /tmp/fp_restored.json)

Then point the application at the restored database (`DB_NAME` in `.env`) and
restart, or rename the databases:

    # stop the app first
    psql -h 127.0.0.1 -p 5432 -U postgres -d postgres \
         -c 'ALTER DATABASE syltharae RENAME TO syltharae_old' \
         -c 'ALTER DATABASE syltharae_restored RENAME TO syltharae'

### 4.2 `APP_DATA_DIR` (translation memory included)

    pkill -f run_web.py                    # the SQLite file must not be open
    mv "$DATA" "$DATA.broken"
    mkdir -p "$DATA"
    tar xzf /backup/appdata-YYYY-MM-DD.tar.gz -C "$DATA"
    bash start.sh

Measured this round: four corrections (en→ar, en→he, en→fa, en→hr) were stored
through `POST /api/translation/memory/correct`, the memory file was deleted,
restored from the tar, and
`sha256 before backup = sha256 after restore =
035cfc017e7db3436cea039ef176380f37078111af13d6562500635a4a01c3c5`;
after the restore `POST /api/translation/memory/suggest` returned
`exact_match=yes` for all four languages.

Translation memory is a SQLite file at `$DATA/translation/translation_memory.db`
— **not** a PostgreSQL table (frozen schema). Copying that one file is a
complete memory backup.

---

## 5. Health

    curl -s http://127.0.0.1:5055/health
    {"checks":{"database":"ok","settings":"ok"},"status":"healthy","uptime_seconds":6}

* `200` healthy, `503` when the database probe fails or the settings cannot be
  read. The body never names an exception class or a connection string.
* The database probe is bounded (`HEALTH_DB_TIMEOUT_SECONDS`, default 2 s,
  clamped) so a hung database cannot hang the probe.
* Measured during the PostgreSQL `SIGKILL` drill: `/health` answered **503**
  while the server was down and **200** again after it returned; the app
  process never exited.
* Measured with the data volume 100 % full: `/health` stayed **200** — a full
  disk does not take the application down, it makes the write paths answer
  `503 memory_unavailable` / `507 STORAGE_UNAVAILABLE`.

---

## 6. Logs

| what | where |
| --- | --- |
| application | stdout/stderr of `run_web.py`; `$DATA/logs/` |
| installer | stdout of `install.py` |
| audit trail | `audit_log` table (who did what, `translation.*`, `place.*`, job actions) |
| import jobs | `jobs` table and `/operations/jobs` (status, progress, errors, `completed_at`) |
| PostgreSQL | the server's own log (`pg_ctl -l`) |

`LOG_LEVEL` (`.env`) sets verbosity; `INFO` is the default. Errors carry a
`correlation_id` (`ERR-YYYYMMDD-NNNNNN`) that also appears in the log line, so a
user's screenshot can be matched to a server event.

---

## 7. Known limits and failure behaviour (measured, not assumed)

| condition | what happens | evidence |
| --- | --- | --- |
| data volume 100 % full — translation memory write | `503 memory_unavailable`, message names the reason | tmpfs drill, this round |
| data volume 100 % full — upload staging | `507 STORAGE_UNAVAILABLE` with the errno; no half-written chunk left behind | tmpfs drill, this round |
| data volume 100 % full — reads | unaffected; `/health` 200 | tmpfs drill |
| PostgreSQL killed mid-import | `/health` 503 while down; pool retries ("Failed to get connection (attempt 1/2)"); the job **resumes** when the server returns and completes | 705-file import, `kill -9` on the postmaster; finished 704/705 stored, 1 failed file, zero orphan rows |
| application killed mid-import | no data corruption (no partial rows, no dangling foreign keys), and on the next start the job is marked `FAILED` with "Application restarted while the job was running" | `kill -9` on `run_web.py` at 16 %; `recover_stale_jobs(stale_seconds=0)` at startup |
| graceful `pg_ctl restart` while the app holds pooled connections | the restart **blocks** (fast shutdown waits for the pool) — kill the postmaster instead of waiting | restart drill: >180 s with no progress, then a clean crash recovery |
| a job is left `RUNNING` by a crash | cleared at the next start (startup recovery), not after six hours | this round's fix; `JOBS_STALE_SECONDS` (default 6 h) governs only the *runtime* guard |
| translation memory file deleted while running | the API answers `503 memory_unavailable` instead of silently starting an empty memory | `services/translation/memory.py`, unit-tested |
| database not UTF8 | bootstrap refuses with the encoding named and the remedy (dump/restore into a UTF8 database) | `test_database_encoding_guard.py` |

Performance budgets measured this round (100 000 paths, `syltharae_perf100k`,
median / p95 in ms): `/api/search` 282/440 (page 1), 273/283 (page 100),
263/276 (page 2000); `/api/query/cursor` 13/19 (13/19 at cursor 50 000, 12/13 on
`hashs`); `/api/places` 11/13; `/api/signals` 14/14. SQL level: count 23.7 ms;
`OFFSET 99900` 18.6 ms versus keyset 0.041 ms (≈450×). These are the numbers to
watch when the corpus grows; they were measured on this machine, not estimated.

---

## 8. Two things this runbook cannot tell you

1. **The scheduler is not wired.** Schedules can be created through the UI and
   the rows are stored, but nothing runs them. This is an open decision.
2. **No translation engine is installed here.** `pip install argostranslate` and
   its model packages are the supported path, but no real-model translation
   quality or speed has been measured in this environment (the benchmark tool
   refuses to run rather than measure a stub).
