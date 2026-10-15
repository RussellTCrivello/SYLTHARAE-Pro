#!/usr/bin/env bash
# One-command test environment for SYLTHARAE.
#
#   bash tools/dev/bootstrap.sh
#
# Idempotent: safe to re-run at any time. It reuses an existing Python 3.11
# .venv, reinstalls the declared dependencies (so an edit to requirements.txt
# or the dev extra is picked up), and prints everything it did.
#
# What the suite expects and why is documented in docs/TEST_ENVIRONMENT.md;
# the working protocol is AGENTS.md section 2.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

did=()

# --- TMPDIR: keep it off small or RAM-backed filesystems, with headroom ------
# pgserver's initdb and the pytest runs write here; a full TMPDIR fails the
# integration suite with "No space left on device" (AGENTS.md section 10).
DEFAULT_TMPDIR="$HOME/.cache/tmp"
TMPDIR="${TMPDIR:-$DEFAULT_TMPDIR}"
mkdir -p "$TMPDIR"
avail_kb="$(df -k "$TMPDIR" | awk 'NR==2 {print $4}')"
if [ "$avail_kb" -lt 2097152 ]; then
    echo "bootstrap: REFUSING to continue." >&2
    echo "  TMPDIR=$TMPDIR sits on a filesystem with only ${avail_kb} KiB free" >&2
    echo "  (less than 2 GiB). The test suites and pgserver need at least that." >&2
    echo "  Point TMPDIR at a larger filesystem and re-run." >&2
    exit 1
fi
export TMPDIR
echo "bootstrap: TMPDIR=$TMPDIR (${avail_kb} KiB free)"

# --- uv ----------------------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
    # --break-system-packages is required on PEP 668 (Debian) systems and a
    # no-op everywhere else.
    echo "bootstrap: installing uv"
    python3 -m pip install -q --break-system-packages uv
    did+=("installed uv")
fi
echo "bootstrap: uv $(uv --version | awk '{print $2}')"

# A uv-managed Python 3.11 is preferred, but the download is blocked in some
# sandboxes; that must not kill the bootstrap, because "uv venv -p 3.11"
# then falls back to the system interpreter (verified: Python 3.11.2).
if ! uv python install 3.11 >/dev/null 2>&1; then
    echo "bootstrap: uv python install 3.11 unavailable (download blocked?); using the system Python"
fi

# --- .venv (Python 3.11) -----------------------------------------------------
if [ -x .venv/bin/python ] && .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)' 2>/dev/null; then
    echo "bootstrap: .venv already present ($(.venv/bin/python --version 2>&1))"
else
    if [ -e .venv ]; then
        echo "bootstrap: .venv exists but is not Python 3.11; recreating it"
        rm -rf .venv
    else
        echo "bootstrap: creating .venv with Python 3.11"
    fi
    uv venv -q -p 3.11 .venv
    did+=("created .venv ($(.venv/bin/python --version 2>&1))")
fi

# --- dependencies ------------------------------------------------------------
# The test tooling is the dev extra declared in pyproject.toml; read it from
# the file rather than retyping the package list.
echo "bootstrap: installing requirements.txt"
uv pip install -q --python .venv/bin/python -r requirements.txt
echo "bootstrap: installing the dev extra from pyproject.toml"
uv pip install -q --python .venv/bin/python -r pyproject.toml --extra dev
did+=("installed requirements.txt + the pyproject dev extra")

# --- known repair: exactly one cv2, the declared headless one ----------------
# requirements.txt asks for opencv-python-headless, but rapidocr-onnxruntime
# also declares the GUI opencv-python, so a plain install leaves BOTH
# distributions in the venv and whichever was unpacked last owns cv2. On hosts
# without libGL.so.1 the GUI build cannot import, which fails the OCR unit
# tests. Removing the GUI build leaves the declared headless one in place and
# is harmless on hosts that do have libGL. See docs/DEFECT_REGISTER.md and
# docs/TEST_ENVIRONMENT.md.
if uv pip list --python .venv/bin/python 2>/dev/null | grep -q '^opencv-python ' \
   && uv pip list --python .venv/bin/python 2>/dev/null | grep -q '^opencv-python-headless '; then
    echo "bootstrap: repair: both opencv distributions present; keeping the declared headless one"
    uv pip uninstall -q --python .venv/bin/python opencv-python
    uv pip install -q --python .venv/bin/python --reinstall opencv-python-headless
    did+=("removed the GUI opencv-python so cv2 comes from opencv-python-headless")
fi

# --- verification ------------------------------------------------------------
if .venv/bin/python -c "import cv2" >/dev/null 2>&1; then
    echo "bootstrap: cv2 imports (OpenCV $(.venv/bin/python -c 'import cv2; print(cv2.__version__)'))"
else
    echo "bootstrap: WARNING: cv2 does not import; the OCR tests will fail" >&2
fi
.venv/bin/python - <<'PY'
import flask, psycopg2, pytest, pyzipper, pgserver, bandit  # noqa: F401
print("bootstrap: imports ok: flask, psycopg2, pytest, pyzipper, pgserver, bandit")
PY
echo "bootstrap: ruff $(.venv/bin/ruff --version 2>&1 | awk '{print $2}')"

echo
echo "bootstrap: done."
if [ ${#did[@]} -gt 0 ]; then
    echo "bootstrap: this run: ${did[*]}"
else
    echo "bootstrap: this run changed nothing (already up to date)"
fi
echo "bootstrap: next: bash tools/dev/run_tests.sh tests/unit 4"
