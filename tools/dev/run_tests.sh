#!/usr/bin/env bash
# Run a test directory in deterministic shards and report honestly.
#
#   bash tools/dev/run_tests.sh tests/unit 4
#   bash tools/dev/run_tests.sh tests/security
#
# * Files are sorted, then dealt into N contiguous shards, so the same
#   directory and shard count always produce the same shards.
# * Each shard writes a JUnit XML file; the shards are merged and summarized
#   by tools/ci/junit_annotations.py, which prints the totals, every skipped
#   test with its reason, and every failure. A skip is never silent.
# * pgserver data directories ($TMPDIR/pgdata_*) are removed between shards.
# * Exit status is non-zero if any shard fails, errors or crashes, or if the
#   combined XML records any failure or error.
#
# The shard count defaults to one shard per 50 files (AGENTS.md section 2:
# a single process running the whole unit suite was OOM-killed on 2 GB).
# REQUIRE_POSTGRES defaults to 1: a missing PostgreSQL must fail the run, not
# skip it into green.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

usage() {
    echo "usage: bash tools/dev/run_tests.sh <tests/directory> [shards]" >&2
    exit 2
}

[ $# -ge 1 ] && [ $# -le 2 ] || usage
DIR="${1%/}"
SHARDS="${2:-}"

[ -d "$DIR" ] || { echo "run_tests: no such directory: $DIR" >&2; exit 2; }
case "$DIR" in
    tests/*) ;;
    *) echo "run_tests: expected a tests/ subdirectory, got: $DIR" >&2; usage ;;
esac

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || {
    echo "run_tests: $PY not found. Run: bash tools/dev/bootstrap.sh" >&2
    exit 2
}

mapfile -t FILES < <(find "$DIR" -maxdepth 1 -type f -name 'test_*.py' | sort)
N=${#FILES[@]}
[ "$N" -gt 0 ] || {
    echo "run_tests: no test_*.py files in $DIR." >&2
    echo "  (tests/js harnesses are not pytest: run them with node, see docs/TEST_ENVIRONMENT.md)" >&2
    exit 2
}

if [ -z "$SHARDS" ]; then
    SHARDS=$(( (N + 49) / 50 ))
else
    case "$SHARDS" in
        ''|*[!0-9]*) echo "run_tests: shards must be a positive integer: $SHARDS" >&2; exit 2 ;;
    esac
    [ "$SHARDS" -ge 1 ] || { echo "run_tests: shards must be >= 1" >&2; exit 2; }
fi

export REQUIRE_POSTGRES="${REQUIRE_POSTGRES:-1}"
DEFAULT_TMPDIR="$HOME/.cache/tmp"
TMPDIR="${TMPDIR:-$DEFAULT_TMPDIR}"
mkdir -p "$TMPDIR"
export TMPDIR
rm -rf "$TMPDIR"/pgdata_* 2>/dev/null || true

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$TMPDIR/run_tests/$(basename "$DIR")-$STAMP"
mkdir -p "$OUT"

CHUNK=$(( (N + SHARDS - 1) / SHARDS ))
echo "run_tests: $DIR — $N files in $SHARDS shard(s) of up to $CHUNK files"
echo "run_tests: REQUIRE_POSTGRES=$REQUIRE_POSTGRES  TMPDIR=$TMPDIR"
echo "run_tests: results in $OUT"

overall=0
total_start=$SECONDS
for i in $(seq 1 "$SHARDS"); do
    off=$(( (i - 1) * CHUNK ))
    [ "$off" -lt "$N" ] || { echo "shard $i/$SHARDS: empty (fewer files than shards)"; continue; }
    shard_files=("${FILES[@]:off:CHUNK}")
    xml="$OUT/shard_$i.xml"
    log="$OUT/shard_$i.log"
    rm -f "$xml"
    t0=$SECONDS
    rc=0
    "$PY" -m pytest "${shard_files[@]}" -rfE --junitxml="$xml" > "$log" 2>&1 || rc=$?
    dt=$(( SECONDS - t0 ))
    if [ -f "$xml" ]; then
        summary="$("$PY" tools/ci/junit_annotations.py "$xml" | grep -m1 'title=pytest totals' || true)"
        echo "shard $i/$SHARDS: ${#shard_files[@]} files, ${dt}s, exit $rc  $summary"
    else
        echo "shard $i/$SHARDS: ${#shard_files[@]} files, ${dt}s, exit $rc, NO JUNIT XML (crashed?)" >&2
        echo "  its tests are missing from the combined totals below; see $log" >&2
        overall=1
    fi
    [ "$rc" -eq 0 ] || overall=1
    rm -rf "$TMPDIR"/pgdata_* 2>/dev/null || true
done

# --- combined summary through junit_annotations.py ---------------------------
COMBINED="$OUT/combined.xml"
"$PY" - "$OUT" "$COMBINED" <<'PY'
import glob
import os
import sys
import xml.etree.ElementTree as ET

out_dir, combined = sys.argv[1], sys.argv[2]
root = ET.Element("testsuites")
for path in sorted(glob.glob(os.path.join(out_dir, "shard_*.xml"))):
    shard_root = ET.parse(path).getroot()
    for suite in ([shard_root] if shard_root.tag == "testsuite"
                  else list(shard_root.iter("testsuite"))):
        root.append(suite)
ET.ElementTree(root).write(combined, encoding="utf-8")
PY
"$PY" tools/ci/junit_annotations.py "$COMBINED"
if ! "$PY" - "$COMBINED" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
totals = {k: sum(int(s.get(k, 0)) for s in root.iter("testsuite"))
          for k in ("tests", "failures", "errors", "skipped")}
passed = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
print(f"run_tests: combined: {passed} passed, {totals['failures']} failed, "
      f"{totals['errors']} errors, {totals['skipped']} skipped "
      f"({totals['tests']} tests)")
sys.exit(1 if totals["failures"] or totals["errors"] else 0)
PY
then
    overall=1
fi

echo "run_tests: total wall-clock: $(( SECONDS - total_start ))s"

# The suites modify the tracked map_data/registry.db (AGENTS.md section 10).
if command -v git >/dev/null 2>&1 \
   && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
   && [ -n "$(git -C "$ROOT" status --porcelain -- map_data/registry.db)" ]; then
    echo "run_tests: NOTE: the run modified the tracked map_data/registry.db." >&2
    echo "  Restore it before committing unless your task changes it on purpose:" >&2
    echo "      git checkout -- map_data/registry.db" >&2
fi

exit "$overall"
