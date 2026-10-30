#!/usr/bin/env python3
"""Install the lock the documented way, and prove the result twice.

    python3 tools/audit/check_install.py            # builds twice, from scratch

This is the check a CI job (or a release) runs before believing an environment.
It is deliberately not a unit test: it creates real virtualenvs, installs the
real lock and imports the real OpenCV, which takes a few minutes.

What it does, twice, in two directories that do not exist beforehand:

1. ``python3.11 -m venv <dir>``
2. ``<dir>/bin/pip install --no-deps -r requirements.lock`` - the command the
   lock's own header documents, nothing else
3. ``<dir>/bin/python tools/audit/env_lock.py --check`` - the installed set is
   the lock, and its OpenCV loads
4. ``<dir>/bin/python -c "import cv2"`` - measured, not inferred
5. ``<dir>/bin/python tools/audit/env_lock.py --fingerprint`` - the set hash

Then it compares the two runs: the same set hash, the same package count, the
same OpenCV version, the same owners. **A difference fails the check** - a lock
that installs to two different sets is not a lock.

The plain-``pip install -r`` failure is demonstrated too, in a third
throwaway environment, because "unsupported" is a claim that should come with
its evidence: resolving the lock re-adds the GUI OpenCV that rapidocr declares,
and the check must then refuse that environment with a non-zero exit.

``--no-plain-install`` skips that third environment (it re-resolves the whole
dependency graph and is the slowest part).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCK = ROOT / "requirements.lock"
ENV_LOCK = ROOT / "tools" / "audit" / "env_lock.py"


def _run(command, label, check=True):
    print(f"+ {' '.join(str(part) for part in command)}", flush=True)
    completed = subprocess.run([str(part) for part in command], text=True,
                               capture_output=True)
    if check and completed.returncode != 0:
        raise SystemExit(f"{label} failed (exit {completed.returncode}):\n"
                         f"{completed.stdout[-2000:]}\n{completed.stderr[-2000:]}")
    return completed


def _build(directory: pathlib.Path, python: str, *, resolve: bool):
    """One environment, built exactly the way the lock says to build it."""
    venv = directory / "venv"
    _run([python, "-m", "venv", venv], "creating the venv")
    pip = venv / "bin" / "pip"
    target = venv / "bin" / "python"
    command = [pip, "install", "--quiet"]
    if not resolve:
        command.append("--no-deps")
    command += ["-r", LOCK]
    _run(command, "installing the lock")

    fingerprint = _run([target, str(ENV_LOCK), "--fingerprint"], "fingerprint")
    check = _run([target, str(ENV_LOCK), "--check"], "env_lock --check", check=False)
    import_cv2 = _run([target, "-c",
                       "import cv2, importlib.metadata as m\n"
                       "owners=[d.metadata['Name'] for d in m.distributions()\n"
                       "        if (d.metadata['Name'] or '').lower().replace('_','-')"
                       " in ('opencv-python','opencv-python-headless',"
                       "'opencv-contrib-python','opencv-contrib-python-headless')]\n"
                       "print(cv2.__version__)\n"
                       "print(','.join(sorted(owners)))"],
                      "import cv2", check=False)
    lines = import_cv2.stdout.splitlines()
    return {
        "directory": str(directory),
        "set_hash": fingerprint.stdout.strip(),
        "packages": (json.loads(_run([target, str(ENV_LOCK), "--json"],
                                     "report").stdout)["packages"]),
        "env_lock_exit": check.returncode,
        "env_lock_output": (check.stdout + check.stderr).strip().splitlines()[-1:],
        "cv2_import_exit": import_cv2.returncode,
        "cv2_version": lines[0] if lines else None,
        "cv2_owners": lines[1].split(",") if len(lines) > 1 else [],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--python", default="python3.11")
    parser.add_argument("--no-plain-install", action="store_true",
                        help="skip the demonstration of the unsupported command")
    parser.add_argument("--keep", action="store_true",
                        help="leave the built environments on disk")
    args = parser.parse_args(argv)

    lock_text = LOCK.read_text(encoding="utf-8")
    if "INSTALL WITH --no-deps" not in lock_text:
        raise SystemExit("REFUSING: the lock no longer states how to install it")

    root = pathlib.Path(tempfile.mkdtemp(prefix="lock-check-"))
    runs = []
    failures = []
    for index in (1, 2):
        directory = root / f"run{index}"
        directory.mkdir()
        result = _build(directory, args.python, resolve=False)
        runs.append(result)
        print(json.dumps(result, indent=2), flush=True)
        if result["env_lock_exit"] != 0:
            failures.append(f"run {index}: env_lock --check exited "
                            f"{result['env_lock_exit']}")
        if result["cv2_import_exit"] != 0:
            failures.append(f"run {index}: `import cv2` failed")
        if result["cv2_owners"] != ["opencv-python-headless"]:
            failures.append(f"run {index}: cv2/ is owned by {result['cv2_owners']}")

    same = {key: runs[0][key] for key in ("set_hash", "packages", "cv2_version",
                                          "cv2_owners")}
    if runs[0]["set_hash"] != runs[1]["set_hash"]:
        failures.append("the two builds produced different set hashes: "
                        f"{runs[0]['set_hash']} vs {runs[1]['set_hash']}")
    if runs[0]["packages"] != runs[1]["packages"]:
        failures.append("the two builds produced different package counts: "
                        f"{runs[0]['packages']} vs {runs[1]['packages']}")

    plain = None
    if not args.no_plain_install:
        directory = root / "plain"
        directory.mkdir()
        print("\n--- demonstrating the unsupported command: pip install -r ---",
              flush=True)
        plain = _build(directory, args.python, resolve=True)
        print(json.dumps(plain, indent=2), flush=True)
        # It must FAIL. An environment that installs the GUI build and then
        # cannot import cv2 is the defect this whole check exists for.
        if plain["env_lock_exit"] == 0 and plain["cv2_import_exit"] == 0:
            failures.append(
                "`pip install -r requirements.lock` produced a working "
                "environment; the documented --no-deps requirement is no longer "
                "load-bearing, so the lock must be re-examined (it may now "
                "resolve to the headless build, which would be a change worth "
                "recording rather than a failure to hide)")

    print("\n" + "=" * 72)
    print("install check")
    print("=" * 72)
    print(json.dumps({"runs": runs, "identical": same,
                      "plain_install": plain and {
                          "set_hash": plain["set_hash"],
                          "cv2_import_exit": plain["cv2_import_exit"],
                          "cv2_owners": plain["cv2_owners"],
                          "env_lock_exit": plain["env_lock_exit"]}},
                     indent=2))

    if not args.keep:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"\nboth builds are the lock: {runs[0]['set_hash']}, "
          f"{runs[0]['packages']} packages, cv2 {runs[0]['cv2_version']} "
          f"owned by {', '.join(runs[0]['cv2_owners'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
