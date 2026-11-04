"""Petits appels Windows pour les rappels : état « ne pas déranger » et clignotement de la barre des tâches."""
import ctypes
from ctypes import wintypes
from Shared.Utils.common import IS_WINDOWS

# SHQueryUserNotificationState : 1 absent/écran verrouillé, 2 appli plein écran, 3 jeu Direct3D plein écran,
# 4 mode présentation, 5 notifications acceptées, 6 heures calmes (Assistant de concentration), 7 appli UWP
BUSY_STATES = {1, 2, 3, 4, 6}


def user_state():
    if not IS_WINDOWS:
        return None
    try:
        s = ctypes.c_int()
        return s.value if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(s)) == 0 else None
    except Exception:
        return None


def fullscreen_busy():
    return user_state() in BUSY_STATES


class _FLASHWINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("hwnd", wintypes.HWND), ("dwFlags", wintypes.DWORD),
                ("uCount", wintypes.UINT), ("dwTimeout", wintypes.DWORD)]


def flash_taskbar(root, count=4):
    """Fait clignoter doucement le bouton TidyDeck dans la barre des tâches (orange par défaut). Aucun son, aucune fenêtre."""
    if not IS_WINDOWS:
        return False
    try:
        hwnd = int(root.wm_frame(), 16)
        fi = _FLASHWINFO(ctypes.sizeof(_FLASHWINFO), hwnd, 0x2 | 0xC, count, 0)   # TRAY | TIMERNOFG
        return bool(ctypes.windll.user32.FlashWindowEx(ctypes.byref(fi)))
    except Exception:
        return False
