"""Capture the three migrated tables in a real browser, before and after.

Part of the Round 22 wrap-up (item A). Drives Chromium through
``playwright-core`` + ``@sparticuz/chromium`` (the same bundle
``tools/audit/browser_walk.py`` uses) against a live server, signs in, opens the
three pages the table migration touched, and records for each one:

* a screenshot, full page, at a fixed viewport;
* the table's ``id``, its ``class`` attribute and its column headers;
* the bounding box of the table, so a layout move is a number rather than an
  impression.

    python3 tools/audit/capture_table_pages.py \\
        --base http://127.0.0.1:5055 --user admin --password-env APP_ADMIN_PASSWORD \\
        --out audit_report/r22_workaround/tables/<label>

``/translation-panel`` is not a page: the selection panel is included by
``templates/Search/search.html`` and by the file-detail page. The Search page is
driven, and the emitted ``<table>`` is read from the panel's own container, so
what is captured is the panel on a live page.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
NODE_DIR = pathlib.Path("/tmp/pw")

SCRIPT = r"""
import chrom from '@sparticuz/chromium';
import { chromium } from 'playwright-core';
import fs from 'fs';

const cfg = JSON.parse(process.env.CAPTURE_CONFIG);
const exe = await chrom.executablePath();
const browser = await chromium.launch({
  executablePath: exe,
  args: [...chrom.args, '--no-sandbox', '--disable-dev-shm-usage'],
  headless: true,
});
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
fs.mkdirSync(cfg.outDir, { recursive: true });

await page.goto(cfg.base + '/auth/login', { waitUntil: 'domcontentloaded' });
const user = await page.$('input[name="username"], #username');
if (user) {
  await user.fill(cfg.user);
  await page.fill('input[type="password"], input[name="password"]', cfg.password);
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'domcontentloaded' }).catch(() => null),
    page.click('button[type="submit"], input[type="submit"]'),
  ]);
}

const results = [];
for (const target of cfg.targets) {
  const row = { name: target.name, path: target.path };
  try {
    const response = await page.goto(cfg.base + target.path, { waitUntil: 'networkidle', timeout: 45000 });
    row.status = response ? response.status() : null;
    row.finalUrl = page.url();
    await page.waitForTimeout(1200);
    const info = await page.evaluate((selector) => {
      const table = document.querySelector(selector);
      if (!table) return { found: false };
      const box = table.getBoundingClientRect();
      return {
        found: true,
        id: table.id || null,
        classes: (table.getAttribute('class') || '').split(/\s+/).filter(Boolean),
        headers: Array.from(table.querySelectorAll('thead th')).map((th) => th.textContent.trim()),
        columns: table.querySelectorAll('thead th').length,
        wrapper: table.parentElement ? table.parentElement.className : null,
        box: { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) },
        rows: table.querySelectorAll('tbody tr').length,
        hidden: table.offsetParent === null,
        html: table.outerHTML,
      };
    }, target.selector);
    row.table = info;
    const file = cfg.outDir + '/' + target.name + '.png';
    await page.screenshot({ path: file, fullPage: true });
    row.screenshot = file;
  } catch (error) {
    row.error = String(error).slice(0, 400);
  }
  results.push(row);
}
fs.writeFileSync(cfg.outDir + '/capture.json', JSON.stringify(results, null, 2));
await browser.close();
console.log(JSON.stringify(results));
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:5055")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password-env", default="APP_ADMIN_PASSWORD")
    parser.add_argument("--password", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", default="")
    args = parser.parse_args(argv)

    password = args.password or os.environ.get(args.password_env, "")
    if not password:
        print(f"no password: set {args.password_env}", file=sys.stderr)
        return 2

    targets = [
        {"name": "monitoring", "path": "/monitoring", "selector": "#scenariosTable"},
        {"name": "reports", "path": "/reports", "selector": "#reportByType"},
        {"name": "translation_panel", "path": "/search",
         "selector": "table[data-translation-rows] ~ table, #translationPanel table, table:has(tbody[data-translation-rows])"},
    ]
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    NODE_DIR.mkdir(parents=True, exist_ok=True)
    script = NODE_DIR / "capture_tables.mjs"
    script.write_text(SCRIPT, encoding="utf-8")

    env = dict(os.environ)
    env["CAPTURE_CONFIG"] = json.dumps({
        "base": args.base, "user": args.user, "password": password,
        "outDir": str(out), "targets": targets,
    })
    env.setdefault("LD_LIBRARY_PATH", "/tmp/nssall")
    env["LD_LIBRARY_PATH"] = "/tmp/nssall:" + env.get("LD_LIBRARY_PATH", "")
    result = subprocess.run(["node", str(script)], cwd=str(NODE_DIR), env=env,
                            capture_output=True, text=True, timeout=300)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr[-2000:])
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
