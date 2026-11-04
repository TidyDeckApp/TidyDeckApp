# -*- coding: utf-8 -*-
"""Sensibilisation DPI et instance unique.

Deux points de diffusion :

* ÉCRAN DENSE — Sur un portable réglé à 125 ou 150 %, un process non déclaré
  « DPI-aware » est dessiné en 96 points par pouce PUIS étiré par Windows :
  tout parait flou, les textes surtout. On le déclare avant de créer la fenêtre
  Tk ; Tk lit alors le vrai DPI et rend chaque pixel (plus de flou d'étirement).

* INSTANCE UNIQUE — Deux TidyDeck ouverts en meme temps = deux rappels qui
  sonnent, une quarantaine manipulée par deux mains, deux nettoyages qui peuvent
  se marcher dessus. Un mutex Windows nomme bloque la seconde ouverture.
"""
import ctypes
from ctypes import wintypes

from Shared.Utils.common import IS_WINDOWS
from Shared.Utils.lang import T

_MUTEX = "Local\\TidyDeck_Instance_Unique"
NOM_FENETRE = "TidyDeck"


_actif = None


def activer_dpi():
    """À appeler AVANT `tk.Tk()`. Renvoie un libelle pour le journal.

    Niveau 1 = « system aware », le bon choix pour Tkinter 8.6, qui ne sait pas
    suivre un changement de moniteur a chaud (niveau 2 = fenetre minuscule sur un
    ecran annexe plus dense). Idempotent : le systeme refuse un second reglage."""
    global _actif
    if _actif is not None:
        return _actif
    if not IS_WINDOWS:
        _actif = "non-Windows"
        return _actif
    try:
        if ctypes.windll.shcore.SetProcessDpiAwareness(1) == 0:      # S_OK
            _actif = "system-aware (shcore)"
            return _actif
    except (OSError, AttributeError):
        pass
    try:
        if ctypes.windll.user32.SetProcessDPIAware():
            _actif = "dpi-aware (user32)"
            return _actif
    except (OSError, AttributeError):
        pass
    _actif = T("non déclaré")
    return _actif


def dpi_systeme():
    """DPI reel du systeme (96 = 100 %, 120 = 125 %, 144 = 150 %)."""
    if not IS_WINDOWS:
        return 96
    try:
        return int(ctypes.windll.user32.GetDpiForSystem())
    except (OSError, AttributeError):
        return 96


def deja_ouvert():
    """Vrai si un autre TidyDeck tourne deja. Le handle est garde vivant par le
    module : le jour ou le processus se termine, le nom se libere."""
    if not IS_WINDOWS:
        return False
    global _handle
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    h = k32.CreateMutexW(None, False, _MUTEX)
    if not h:
        return False            # on ne bloque pas le logiciel pour si peu
    _handle = h
    return ctypes.get_last_error() == 183     # ERROR_ALREADY_EXISTS


_handle = None


def liberer():
    """Ferme le mutex (test isolation). Inutile en usage normal : le process meurt."""
    global _handle
    if IS_WINDOWS and _handle:
        try:
            ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(_handle))
        except Exception:
            pass
    _handle = None


def attendre_instance_libre(duree):
    """Attend qu'une autre instance rende le mutex, puis le prend pour nous.

    Cas réel : relance « en administrateur » — l'enfant élevé démarre souvent
    avant que le parent (non élevé) ait fermé sa fenêtre et rendu son mutex.
    Sans patience, l'enfant se croirait « déjà ouvert » et quitterait sans bruit.
    Vrai si le mutex est à nous à la fin ; Faux après expiration du délai."""
    if not IS_WINDOWS:
        return True
    import time as _time
    liberer()                    # notre propre handle doit rendre le nom d'abord
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fin = _time.monotonic() + duree
    while True:
        h = k32.CreateMutexW(None, False, _MUTEX)
        if h and ctypes.get_last_error() != 183:   # ERROR_ALREADY_EXISTS
            global _handle
            _handle = h
            return True
        if h:
            try:
                k32.CloseHandle(wintypes.HANDLE(h))
            except Exception:
                pass
        if _time.monotonic() >= fin:
            return False
        _time.sleep(0.25)


def ramener_existant():
    """Met la premiere fenetre TidyDeck au premier plan. Renvoie True si trouve."""
    if not IS_WINDOWS:
        return False
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, None)
    trouve = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def chaque(h, _p):
        if not user32.IsWindowVisible(h):
            return True
        n = user32.GetWindowTextLengthW(h)
        if n <= 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(h, buf, n + 1)
        if buf.value.startswith(NOM_FENETRE):
            trouve.append(h)
            return False
        return True

    user32.EnumWindows(chaque, 0)
    if not trouve:
        return False
    h = trouve[0]
    if user32.IsIconic(h):
        user32.ShowWindow(h, 9)          # SW_RESTORE
    user32.SetForegroundWindow(h)
    return True
