# Third-party notices

SYLTHARAE itself is licensed under the **GNU Affero General Public License,
version 3 or later** (`AGPL-3.0-or-later`, see [LICENSE](LICENSE)). This file
records the third-party components the application distributes or depends on,
their licences, and where each licence statement can be checked.

Nothing here is an additional restriction on the AGPL terms; it is the
attribution and provenance record for the components listed.

Three groups of components are covered:

1. **vendored front-end assets** shipped in `static/` (bundled JavaScript, CSS
   and icon fonts);
2. **fonts** shipped in `static/fonts/`, with their SIL Open Font License texts;
3. **Python dependencies** resolved from `requirements.txt` and the optional
   extras in `pyproject.toml`.

Versions below are the ones carried in the shipped files' own headers. The
bundles are refreshed by replacing the file, so the header in the file - not
this table - is the authority when the two are compared.

## 1. Vendored front-end assets

| Component | Version | Licence | Files |
| --- | --- | --- | --- |
| Bootstrap (CSS and JS bundle) | 5.3.0 | MIT | `static/css/bootstrap.min.css`, `static/js/bootstrap.bundle.min.js` |
| Bootstrap Icons (icon font, CSS and font binaries) | 1.13.1 | MIT | `static/icons/bootstrap-icons.min.css`, `static/icons/fonts/bootstrap-icons.woff`, `static/icons/fonts/bootstrap-icons.woff2` |
| jQuery | 3.6.0 | MIT | `static/js/jquery.min.js` |
| Select2 (JS and CSS) | 4.0.13 | MIT | `static/dist/js/select2.min.js`, `static/dist/css/select2.min.css` |
| Chart.js (UMD bundle) | 4.4.0 | MIT | `static/js/chart.umd.js` |
| jsPDF (UMD bundle) | 2.5.1 | MIT | `static/js/jspdf.umd.min.js` |

Evidence per file, readable in the shipped copy:

* Bootstrap: `/*! Bootstrap v5.3.0 (https://getbootstrap.com/) Copyright
  2011-2023 The Bootstrap Authors Licensed under MIT
  (https://github.com/twbs/bootstrap/blob/main/LICENSE)`.
* Bootstrap Icons: `/*! Bootstrap Icons v1.13.1 (https://icons.getbootstrap.com/)
  Copyright 2019-2024 The Bootstrap Authors Licensed under MIT
  (https://github.com/twbs/icons/blob/main/LICENSE) */`.
* jQuery: `/*! jQuery v3.6.0 | (c) OpenJS Foundation and other contributors |
  jquery.org/license */`.
* Select2: `/*! Select2 4.0.13 |
  https://github.com/select2/select2/blob/master/LICENSE.md */` (the header is
  on the JavaScript file; the stylesheet is the same release of the same
  component, and Select2 is MIT).
* Chart.js: the bundle keeps the build provenance line
  `Original file: /npm/chart.js@4.4.0/dist/chart.umd.js`; that CDN build carries
  no licence header, so the licence is cited from the upstream project
  (`https://github.com/chartjs/Chart.js/blob/master/LICENSE.md`, MIT).
* jsPDF: `/** @license jsPDF - PDF Document creation from JavaScript Version
  2.5.1 ... Copyright (c) 2010-2021 James Hall <james@parall.ax>, 2015-2021
  yWorks GmbH, ...` followed by the MIT permission text.

Bootstrap Icons also ships `static/icons/bootstrap-icons.css`,
`static/icons/bootstrap-icons.json`, `static/icons/bootstrap-icons.scss` and
`static/icons/bootstrap-icons.ts` from the same MIT-licensed release; they are
source/asset companions of the entries above rather than separate components.

## 2. Fonts

| Font | Licence | Files | Licence text |
| --- | --- | --- | --- |
| Inter | SIL Open Font License 1.1 | `static/fonts/inter-*.ttf` | `static/fonts/OFL-Inter.txt` |
| Noto Sans Arabic (including Condensed, SemiCondensed and ExtraCondensed) | SIL Open Font License 1.1 | `static/fonts/NotoSansArabic*.ttf` | `static/fonts/OFL-NotoSansArabic.txt` |
| Noto Sans Hebrew | SIL Open Font License 1.1 | `static/fonts/NotoSansHebrew-VF.ttf` | `static/fonts/OFL-NotoSansHebrew.txt` |

Each `OFL-*.txt` beside the fonts is the upstream licence text as shipped with
the font: it begins with the font's copyright line and contains
`SIL OPEN FONT LICENSE Version 1.1`. The OFL permits redistribution of the
fonts as part of a larger work, provided the licence travels with them and the
fonts are not sold on their own - which is why the texts are committed next to
the binaries rather than only referenced.

