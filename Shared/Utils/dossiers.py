# -*- coding: utf-8 -*-
"""Dossiers connus : trouver le chemin reel au lieu de deviner un nom.

Ce que l'Explorateur affiche n'est pas ce qu'il y a sur le disque : « Telechargements »
est en realite C:\\Users\\moi\\Downloads. S'y ajoutent trois choses qui arrivent pour
de vrai : le dossier est renomme, deplace sur un autre disque, ou bascule sur
OneDrive (et « Documents » devient C:\\Users\\moi\\OneDrive\\Documents). Comparer des
noms en dur rate alors le dossier sans jamais le dire — la page reste vide.

SHGetKnownFolderPath rend le chemin reel, redirection comprise : on donne le GUID
du dossier, Windows repond. Les noms en dur ne restent qu'un repli, pour les deux
langues que TidyDeck affiche, quand l'appel est indisponible.

Point important pour les dossiers bascules sur OneDrive : `trouver()` peut rendre
une racine synchronisee. Les scanneurs doivent donc continuer a ignorer les
placeholders (voir cloud.py) — ce module ne telecharge jamais rien.
"""
import ctypes
import os
import threading
import uuid
from pathlib import Path

from Shared.Utils.common import IS_WINDOWS

# GUID officiels (Knownfolders.h). Un GUID, pas un nom : c'est ce qui rend le
# resultat independant de la langue d'installation.
IDS = {
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
    "music": "{4BD8D571-6D19-48D3-BE97-422220080E43}",
    "saved_games": "{4C5C32FF-BB9D-43b0-B5B4-2D72E54EAAA4}",
    "onedrive": "{A52BBA46-E9E1-435f-B3D9-28DAA648C0F6}",
    "appdata": "{3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}",
    "localappdata": "{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}",
    # Les deux dossiers « Demarrage » : leur chemin affiche est traduit mais le
    # chemin reel peut aussi etre detourne (GPO, profil itinerant).
    "startup": "{B97D20BB-F46A-4C97-BA10-5E3608430854}",
    "common_startup": "{82A5EA35-D9CD-47C5-9629-E15D2F714E6E}",
}

# Repli : les deux langues que TidyDeck affiche, sous le profil. Utilise seulement
# quand l'appel repond mal — au-dela de ces noms, c'est l'API qui repond, et elle
# connait toutes les langues de Windows.
NOMS = {
    "downloads": ("Downloads", "Téléchargements"),
    "desktop": ("Desktop", "Bureau"),
    "documents": ("Documents", "Mes Documents"),
    "pictures": ("Pictures", "Images"),
    "videos": ("Videos", "Vidéos"),
    "music": ("Music", "Musique"),
    "saved_games": ("Saved Games", "Parties sauvegardees"),
}

# Les dossiers que TidyDeck est susceptible de scanner / proposer.
CLES_UTILISEES = ("downloads", "desktop", "documents", "pictures", "videos", "music")

COM_MODE = 0x2  # COINIT_APARTMENTTHREADED
RPC_E_CHANGED_MODE = -2147418106  # deja initialise dans un autre mode : l'appel marche

_shell32 = _ole32 = None
if IS_WINDOWS:
    try:
        _shell32 = ctypes.windll.shell32
        _ole32 = ctypes.windll.ole32
        _shell32.SHGetKnownFolderPath.restype = ctypes.c_long
        _shell32.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                                 ctypes.c_void_p,
                                                 ctypes.POINTER(ctypes.c_wchar_p)]
        _ole32.CoTaskMemFree.restype = None
        _ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    except Exception:
        _shell32 = _ole32 = None

_local = threading.local()
_cache = {}
_lock = threading.Lock()


def _com_initialise():
    """COM doit etre initialise dans le thread qui appelle (exigence Microsoft).

    Les scans tournent dans des threads separees : on initialise donc une fois par
    thread et on accepte qu'il le soit deja, y compris dans un autre mode."""
    if getattr(_local, "com", None) is not None:
        return _local.com
    ok = False
    if _ole32 is not None:
        try:
            hr = _ole32.CoInitializeEx(None, COM_MODE)
            ok = hr in (0, 1, RPC_E_CHANGED_MODE)
        except Exception:
            ok = False
    _local.com = ok
    return ok


def _api(cle):
    """Le chemin rendu par Windows. None si l'appel est indisponible ou echoue."""
    guid = IDS.get(str(cle).lower())
    if not guid or _shell32 is None or not _com_initialise():
        return None
    try:
        raw = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(guid).bytes_le)
        sortie = ctypes.c_wchar_p()
        hr = _shell32.SHGetKnownFolderPath(raw, 0, None, ctypes.byref(sortie))
    except Exception:
        return None
    if hr != 0 or not sortie.value:
        return None
    chemin = sortie.value.strip()
    try:
        # La chaine est allouee par Windows : a rendre, sinon fuite a chaque appel.
        _ole32.CoTaskMemFree(ctypes.cast(sortie, ctypes.c_void_p))
    except Exception:
        from Shared.Utils import depannage
        depannage.noter("Shared/Utils/dossiers.py:118")
    return chemin or None


def connu(cle):
    """Chemin reel du dossier connu, meme deplace, meme dans une autre langue.

    Ne verifie pas qu'il existe (un dossier peut etre supprime ; l'appelant decide).
    Resultat mis en cache : la redirection ne change pas pendant une session.
    """
    c = str(cle).lower()
    with _lock:
        if c in _cache:
            return _cache[c]
    res = _api(c)
    with _lock:
        _cache[c] = res
    return res


def trouver(cle):
    """Path du dossier, dans sa vraie langue et son vrai endroit. None si introuvable."""
    p = connu(cle)
    if p:
        try:
            if os.path.isdir(p):
                return Path(p)
        except OSError:
            pass
    for nom in NOMS.get(str(cle).lower(), ()):
        q = Path.home() / nom
        try:
            if q.is_dir():
                return q
        except OSError:
            continue
    return None


def tous(cles):
    """Les dossiers existants, dans l'ordre demande, sans doublon.

    Le deduplage est insensible a la casse : un meme dossier rendu par deux cles
    differentes (redirection OneDrive) ne doit pas etre scanne deux fois."""
    vus, out = set(), []
    for c in cles:
        p = trouver(c)
        if p is None:
            continue
        k = os.path.normcase(str(p))
        if k in vus:
            continue
        vus.add(k)
        out.append(p)
    return out


def nom(cle):
    """Nom reel du dossier tel que Windows le nomme sur CETTE machine."""
    p = connu(cle)
    return os.path.basename(p.rstrip("\\/")) if p else None


def vider_cache():
    """Oublie les resultats (tests, ou apres une redirection en cours de session)."""
    with _lock:
        _cache.clear()
