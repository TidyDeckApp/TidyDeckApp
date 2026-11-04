"""Met le projet a l'import (les tests sont dans <projet>/tests)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def has_display():
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.destroy()
        return True
    except Exception:
        return False


HAS_DISPLAY = has_display()
