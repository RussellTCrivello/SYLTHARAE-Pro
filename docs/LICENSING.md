# Licensing

SYLTHARAE is licensed under the **GNU Affero General Public License, version 3
or later** — SPDX identifier `AGPL-3.0-or-later`. The full text is in
[LICENSE](../LICENSE); the package metadata in `pyproject.toml` declares the
same expression and lists `LICENSE` and `THIRD_PARTY_NOTICES.md` as the licence
files that ship with the distribution.

## What the licence asks of an operator

The AGPL is the GPL plus section 13: if you run a **modified** copy of this
software so that other people interact with it over a network, those users must
be offered the corresponding source. SYLTHARAE makes that offer in the
application itself rather than in a footer nobody reads:

* every page renders the running version and a link to the source, from the
  `inject_release_info` context processor in `apps/web/app.py`;
* the link's target is the `SOURCE_CODE_URL` environment variable.

Set it to the location of your modified source:

```
SOURCE_CODE_URL=https://example.org/syltharae-fork
```

Only `http://` and `https://` values are accepted. Anything else is refused and
the built-in default (`DEFAULT_SOURCE_CODE_URL`, currently `#`) is used, so a
typo cannot turn a page into a `javascript:` link — the validation and its
warning are in `apps/web/app.py`. The variable is documented in `.env.example`
and in [CONFIGURATION.md](CONFIGURATION.md), and the tests in
`tests/unit/test_licensing.py` check both the presence of the link on the pages
and that scheme restriction.

An unmodified deployment does not have to point anywhere specific: the default
link is inert, and the version plus the copyright statement in LICENSE remain in
place. If you modify the software and let others use it, `SOURCE_CODE_URL` is
the control you must set.

## Third-party components

The application distributes third-party front-end assets, fonts and Python
dependencies, each under its own licence and each permitted here. They are
listed with versions, licence identifiers and the evidence for each — the
header inside the shipped file, or the distribution metadata — in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Nothing in that file adds a
restriction to the AGPL terms; it is the attribution and provenance record.

Two categories are worth calling out because they surprise people:

* **Fonts.** Inter, Noto Sans Arabic and Noto Sans Hebrew ship under the SIL
  Open Font License 1.1, and each family's `OFL-*.txt` is committed next to the
  binaries in `static/fonts/`, because the licence must travel with the fonts.
* **Copyleft dependencies.** Several dependencies are themselves GPL or
  copyleft (for example `extract-msg` and `mobi` under GPL-3.0-only, `mutagen`
  under GPL-2.0-or-later, `psycopg2-binary` under LGPL-3.0-or-later). Combining
  them with an AGPL work is permitted, and the checker below is what proves each
  one is; a dependency that could not be combined (`GPL-2.0-only`, or a
  non-commercial licence) fails the check rather than being waved through.

## Checking the dependency licences

[tools/licenses/check_licenses.py](../tools/licenses/check_licenses.py)
resolves the dependency closure, reads each distribution's declared licence
(`License-Expression`, then `License`, then the `License ::` classifiers) and
classifies it as compatible, incompatible or unknown:

```
python3 tools/licenses/check_licenses.py            # requirements.txt closure
python3 tools/licenses/check_licenses.py --extras   # + pyproject optional extras
python3 tools/licenses/check_licenses.py --quiet    # one summary line, exit status only
```

Exit status is 0 only when nothing is incompatible **and** nothing is unknown: an
unreviewed licence counts as unchecked. Where a package's metadata is missing or
ambiguous, the checker resolves it in its `REVIEWED` table with the upstream
licence and a note saying where that was read, so the decision can be re-checked
rather than trusted. `tests/unit/test_licensing.py` runs the checker (including
the optional extras) and fails on any incompatible or unknown finding, so the
dependency set cannot regress silently.

## Tests

```
python3 -m pytest tests/unit/test_licensing.py -q
```

That file is the enforcement point for everything above: the licence text, the
package metadata, the shipped `THIRD_PARTY_NOTICES.md` coverage of every
vendored file, the font licence texts, the dependency classification, and the
section 13 source link with its version display.
