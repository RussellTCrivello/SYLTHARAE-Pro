# Round 14 evidence

Item 1 - action-name ownership.

* `ownership_red.txt` - `tests/unit/test_js_action_ownership.py` against the
  pre-fix tree: five failing tests, naming all eight co-loading collisions.
* `ownership_green.txt` - the same file plus `test_js_global_collisions.py`
  after the renames: 10 passed.
* `browser_actions.html`/`browser_actions.txt` + `browser_actions.json` - a real
  Chromium run (`tools/audit/browser_action_ownership.py`) over the 18 pages
  that use one of the 17 duplicate names. For each action it records which
  script made the last `window.<name>` assignment (a setter installed before any
  page script runs - the registry's copies are bound functions, so
  `toString()` cannot identify them) and what a click on the control did: the
  request it issued, or the effect it produced.
  Result: **70 checks, 0 unexpected failures**; 4 known product defects and 4
  fixture limits are listed in the report.

## Rebuilding the browser in this sandbox

The image has no browser, no npm bundle and no NSS. Per session:

```
python3 -m venv /tmp/sylth-venv && /tmp/sylth-venv/bin/pip install -r requirements.txt
mkdir -p /tmp/br && cd /tmp/br && npm init -y && npm install puppeteer-core@23 @sparticuz/chromium@131
# NSS/NSPR shims: Chromium links these; nothing in this image ships them and the
# only reachable registries are npm/pypi/github. Only 38 NSS symbols are used,
# none of them reached on an http:// page (see build_stubs below).
```

`/tmp/stubgen` is produced by exporting each undefined NSS/NSPR symbol from the
Chromium binary as a returning-0 stub, versioned to the versions `readelf -V`
reports (`NSS_3.2`, `NSS_3.3`, `NSS_3.4`, `NSS_3.6`, `NSS_3.9.2`, `NSS_3.30`,
`NSSUTIL_3.12.3`). Chromium then starts, renders and drives the pages; TLS is
not exercised (every request is `http://127.0.0.1`).

Item 5 - the clean-clone two-part suite. **Partial, and committed that way.**

* `item5_clean_clone_suite.md` - what ran, what it produced, where it stopped,
  and the commands to finish it.
* `item5_observed_failing_ids_unit.txt` - the 39 unit failing identifiers printed
  during the clean-clone run (11 ERROR + 28 FAILURE), against the 67-id round-13
  baseline.
* `item5_cleared_ids_unit.txt` - the 29 identifiers that failed in round 13 and
  passed on the clean clone; all of them text-recognition tests that needed an
  engine.

Both identifier lists carry an explicit evidence grade at the top: the JUnit
record they were read from was destroyed with `/tmp` when the sandbox was
rebuilt, so they are **observed, not committed evidence**. The unit part of the
diff was computed; the integration part never finished and has no count. Re-running
the two commands in `item5_clean_clone_suite.md` on a fresh clone is what turns
these numbers into evidence.
