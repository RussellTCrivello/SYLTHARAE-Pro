"""The lock has to yield a *working* OpenCV, and say so when it does not.

Round 22 spent a round and a half blaming the code for an environment that
looked right: `requirements.lock` listed both `opencv-python` and
`opencv-python-headless`, both unpack into the same `cv2/` directory, the GUI
wheel was written last, and `import cv2` raised `ImportError: libGL.so.1`. The
package set matched the lock byte for byte while 31 ids failed and 84 skipped.

So the environment tool is now asked two questions, not one:

* does the installed set hash to the lock? (it always did)
* does `import cv2` work? (it did not, and nothing noticed)

These tests pin the second question, including the part that matters most: a
lock whose OpenCV cannot load must make `--check` fail loudly rather than print a
report and exit 0.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.audit import env_lock  # noqa: E402

UNUSABLE = {"usable": False, "owners": ["opencv-python", "opencv-python-headless"],
            "error": "ImportError: libGL.so.1: cannot open shared object file"}
USABLE = {"usable": True, "owners": ["opencv-python-headless"], "version": "5.0.0"}


@pytest.fixture
def lock_with_opencv(tmp_path, monkeypatch):
    lock = tmp_path / "requirements.lock"
    lock.write_text("flask==3.1.3\nopencv-python-headless==5.0.0.93\n", encoding="utf-8")
    monkeypatch.setattr(env_lock, "LOCK", lock)
    return lock


def _report(**overrides):
    base = {"python": "3.11.2", "executable": "/x/python", "packages": 2,
            "set_hash": "abc", "lock_hash": "abc", "lock_present": True,
            "match": True, "label": None, "engines": {},
            "missing_from_this_env": [], "not_in_the_lock": [],
            "opencv": dict(USABLE)}
    base.update(overrides)
    return base


def test_a_lock_whose_opencv_cannot_load_fails_the_check(lock_with_opencv, monkeypatch):
    """The regression that cost a round: match == True and cv2 broken."""
    monkeypatch.setattr(env_lock, "report", lambda label=None: _report(opencv=dict(UNUSABLE)))
    exit_code = env_lock.main(["--check"])
    assert exit_code == 3, ("a lock whose OpenCV cannot load must fail the check, "
                            f"not report success (exit was {exit_code})")


def test_a_lock_with_working_opencv_passes_the_check(lock_with_opencv, monkeypatch):
    monkeypatch.setattr(env_lock, "report", lambda label=None: _report())
    assert env_lock.main(["--check"]) == 0


def test_a_lock_without_opencv_is_not_asked_the_question(tmp_path, monkeypatch):
    lock = tmp_path / "requirements.lock"
    lock.write_text("flask==3.1.3\n", encoding="utf-8")
    monkeypatch.setattr(env_lock, "LOCK", lock)
    monkeypatch.setattr(env_lock, "report", lambda label=None: _report(opencv=dict(UNUSABLE)))
    assert env_lock.main(["--check"]) == 0, (
        "a lock that ships no OpenCV cannot be refused for having no OpenCV")


def test_the_report_says_which_distributions_own_cv2():
    """Two owners are the mechanism, so the report has to name them."""
    state = env_lock.opencv_state()
    assert set(state) >= {"usable", "owners"}
    assert isinstance(state["owners"], list)
    if not state["usable"]:
        assert state.get("error"), "an unusable cv2 has to say why"


def test_only_one_distribution_owns_cv2_in_this_environment():
    """Whatever this environment is, the fighting-over-cv2/ state is refused.

    In the locked environment this asserts the headless wheel is the sole owner.
    Elsewhere it is skipped rather than failed: the point of the test is the
    invariant, and the lock check above is what enforces it where it applies.
    """
    state = env_lock.opencv_state()
    if not state["usable"]:
        pytest.skip(f"cv2 is not usable in this interpreter: {state.get('error')}")
    assert state["owners"] == ["opencv-python-headless"], (
        "cv2/ is provided by " + (", ".join(state["owners"]) or "no distribution")
        + "; exactly one distribution may own it, and the GUI build needs libGL")


def test_the_rebuild_tool_installs_without_resolving_dependencies():
    """`--no-deps` is the fix, not a detail: resolution reintroduces the GUI build."""
    source = (pathlib.Path(__file__).resolve().parents[2]
              / "tools" / "audit" / "rebuild_lock_env.py").read_text(encoding="utf-8")
    assert '"--no-deps"' in source
    assert "opencv-python-headless" in source
    lock = (pathlib.Path(__file__).resolve().parents[2] / "requirements.lock").read_text(
        encoding="utf-8")
    live = [line for line in lock.splitlines()
            if line.strip() and not line.startswith("#")]
    assert "opencv-python==5.0.0.93" not in live, (
        "the GUI OpenCV build is back in the lock; it owns cv2/ and needs libGL.so.1")
    assert "opencv-python-headless==5.0.0.93" in live


# --------------------------------------------------------------------------- #
# The lock's *text*, checked before anything is built from it
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("distribution", ["opencv-python", "opencv-contrib-python"])
def test_the_lock_contains_no_gui_opencv_distribution(distribution):
    """Item B.1: a GUI build in the lock is refused on sight.

    This is the check that would have caught the defect before a venv was
    built: the lock is read as text, and a distribution that needs libGL is a
    problem regardless of what happens to be installed anywhere.
    """
    lines = (pathlib.Path(__file__).resolve().parents[2] / "requirements.lock").read_text(
        encoding="utf-8").splitlines()
    named = [line for line in lines
             if line.split("==")[0].strip().lower() == distribution]
    assert named == [], (
        f"{distribution} is a GUI OpenCV build: it needs libGL.so.1, so a "
        "headless host installs it and then cannot import cv2")


def test_the_lock_names_exactly_one_distribution_that_owns_cv2():
    lines = (pathlib.Path(__file__).resolve().parents[2] / "requirements.lock").read_text(
        encoding="utf-8").splitlines()
    owners = [line.split("==")[0].strip().lower() for line in lines
              if line.split("==")[0].strip().lower() in env_lock.CV2_OWNERS]
    assert owners == ["opencv-python-headless"], owners


def test_a_gui_lock_is_refused_before_it_is_built(tmp_path, monkeypatch):
    """`rebuild_lock_env.py` refuses the lock text, not only the result."""
    from tools.audit import rebuild_lock_env

    lock = tmp_path / "requirements.lock"
    lock.write_text("flask==3.1.3\nopencv-python==5.0.0.93\n"
                    "opencv-python-headless==5.0.0.93\n", encoding="utf-8")
    monkeypatch.setattr(rebuild_lock_env, "LOCK", lock)
    monkeypatch.setattr(env_lock, "LOCK", lock)
    built = []
    monkeypatch.setattr(rebuild_lock_env.subprocess, "run",
                        lambda *a, **k: built.append(a) or pytest.fail(
                            "the tool built an environment from a lock it should "
                            "have refused"))
    assert rebuild_lock_env.main(["--venv", str(tmp_path / "venv")]) == 3
    assert built == [], "nothing may be installed from a refused lock"


def test_a_gui_lock_makes_the_check_fail_loudly(tmp_path, monkeypatch, capsys):
    """Item B.3: the failure is an exit code and a sentence, not a warning."""
    lock = tmp_path / "requirements.lock"
    lock.write_text("flask==3.1.3\nopencv-python==5.0.0.93\n", encoding="utf-8")
    monkeypatch.setattr(env_lock, "LOCK", lock)
    monkeypatch.setattr(env_lock, "report", lambda label=None: _report())
    assert env_lock.main(["--check"]) == 3
    message = capsys.readouterr().err
    assert "REFUSING" in message
    assert "libGL" in message


def test_the_lock_problems_are_described_for_the_two_known_defects():
    gui = env_lock.lock_cv2_problems(["opencv-python==5.0.0.93"])
    both = env_lock.lock_cv2_problems(
        ["opencv-python==5.0.0.93", "opencv-python-headless==5.0.0.93"])
    headless = env_lock.lock_cv2_problems(["opencv-python-headless==5.0.0.93"])
    assert len(gui) == 1 and "libGL" in gui[0]
    assert len(both) == 2 and any("own cv2/" in problem for problem in both)
    assert headless == []


def test_the_lock_header_forbids_the_plain_install():
    """Item B.3: the file itself says the unsupported command is unsupported."""
    lock = (pathlib.Path(__file__).resolve().parents[2] / "requirements.lock").read_text(
        encoding="utf-8")
    assert "INSTALL WITH --no-deps" in lock
    assert "--no-deps" in lock
    assert "plain `pip install -r`" in lock or "plain pip install -r" in lock


def test_the_setup_docs_state_the_same_rule():
    """A rule in the lock's header is no use to someone following the guide."""
    root = pathlib.Path(__file__).resolve().parents[2]
    texts = {}
    for path in (root / "docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "requirements.lock" in text:
            texts[path.relative_to(root)] = text
    assert texts, "no document mentions requirements.lock"
    offenders = [name for name, text in texts.items()
                 if "--no-deps" not in text]
    assert not offenders, (
        "these documents tell a reader to install the lock without saying it "
        f"must be installed with --no-deps: {offenders}")
