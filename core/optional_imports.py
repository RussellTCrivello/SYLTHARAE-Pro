"""Optional native imports that cannot damage the interpreter when they fail.

OpenCV is the reason this module exists. Its loader inserts its own package
directory into ``sys.path`` **before** it tries to load the compiled binaries,
and restores the path only when the load succeeds::

    p = os.path.join(os.path.dirname(__file__))
    if p not in sys.path:                       # inserted unconditionally
        sys.path.insert(1, p)
    ...
    sys.path = save_sys_path                    # only reached on success

So on a machine where the binaries cannot load - ``libGL.so.1`` missing for the
GUI wheel, a broken install, a headless box - ``import cv2`` fails **and leaves
the directory on ``sys.path``**. From that point on, any bare ``from <name>
import ...`` in the process may resolve to a file inside ``cv2/`` instead of the
one intended; ``cv2/version.py`` shadowing the project's ``version.py`` cost 222
tests in two seeded orders before it was found.

``import_opencv()`` imports OpenCV and, if the import fails, puts the
interpreter back exactly as it was found, then answers ``None``. A caller is
never handed a half-imported module, and the next module in the same process
inherits nothing.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import List, Optional

__all__ = ["import_opencv", "restore_after_failed_import"]

#: Names OpenCV sets on the interpreter itself, outside ``sys.path`` and
#: ``sys.modules``. Restored too, so a later import gets a clean attempt.
_INTERPRETER_ATTRIBUTES = ("OpenCV_LOADER",)


def restore_after_failed_import(before_path: List[str],
                                before_modules: dict) -> None:
    """Undo everything a failed optional import may have left behind.

    ``before_path`` is a copy of ``sys.path`` taken *before* the import and
    ``before_modules`` a set of the module names that existed then; anything
    named ``<package>`` or ``<package>.<sub>`` that appeared is dropped, and any
    module the failed import evicted is not restored (Python does not keep it).
    """
    sys.path[:] = before_path
    for name in [m for m in sys.modules if m not in before_modules]:
        # Only the failed package's own leftovers: a module that another thread
        # imported in the meantime is not ours to remove.
        if name.split(".")[0] == "cv2":
            del sys.modules[name]
    for attribute in _INTERPRETER_ATTRIBUTES:
        if hasattr(sys, attribute):
            try:
                # Only OpenCV's own marker is removed, and only here.
                delattr(sys, attribute)
            except AttributeError:  # pragma: no cover - raced away
                pass


def import_opencv() -> Optional[ModuleType]:
    """OpenCV, or ``None`` if it cannot be imported here.

    ``None`` is a supported answer, not an error: OCR and video reading are
    optional features, and a machine without a usable OpenCV still reads
    documents. What is *not* acceptable is returning normally and leaving the
    interpreter changed, which is what a bare ``import cv2`` does.
    """
    before_path = list(sys.path)
    before_modules = set(sys.modules)
    try:
        import cv2
    except Exception:  # noqa: BLE001 - ImportError, OSError and its friends
        restore_after_failed_import(before_path, before_modules)
        return None
    return cv2
