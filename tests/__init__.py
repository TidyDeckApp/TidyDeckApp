import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _has_display():
    if sys.platform == "win32":
        return True
    return bool(os.environ.get("DISPLAY"))


HAS_DISPLAY = _has_display()
