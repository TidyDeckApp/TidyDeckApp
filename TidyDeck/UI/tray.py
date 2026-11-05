# -*- coding: utf-8 -*-
"""Icône système (zone de notification, à côté de l'horloge) — pur ctypes, zéro dépendance.

Option « Réduire à côté de l'horloge » : la fenêtre se masque, TidyDeck reste
discret près de l'horloge ; double-clic sur l'icône = retour, clic droit = menu
 Ouvrir / Quitter. Un thread dédié possède une fenêtre « message-only » qui
reçoit les messages de l'icône ; la fenêtre Tk ne fait que lire une file
(thread-safe) — tkinter ne doit jamais être appelé depuis un autre thread.
"""
import ctypes
import queue
import threading

from Shared.Utils.common import IS_WINDOWS, chemin_asset

WM_APP = 0x8000
WM_TRAY = WM_APP + 1
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_LBUTTONDBLCLK = 0x0203
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
NIM_ADD, NIM_DELETE = 0, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x1, 0x2, 0x4
TPM_RETURNCMD = 0x0100
LR_LOADFROMFILE = 0x0010
IMAGE_ICON = 1
IDI_APPLICATION = ctypes.c_wchar_p(32512)

SUPPORT = IS_WINDOWS

_events: "queue.Queue[str]" = queue.Queue()
_state = {"thread": None, "hwnd": None, "ready": None, "ok": False, "proc": None}

if IS_WINDOWS:
    _user32 = ctypes.windll.user32
    _shell32 = ctypes.windll.shell32
    _kernel32 = ctypes.windll.kernel32

    _kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    _kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    _user32.RegisterClassExW.argtypes = [ctypes.c_void_p]
    _user32.CreateWindowExW.restype = ctypes.c_void_p
    _user32.CreateWindowExW.argtypes = [ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint,
                                        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    _user32.DefWindowProcW.restype = ctypes.c_ssize_t
    _user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    _user32.GetMessageW.restype = ctypes.c_int
    _user32.GetMessageW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
    _user32.TranslateMessage.argtypes = [ctypes.c_void_p]
    _user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
    _user32.PostQuitMessage.argtypes = [ctypes.c_int]
    _user32.DestroyWindow.argtypes = [ctypes.c_void_p]
    _user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    _user32.LoadImageW.restype = ctypes.c_void_p
    _user32.LoadImageW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    _user32.LoadIconW.restype = ctypes.c_void_p
    _user32.LoadIconW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    _user32.CreatePopupMenu.restype = ctypes.c_void_p
    _user32.AppendMenuW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_wchar_p]
    _user32.TrackPopupMenu.restype = ctypes.c_int
    _user32.TrackPopupMenu.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
    _user32.DestroyMenu.argtypes = [ctypes.c_void_p]
    _user32.GetCursorPos.argtypes = [ctypes.c_void_p]
    _user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    _shell32.Shell_NotifyIconW.restype = ctypes.c_int
    _shell32.Shell_NotifyIconW.argtypes = [ctypes.c_uint, ctypes.c_void_p]

    class _POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class _MSG(ctypes.Structure):
        _fields_ = [("hwnd", ctypes.c_void_p), ("message", ctypes.c_uint),
                    ("wParam", ctypes.c_size_t), ("lParam", ctypes.c_ssize_t),
                    ("time", ctypes.c_uint), ("ptx", ctypes.c_long), ("pty", ctypes.c_long)]

    class _NID(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint32), ("hWnd", ctypes.c_void_p), ("uID", ctypes.c_uint32),
                    ("uFlags", ctypes.c_uint32), ("uCallbackMessage", ctypes.c_uint32),
                    ("hIcon", ctypes.c_void_p), ("szTip", ctypes.c_wchar * 128),
                    ("dwState", ctypes.c_uint32), ("dwStateMask", ctypes.c_uint32),
                    ("szInfo", ctypes.c_wchar * 256), ("uVersion", ctypes.c_uint32),
                    ("szInfoTitle", ctypes.c_wchar * 64), ("dwInfoFlags", ctypes.c_uint32),
                    ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", ctypes.c_void_p)]

    class _WNDCLASSEXW(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint32), ("style", ctypes.c_uint32),
                    ("lpfnWndProc", ctypes.c_void_p), ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int), ("hInstance", ctypes.c_void_p),
                    ("hIcon", ctypes.c_void_p), ("hCursor", ctypes.c_void_p),
                    ("hbrBackground", ctypes.c_void_p), ("lpszMenuName", ctypes.c_wchar_p),
                    ("lpszClassName", ctypes.c_wchar_p), ("hIconSm", ctypes.c_void_p)]


