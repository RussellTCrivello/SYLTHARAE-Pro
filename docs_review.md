# docs/ — review sheet (not committed)

Written for D-7: what each file in `docs/` is, what generates it, what the suite asserts
about it, and anything in it that this repository cannot verify. **Nothing under `docs/`
is committed**, and this sheet is not committed either.

`docs/` in this checkout holds **21 files**. Fourteen documents that the suite reads are
**absent entirely** (listed at the end) — they account for the 38 `DOCS-NOT-COMMITTED`
cases in the failing-test table.

Measured checks referenced below, run in this checkout:
`tools/docs/generate_reference.py --check` → stale;
`tools/docs/generate_schema.py --check` → *schema reference is up to date* (exit 0);
`tools/licenses/check_licenses.py` → 114 compatible, 2 unknown;
`tools/db/integrity_audit.py --json` → 5 redundant index rows;
live `/auth/login` response headers; `git ls-files static`.

---

## 1. Hand-written pages (5)

| file | generator | what the suite asserts | what the repo cannot verify |
| --- | --- | --- | --- |
| `docs/CONFIGURATION.md` | hand-written (marked **STATUS: NEEDS-REVIEW**) | `tests/unit/test_env_config_names.py` — every variable `.env.example` presents as live is read by code; the 7 reserved names appear both in `.env.example` and here. `tests/unit/test_ocr_selfcheck.py` — remediations name only real settings. `tests/unit/test_licensing.py` — quotes `` `SOURCE_CODE_URL` `` | **The "Default" column mixes two different defaults.** It lists `DB_POOL_MIN_CONNECTIONS` / `DB_POOL_MAX_CONNECTIONS` as `2` / `25`, which is what `.env.example` ships; the code's own fallback when nothing is set is `1` / `20` (`database/database/config.py`, and `test_env_config_names::test_pool_defaults_unchanged` asserts `(1, 20)`). Both numbers are defensible, the word "Default" is not. Behaviour-dependent rows (`TESSERACT_CMD` auto-detection, `RATELIMIT_STORAGE_URI` Redis) cannot be verified here: no OCR binary, no Redis. |
| `docs/SECURITY.md` | hand-written (**STATUS: NEEDS-REVIEW**) | `tests/unit/test_csp_no_inline_script.py` — the CSP quoted here must be the one the app sends; `tests/security/test_change_password.py` — the password-change paragraph, the three audit action names and the 10/minute limit. `tests/security/test_import_export_authz.py`, `test_settings_error_hygiene.py` cover the controls it names | **The public-endpoint sentence overstates the list.** It says "the public endpoints are the static files, `auth.*`, `setup.*`, `health.*` and the translations catalogue". `PUBLIC_ENDPOINTS` names six specific `auth.*` endpoints (`login`, `logout`, `me`, `login_page`, `first_admin_page`, `first_admin_create`) and nine `setup.*` ones; `auth.change_password` and the whole user-management surface are *not* public. **HSTS** cannot be verified here: it is only sent when `FLASK_ENV=production` *and* `request.is_secure`, and this sandbox is plain HTTP. The CSP string itself **was verified byte-identical** to the live header. |
| `docs/DEVELOPMENT.md` | hand-written (**STATUS: NEEDS-REVIEW**) | `tests/unit/test_csp_no_inline_script.py` (the `data-on-<event>` convention, no inline handlers); `tests/unit/test_shared_js_helpers.py` (no local `escapeHtml`) | "When no server is reachable the fixtures skip rather than fail" — **not exercised**: `pgserver` always supplies a server in this environment, so the skip path was never taken. The described commands (`python3 -m pytest tests/unit`, the two generators) were run and work. |
| `docs/LICENSING.md` | hand-written, **not** in `pyproject`'s `license-files` | `tests/unit/test_licensing.py` — the SPDX id, `SOURCE_CODE_URL` in `.env.example` and in `CONFIGURATION.md`, the checker's path | Two claims verified: `LICENSE` is 661 lines (measured), and the checker's verdict is real (114 compatible, 2 unknown). One claim is now **out of date in the good direction**: its "Open items" says `THIRD_PARTY_NOTICES.md` does not exist — it exists as of this round (`8bd1c7c`), generated from installed metadata. The `pymupdf-layout` / `pymupdf4llm` gap is still true and still open. |
| `docs/database/DUPLICATION_REGISTER.md` | written from `tools/db/integrity_audit.py --json` | `tests/integration/test_db_integrity_audit.py` — the five shapes are registered, a sixth fails the gate | **Fully verified**: the audit's current output lists exactly these five pairs with these index names. The "what a future migration would do" paragraph is a proposal, not a fact. |

## 2. Generated reference set (16 files)

`docs/reference/` is produced by two generators and is checked for staleness, not for
truth: `tests/unit/test_reference_docs.py` (runs `generate_reference.py --check`) and
`tests/integration/test_schema_reference.py` (runs `generate_schema.py --check`).

