#!/usr/bin/env python
"""Rewrite host-specific prefixes in generated artefacts, mechanically.

A test log that says ``/tmp/wt/head/tests/...`` is evidence of a run on *this*
machine; the same line with ``<worktree-head>/tests/...`` is evidence of the
same run anywhere. This tool performs that substitution and nothing else: it
does not drop lines, reorder output or edit a number. The mapping is printed
with every run so the transformation is reproducible.

    python tools/audit/sanitize_artifacts.py audit_report/r20
"""
from __future__ import annotations

import argparse
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Longest patterns first: ``/tmp/wt/head`` must win over a bare ``/tmp``.
#:
#: Placeholders are brace-delimited, not angle-bracketed: an XML artefact keeps
#: its failure messages in attributes, and ``<repo>`` inside an attribute makes
#: the file unparseable. Braces are inert in XML, JSON, CSV and plain text, so
#: one placeholder form serves every artefact without escaping rules.
RULES = [
    (re.compile(r"/home/user/SYLTHARAE-Pro"), "{repo}"),
    (re.compile(r"/tmp/wt/head"), "{worktree-head}"),
    (re.compile(r"/tmp/wt/base"), "{worktree-base}"),
    (re.compile(r"/tmp/pgdata_devstack_[A-Za-z0-9_]+"), "{pgdata}"),
    (re.compile(r"/tmp/pytest-of-[A-Za-z0-9._-]+/pytest-\d+"), "{pytest-tmp}"),
    (re.compile(r"/tmp/rv/bin/python"), "{venv}/bin/python"),
    (re.compile(r"/tmp/rv"), "{venv}"),
    (re.compile(r"/tmp/al2023"), "{chromium-libs}"),
    (re.compile(r"/tmp/[A-Za-z0-9._-]+"), "{tmp}"),
    # A parametrised test id can carry a Windows profile path verbatim; the
    # backslashes are doubled inside a pytest id, hence the doubled pattern.
    (re.compile(r"C:\\\\Users\\\\[A-Za-z0-9._-]+"), "{windows-home}"),
    (re.compile(r"C:\\Users\\[A-Za-z0-9._-]+"), "{windows-home}"),
    (re.compile(r"127\.0\.0\.1:5000"), "{base-url}"),
    (re.compile(r"localhost:5000"), "{base-url}"),
]

#: Placeholders written by the first version of this tool. Angle brackets break
#: XML parsing, so any artefact that already contains them is repaired on the
#: next run rather than left unparseable.
LEGACY = [
    ("<worktree-head>", "{worktree-head}"), ("<worktree-base>", "{worktree-base}"),
    ("<pytest-tmp>", "{pytest-tmp}"), ("<chromium-libs>", "{chromium-libs}"),
    ("<pgdata>", "{pgdata}"), ("<venv>", "{venv}"), ("<base-url>", "{base-url}"),
    ("<repo>", "{repo}"), ("<tmp>", "{tmp}"),
]

SUFFIXES = {".xml", ".txt", ".log", ".json", ".csv", ".md"}


def sanitize_text(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for pattern, replacement in RULES:
        text, number = pattern.subn(replacement, text)
        if number:
            counts[replacement] = counts.get(replacement, 0) + number
    for legacy, replacement in LEGACY:
        text, number = text.replace(legacy, replacement), text.count(legacy)
        if number:
            counts[replacement] = counts.get(replacement, 0) + number
    return text, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=pathlib.Path)
    options = parser.parse_args()
    directory = options.directory if options.directory.is_absolute() \
        else ROOT / options.directory
    total = 0
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        if path.name in {"REPORT.md", "portability_baseline.txt"}:
            continue  # prose and the baseline are written by hand, on purpose
        original = path.read_text(encoding="utf-8", errors="ignore")
        cleaned, counts = sanitize_text(original)
        if not counts:
            continue
        path.write_text(cleaned, encoding="utf-8")
        total += sum(counts.values())
        print(f"  {path.relative_to(directory)}: "
              + ", ".join(f"{k} x{v}" for k, v in sorted(counts.items())))
    print(f"{total} fragment(s) rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