def _nim(hwnd, op):
    nid = _NID()
    nid.cbSize = ctypes.sizeof(_NID)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAY
    nid.hIcon = _state.get("icon") or 0
    nid.szTip = "TidyDeck"
    return _shell32.Shell_NotifyIconW(op, ctypes.byref(nid))


def _thread_loop(menu_open, menu_quit):
    hinst = _kernel32.GetModuleHandleW(None)

    def wnd_proc(h, msg, wparam, lparam):
        if msg == WM_TRAY:
            evt = int(lparam) & 0xFFFF
            if evt in (WM_LBUTTONDBLCLK, WM_LBUTTONUP):
                _events.put("restore")
            elif evt == WM_RBUTTONUP and menu_open:
                menu = _user32.CreatePopupMenu()
                _user32.AppendMenuW(menu, 0, 1, menu_open)
                if menu_quit:
                    _user32.AppendMenuW(menu, 0, 2, menu_quit)
                pt = _POINT()
                _user32.GetCursorPos(ctypes.byref(pt))
                _user32.SetForegroundWindow(h)
                cmd = _user32.TrackPopupMenu(menu, TPM_RETURNCMD, pt.x, pt.y, 0, h, None)
                _user32.DestroyMenu(menu)
                if cmd == 1:
                    _events.put("restore")
                elif cmd == 2:
                    _events.put("quit")
            return 0
        if msg == WM_CLOSE:
            _nim(h, NIM_DELETE)
            _user32.DestroyWindow(h)
            return 0
        if msg == WM_DESTROY:
            _user32.PostQuitMessage(0)
            return 0
        return _user32.DefWindowProcW(h, msg, wparam, lparam)

    proc = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint,
                              ctypes.c_size_t, ctypes.c_ssize_t)(wnd_proc)
    _state["proc"] = proc          # reference vitale : sans elle, appel sur objet libere
    wc = _WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(wc)
    wc.lpfnWndProc = ctypes.cast(proc, ctypes.c_void_p)
    wc.hInstance = hinst
    wc.lpszClassName = "TidyDeckTray"
    _user32.RegisterClassExW(ctypes.byref(wc))     # 141 = deja enregistre : tant mieux
    hwnd = _user32.CreateWindowExW(0, "TidyDeckTray", "TidyDeck", 0,
                                   0, 0, 0, 0, ctypes.c_void_p(-3), None, hinst, None)
    _state["hwnd"] = hwnd
    icon = 0
    try:
        icon = _user32.LoadImageW(hinst, chemin_asset("tidydeck.ico"), IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
    except Exception:
        icon = 0
    _state["icon"] = icon or _user32.LoadIconW(None, IDI_APPLICATION)
    _state["ok"] = bool(hwnd) and bool(_nim(hwnd, NIM_ADD))
    _state["ready"].set()
    m = _MSG()
    while _user32.GetMessageW(ctypes.byref(m), None, 0, 0) > 0:
        _user32.TranslateMessage(ctypes.byref(m))
        _user32.DispatchMessageW(ctypes.byref(m))
    _state["hwnd"] = None
    _state["thread"] = None


def visible():
    t = _state["thread"]
    return bool(t and t.is_alive() and _state["hwnd"])


def afficher(menu_open="Open TidyDeck", menu_quit="Quit TidyDeck"):
    """Affiche l'icône ; True si l'icône est bien en place (False = repli tâche)."""
    if not SUPPORT:
        return False
    if visible():
        return True
    _state["ready"] = threading.Event()
    _state["ok"] = False
    t = threading.Thread(target=_thread_loop, args=(menu_open, menu_quit),
                         daemon=True, name="TidyDeckTray")
    _state["thread"] = t
    t.start()
    _state["ready"].wait(3.0)
    if not _state["ok"]:
        retirer()
        return False
    return True


def retirer():
    if _state["hwnd"]:
        _user32.PostMessageW(ctypes.c_void_p(_state["hwnd"]), WM_CLOSE, 0, 0)


def events():
    """Vide la file d'événements icône (à appeler depuis le thread Tk)."""
    out = []
    while True:
        try:
            out.append(_events.get_nowait())
        except queue.Empty:
            break
    return out
