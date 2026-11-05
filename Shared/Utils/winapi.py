"""Petits appels Windows via ctypes (corbeille, mémoire, uptime)."""
import ctypes
import datetime
from ctypes import wintypes
from Shared.Utils.common import IS_WINDOWS
from Shared.Utils.lang import T


class _RBINFO(ctypes.Structure):
    # PAQUAGE NATUREL OBLIGATOIRE : SHQUERYRBINFO aligne les __int64 sur 8 octets
    # (cbSize=24). Avec _pack_=1 (20), Windows repondait E_INVALIDARG a chaque appel :
    # la Corbeille affichait 0 partout, meme sur un seul lecteur (bug #41).
    _fields_ = [("cbSize", wintypes.DWORD), ("i64Size", ctypes.c_longlong),
                ("i64NumItems", ctypes.c_longlong)]


DRIVE_FIXED = 3
ECHECS_CORBEILLE = []  # lecteurs ignorés au dernier appel (piste pour le debug)


def _shell32():
    return ctypes.windll.shell32


def _fixed_drives():
    """Racines des lecteurs fixes (« C:\\ ») ; liste vide si rien n'est lisible."""
    out = []
    try:
        k = ctypes.windll.kernel32
        mask = k.GetLogicalDrives()
        for i in range(26):
            if mask & (1 << i):
                root = "%s:\\" % chr(65 + i)
                try:
                    if k.GetDriveTypeW(root) == DRIVE_FIXED:
                        out.append(root)
                except Exception:
                    continue
    except Exception:
        pass
    return out


def _debug_note(msg):
    """Ligne de debug dans %LOCALAPPDATA%\\TidyDeck\\debug.log ; jamais bloquant."""
    try:
        from Shared.Utils.common import data_dir
        with open(data_dir() / "debug.log", "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    except Exception:
        pass


def _query_global():
    """Dernier repli si aucun lecteur fixe n'a pu être énuméré : l'ancien appel
    (le lecteur courant seulement) — mieux que rien, mais chiffres incomplets."""
    try:
        info = _RBINFO()
        info.cbSize = ctypes.sizeof(_RBINFO)
        if _shell32().SHQueryRecycleBinW(None, ctypes.pointer(info)) == 0:
            return max(0, int(info.i64Size)), max(0, int(info.i64NumItems))
    except Exception:
        pass
    return 0, 0


def recycle_bin_info():
    """(taille en octets, nb d'éléments) de la Corbeille, sommée lecteur par lecteur.

    L'ancien appel SHQueryRecycleBinW(None) ne comptait que le lecteur courant :
    sur les machines à plusieurs disques les chiffres affichés étaient faux.
    On interroge ici chaque lecteur fixe et on somme. Un lecteur en échec est
    ignoré, noté dans ECHECS_CORBEILLE et dans le journal debug : rien d'autre
    ne s'arrête à cause de lui. Pas de cache : chaque analyse redemande tout."""
    global ECHECS_CORBEILLE
    ECHECS_CORBEILLE = []
    if not IS_WINDOWS:
        return 0, 0
    drives = _fixed_drives()
    if not drives:
        return _query_global()
    total_size = total_items = 0
    for root in drives:
        try:
            info = _RBINFO()
            info.cbSize = ctypes.sizeof(_RBINFO)
            code = _shell32().SHQueryRecycleBinW(root, ctypes.pointer(info))
            if code != 0:
                raise OSError(f"code {code}")
            total_size += max(0, int(info.i64Size))
            total_items += max(0, int(info.i64NumItems))
        except Exception as e:
            ECHECS_CORBEILLE.append(root)
            _debug_note(T("corbeille : lecteur {v0} ignoré ({v1})").format(v0=root, v1=e))
    return total_size, total_items


def empty_recycle_bin() -> bool:
    if not IS_WINDOWS:
        return False
    try:  # NOCONFIRMATION | NOPROGRESSUI | NOSOUND
        return ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7) == 0
    except Exception:
        return False


class _MEM(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def memory_status():
    """(RAM totale, RAM disponible) en octets, ou (0, 0)."""
    if not IS_WINDOWS:
        return 0, 0
    try:
        m = _MEM()
        m.dwLength = ctypes.sizeof(_MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ullTotalPhys), int(m.ullAvailPhys)
    except Exception:
        return 0, 0


def uptime_days() -> float:
    if not IS_WINDOWS:
        return 0.0
    try:
        k = ctypes.windll.kernel32
        k.GetTickCount64.restype = ctypes.c_ulonglong
        return k.GetTickCount64() / 1000 / 86400
    except Exception:
        return 0.0
