# Licensing

SYLTHARAE is distributed under `AGPL-3.0-or-later` — the GNU Affero General
Public License, version 3 or (at your option) any later version.

Where each fact lives, so nothing here is a second source of truth:

| what | where |
| --- | --- |
| the licence text | [`LICENSE`](../LICENSE) (AGPL v3, 661 lines) |
| the declaration the package metadata publishes | `pyproject.toml`: `license = "AGPL-3.0-or-later"`, `license-files = ["LICENSE", "THIRD_PARTY_NOTICES.md"]` |
| the dependency check | `tools/licenses/check_licenses.py` (reads the installed distribution metadata; `--quiet` exits non-zero on an incompatible or unknown licence) |
| bundled fonts and static assets | each file's licence sits next to it, e.g. `static/fonts/OFL-Inter.txt`, `static/fonts/OFL-NotoSansArabic.txt`, `static/fonts/OFL-NotoSansHebrew.txt` |
| the source offer the licence requires | `SOURCE_CODE_URL` in `.env.example` and `docs/CONFIGURATION.md`; the default is `DEFAULT_SOURCE_CODE_URL` in `apps/web/app.py` and is rendered on every page and on the first-run setup page |

## Section 13 (remote network interaction)

A user interacting with the software over a network must be offered its
source. The interface renders that link on every page and on the setup page a
fresh install shows; `SOURCE_CODE_URL` overrides the target, and a non-HTTP
value is refused by the setup page rather than rendered.

## Open items

* `THIRD_PARTY_NOTICES.md` does not exist yet. `pyproject.toml` lists it in
  `license-files`, so the package metadata points at a file the repository
  does not ship. Writing it means reviewing the licence of every vendored
  static file and every dependency — a legal review, not a code change — and
  its text is licensing text, which this round does not generate.
* `pymupdf-layout` and `pymupdf4llm` (both installed, both optional PDF
  helpers) declare no usable licence metadata: no `License-Expression`, no
  `License` field, no licence classifier. `tools/licenses/check_licenses.py`
  classifies them `unknown`, which is the honest verdict; resolving it needs
  upstream metadata or a written decision, not a guess in a mapping table.

Both are listed under D-6 in `audit_report/R4_decisions.md`.

This file is under `docs/`, which is not committed (D-7 asks for a decision on
the generated documentation first).