| file | generator | check result | what it states that is wrong or unverifiable |
| --- | --- | --- | --- |
| `reference/DATABASE_SCHEMA.md` | `tools/docs/generate_schema.py` | **up to date** (exit 0) against a fresh bootstrap of `m0001`–`m0003` | Nothing found. It is a dump of `pg_catalog` ("42 tables"), and the 42 was re-derived. |
| `reference/HTTP_ROUTES.md` | `tools/docs/generate_reference.py` | **stale** (diff = 2 lines) | `/api/import-export/settings/export` is listed as **`any user`**; the live policy is **`admin`** (`AUTH_ADMIN_READ_ENDPOINTS` in `core/security/flask_ext.py`, the AUTHZ-02 fix). A stale generated page that understates an authorization rule is the worst kind of stale — regenerate before committing. The header count ("484 routes", static excluded) still matches the live URL map. |
| `reference/README.md` | same | **stale** | Module counts: `tools` is listed as **57 modules**; the tree has **79**. Every other package count still matches (`apps` 30, `Api` 82, `core` 126, `database` 51, `pipeline` 4, `reader_file` 29, `services` 46, `settings` 10, `concurrency` 6, `Hdg_Err_Ex_Log` 11, `scripts` 21). |
| `reference/python/core.md` | same | **stale** | Missing `_Spans` (added this round in `temporal_intel`), and it renders `NotificationPriority` as `(Enum)` where the class is now `(str, Enum)`. Everything else in 1 602 lines is a copy of docstrings, so it is exactly as true as they are. |
| `reference/python/database.md` | same | **stale** | Same class of drift (docstrings changed since generation). |
| `reference/python/tools.md` | same | **stale** | Grown by the tools added in rounds 4–6 (`tools/audit/*`), including the ones this report cites. |
| `reference/python/Api.md`, `apps.md`, `Hdg_Err_Ex_Log.md`, `concurrency.md`, `entry_points.md`, `pipeline.md`, `reader_file.md`, `scripts.md`, `services.md`, `settings.md` | same | current per `--check` | Nothing found. Each is a docstring dump; **none of it is executed**, so a docstring that describes behaviour no longer present would pass every check. That is a property of the format, not a defect in a file. |

## 3. Absent, though the suite reads them

Fourteen documents are referenced by tests and are not in `docs/` at all. Their generators
(or the tests that write them) exist, so they are one command away — but that command
publishes documents nobody has read, which is exactly what D-7 asks about.

`ACTION_SURFACE_AUDIT.md` · `ARCHITECTURE.md` · `AUDIT_REPORT.md` · `COMPONENT_LIBRARY.md` ·
`DOMAIN_MODEL.md` · `EXPERIENCE_CONTRACT.md` · `INTERFACE_REGISTRY.md` ·
`JS_ARCHITECTURE_AUDIT.md` · `PRODUCTIZATION_MAP.md` · `REGISTRY_EVIDENCE.md` ·
`SCREEN_INSPECTOR_EVIDENCE.md` · `WINDOWS_OFFLINE.md` · `database/RELATIONSHIP_INTEGRITY.md` ·
`endpoint_inventory.json`

## 4. What I would do before committing any of this

1. Regenerate `docs/reference/` (`generate_reference.py`), because three of its pages are
   stale and one of them understates an authorization rule. `DATABASE_SCHEMA.md` needs no
   action (`--check` exit 0).
2. Fix the "Default" column in `CONFIGURATION.md` — either say `.env.example` ships 2/25
   or say the code falls back to 1/20. One sentence, and it removes the only place where
   the documentation and a test disagree.
3. Correct the public-endpoint sentence in `SECURITY.md` to "six `auth.*` and nine
   `setup.*` endpoints, named in `PUBLIC_ENDPOINTS`".
4. Then decide D-7 (commit or not), and regenerate the fourteen absent documents only
   after that decision — they are the 38 red cases.

## 5. What was corrected on 2026-10-24 (uncommitted, by instruction)

1. `docs/reference/**` regenerated with `tools/docs/generate_reference.py` ("wrote 5 of
   15 reference files"). Diff against the pre-regeneration tree:
   * `HTTP_ROUTES.md:270` — `/api/import-export/settings/export` `any user` -> `admin`
     (matches `AUTH_ADMIN_READ_ENDPOINTS`, `core/security/flask_ext.py:117-126`);
   * `README.md:19` — `tools` 57 -> 79 modules; `python/tools.md` gained the 22 modules it
     had been omitting, including all of `tools/audit/`;
   * `python/core.md` — `_Spans` added; `NotificationPriority` now `(str, Enum)`;
     `priority_basis()` added; `priority_from_summary()` returns `dict`, not `str`;
   * `python/database.md:265` — `check_side_usage` docstring.
   `tests/unit/test_reference_docs.py` now passes (2 passed).
2. `CONFIGURATION.md:34` — the "Default" column said `2` / `25`, which is the
   `DatabaseSettings` default, not what the named variables do. In the working path
   (`DatabaseConfig.create_from_settings`) *no* environment variable sets the pool
   bounds; `DB_POOL_*` and the legacy names are read only in the except branch
   (`database/database/config.py:88-92`, defaults `1`/`20`). The row now says that.
3. `SECURITY.md:16-26` — "the static files, `auth.*`, `setup.*`, `health.*` and the
   translations catalogue" replaced with the live list: 20 endpoints = `static`,
   `favicon`, `health.health`, `get_csrf_token`, `translations.get_i18n_catalog`,
   six `auth.*` (`login`, `login_page`, `logout`, `me`, `first_admin_page`,
   `first_admin_create`) and nine `setup.*`.
4. `DEVELOPMENT.md` — added the OCR/cv2 install trap (diagnose + repair commands) and
   the three ways PostgreSQL can look reachable while the crash-recovery module skips.

Still open, unchanged: the 14 absent documents (38 red cases), `LICENSING.md`'s
"notices does not exist" sentence (now false), and the D-7 decision.