## 3. Python dependencies

The dependency closure is declared in `requirements.txt` and `pyproject.toml`
and its licences are read from each installed distribution's metadata by
[tools/licenses/check_licenses.py](tools/licenses/check_licenses.py), which
classifies an expression as compatible with `AGPL-3.0-or-later` or not. On the
declared closure that check reports **112 compatible, 0 incompatible, 0 unknown,
0 not installed**:

```
python3 tools/licenses/check_licenses.py --quiet
```

Grouped by the licence expression the metadata declares:

| Declared licence | Packages |
| --- | --- |
| MIT | beautifulsoup4, blinker, brotli, charset-normalizer, colorclass, compressed-rtf, deprecated, docx2txt, et-xmlfile, flask-compress, flask-limiter, iniconfig, lark, limits, loguru, markdown-it-py, mdurl, msoffcrypto-tool, onnxruntime, openpyxl, ordered-set, platformdirs, pluggy, pyclipper, pyparsing, pytest, pytest-cov, python-docx, python-pptx, pytz, pyyaml, red-black-tree-mod, rich, rollbar, ruff, sentry-sdk, six, soupsieve, texttable, tzlocal, urllib3 |
| BSD-3-Clause | babel, click, easygui, flask, flask-babel, flask-wtf, idna, itsdangerous, jinja2, lxml, markupsafe, olefile, oletools, protobuf, psutil, pycparser, pypdf, python-dotenv, shapely, striprtf, werkzeug, wtforms, xlrd |
| Apache-2.0 | bandit, coverage, fasteners, flatbuffers, opencv-python, opencv-python-headless, pgserver, pytesseract, rapidocr-onnxruntime, requests, stevedore, tzdata |
| BSD-2-Clause | ebcdic, icalendar, pygments, wrapt, xlsxwriter |
| LGPL-2.1-or-later | inflate64, multivolumefile, py7zr, pybcj, pyppmd |
| PSF-2.0 | backports-zstd, defusedxml, standard-imghdr, typing-extensions |
| GPL-3.0-only | extract-msg, mobi, pcodedmp |
| LGPL-3.0-or-later | psycopg2-binary, pyxlsb |
| GPL-2.0-or-later | mutagen |
| GPL-3.0-or-later | html2text |
| Apache-2.0 OR BSD-3-Clause | cryptography, python-dateutil |
| Apache-2.0 OR BSD-2-Clause | packaging |
| GPL-2.0-or-later OR Apache-2.0 | odfpy |
| BSD-2-Clause AND LicenseRef-Public-Domain | pycryptodomex |
| BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | numpy |
| MPL-2.0 | certifi |
| MPL-2.0 AND MIT | tqdm |
| MIT-0 | cffi |
| MIT-CMU | pillow |
| ISC | rarfile |
| 0BSD | chardet |
| LGPL-3.0-only | rtfde |
| AGPL-3.0-only | pymupdf |
| AGPL-3.0-or-later | ebooklib |

Notes that matter for the licence reading:

* `pyproject.toml` declares the distributions that are not installed in every
  environment (`libpff-python`, `pyzipper`, `waitress` - PST support, encrypted
  archives, and the production WSGI server). They are **not installed here**,
  so the checker reports them as not installed rather than judging them; review
  their licences before adding them to a deployment, as `requirements.txt`
  already instructs for `libpff-python`.
* Where metadata is missing or ambiguous, `tools/licenses/check_licenses.py`
  resolves the package in its `REVIEWED` table, recording the upstream licence
  **and where it was read**, so a reviewer can re-check the entry instead of
  trusting it. An unreviewed licence is reported as unknown, and unknown fails
  the check.
* `GPL-2.0-only` is classified incompatible on purpose: it cannot be combined
  with AGPL-3.0. `GPL-2.0-or-later`, `GPL-3.0-only` and `LGPL-2.1-or-later`
  are compatible, and a dual `MIT OR GPL-2.0-only` is compatible because the
  MIT alternative can be taken.

## Re-running the checks

```
# dependency licences (exit 1 on anything incompatible or unknown)
python3 tools/licenses/check_licenses.py

# the notices must list every vendored file that ships, and nothing that does not
python3 -m pytest tests/unit/test_licensing.py -q
```

`tests/unit/test_licensing.py` verifies this file against the repository: it
scans `git ls-files static` for vendored bundles, font binaries and icon fonts,
and fails if any of them is missing here - and equally if this file lists a path
that does not exist. That is what keeps this document from drifting away from
what is actually shipped.
