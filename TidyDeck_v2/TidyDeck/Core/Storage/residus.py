"""Détection des résidus d'applications désinstallées (Phase 0 : LECTURE SEULE).

Règle (cahier résidus v1, corrigée) : un dossier n'est proposé que si AUCUN
logiciel installé ne lui correspond — nom, éditeur ou dossier d'installation,
dans le doute on ne propose pas — ET qu'il est inactif depuis longtemps et
assez gros pour mériter l'attention. Une correspondance avec un logiciel
installé = jamais proposé.

Ce module ne supprime rien, ne déplace rien, n'écrit nulle part, ne touche pas
au registre, n'utilise ni réseau, ni PowerShell, ni taskkill. La mise à l'écart
(annulable) n'arrivera qu'en Phase 1, après M1-M6 sur au moins 5 machines,
sans aucun faux positif à confiance « Élevée ».

Le module accepte une fausse arborescence (racines fabriquées par les tests) :
toutes les fonctions prennent des listes de racines et une liste d'installés
explicite quand on le leur demande.
"""
import os
import re
import time
from datetime import datetime

from Shared.Utils.common import human_size, IS_WINDOWS
from Shared.Utils.lang import T

RESIDUS_VERSION = "0.6.0"

# Un dossier de cette liste n'est JAMAIS proposé, quelle que soit la zone.
# Noms normalisés (minuscules, sans espace ni tiret).
EXCLUSIONS_RESIDUS = frozenset({
    # Note : le cahier des charges citait « C:\ProgramData\Microsoft » comme
    # exemple de résidu. On s'en écarte volontairement : les dossiers Microsoft
    # (Edge, OneDrive, Office, ClickToRun...) sont partagés et vivants sur
    # presque toutes les machines. La sécurité passe avant l'exemple.
    "temp", "tmp", "tempfiles", "microsoft", "windows", "windows Defender",
    "windows Defender Advanced", "packages", "programs", "programdata",
    "users", "userenv", "audiodg", "ntuser", "desktop.ini", "Microsoft Edge",
    "Microsoft Edge Update", "Microsoft OneDrive",
    "Microsoft Office", "Microsoft OfficeClickToRun", "Microsoft Toolkit",
    "Microsoft Visual Studio", "Microsoft_C#_Compiler", "Windows Defender",
    "Windows Media Player", "WindowsPowerShell", "ssh", "Secureboot",
    "ssh-agent-pid", "mediaCreation", "USOShared", "USOPrivate", "SoftwareDistribution",
    "Package Cache", "UpdateAssistant", "CompatTelRunner", "regidle",
    "Comms", "ConnectedDevicesPlatform", "ConnectedDevicesStore", "D3DSCache",
    "FontCache", "IsolatedStorage", "Network", "Packages", "PeerDistRepub",
    "Temp", "Temps", "Placeholder", "TileDataLayer", "VirtualStore",
    "WindowsApps", "container", "history", "installerCache", "i4i",
    "roaming", "webaccount", "wellknown",
    # Éditeurs et logiciels dont le dossier reste normal sur presque tous les
    # PC (retour terrain : faux positifs à confiance haute).
    "google", "mozilla", "opera", "brave", "discord", "spotify", "dropbox",
    "onedrive", "nvidia", "nvidia corporation", "amd", "intel", "realtek",
    "ubisoft", "ea", "electronic arts", "origin", "battle.net", "blizzard",
    "riot games", "obs", "obs-studio", "python", "jetbrains", "adobe",
    "autodesk", "tidydeck",
})

# Dossiers qui ne contiennent QUE des sauvegardes de jeux, des documents
# perso ou du cache de navigateur : jamais proposés, même orphelins.
INTERDITS_RESIDUS = frozenset({
    "steam", "steamapps", "epicgames", "gog games", "gog galaxy", "savegame",
    "savegames", "savedgames", "myscreenshots", "screenshots",
    "documents", "one note", "onenote", "teams", "outlook", "thunderbird",
    r"firefox", r"google\chrome", "chrome", "edge", "safari", "browser",
})

_ZONES_PAR_DEFAUT = ("APPDATA", "LOCALAPPDATA", "PROGRAMDATA")

MOTIF_PROCESSUS = "Programme en cours d'utilisation"

# Suffixes de version / d'édition qu'on retire avant de comparer deux noms.
_SUFFIXES = re.compile(
    r"[\s\-]?(?:\d+(?:\.\d+)*|x(?:64|86)|beta|alpha|rc\d*|preview|pro|"
    r"home|edition|version|setup|x?\d+bit)\b", re.I)


def normalise(nom):
    """Nom réduit pour la comparaison : minuscule, sans ponctuation de séparation,
    sans suffixe de version. « Microsoft Edge Core 1.42 » -> « microsoftedgecore »."""
    s = str(nom).strip().lower()
    s = _SUFFIXES.sub("", s)
    for sep in (" ", "-", "_", ".", ",", "(", ")", "\\", "/"):
        s = s.replace(sep, "")
    return s.strip()


def levenshtein(a, b):
    """Distance d'édition entre deux chaînes (petites)."""
    a, b = str(a), str(b)
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def est_lien(chemin):
    """Lien symbolique, jointure ou mount point : on ne descend jamais dedans.
    (Windows ne remonte pas les liens via os.path.isdir ; on teste l'attribut.)"""
    try:
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(chemin))
        if attrs != -1:
            return bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except Exception:
        pass
    return os.path.islink(chemin) or os.path.ismount(chemin)


def est_nuage(chemin):
    """Dossier nuage (OneDrive, Dropbox…) : on ne le propose jamais, on ne le
    lit même pas en détail."""
    if "onedrive" in os.path.abspath(chemin).lower():
        return True
    p = os.path.abspath(chemin)
    while p:
        if os.path.isdir(os.path.join(p, ".team")) or os.path.exists(os.path.join(p, ".dropbox")):
            return True
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return False


# ----------------------------------------------------------------__ installs
def _hives():
    import winreg
    return (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)


_CLE_UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"


def _iter_uninstall():
    """Remonte les 3 sources : HKLM 64 bits, HKLM Wow6432Node (32 bits), HKCU."""
    import winreg
    ouverts = []
    try:
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for sous in ("", r"\Wow6432Node"):
                chemin = _CLE_UNINSTALL + sous
                try:
                    k = winreg.OpenKey(hive, chemin)
                except OSError:
                    continue
                ouverts.append(k)
                yield k
    finally:
        for k in ouverts:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass


def _val(cle, nom):
    import winreg
    try:
        v, _ = winreg.QueryValueEx(cle, nom)
        return str(v) if v is not None else ""
    except OSError:
        return ""


_PLATEFORMES = (("steam", "Steam"), ("epic", "Epic Games"), ("gog", "GOG"))


def installes():
    """Liste des programmes installés : registre (3 sources) + menu Démarrer +
    applications Microsoft Store. Chaque entrée : {nom, cle, source, editeur,
    installation, jeu}."""
    out = {}

    def ajoute(nom, source, editeur="", installation=""):
        nom = str(nom or "").strip()
        if not nom:
            return
        k = normalise(nom)
        if not k:
            return
        jeu = ""
        base = (nom + " " + (editeur or "")).lower()
        for mot, plat in _PLATEFORMES:
            if mot in base:
                jeu = plat
                break
        if "steamapps" in (installation or "").lower():
            jeu = "Steam"
        entree = {"nom": nom, "cle": k, "source": source, "editeur": editeur,
                  "installation": installation, "jeu": jeu}
        if k not in out:
            out[k] = entree

    if IS_WINDOWS:
        import winreg
        for cle in _iter_uninstall():
            try:
                for i in range(winreg.QueryInfoKey(cle)[0]):
                    sub = winreg.EnumKey(cle, i)
                    try:
                        c = winreg.OpenKey(cle, sub)
                    except OSError:
                        continue
                    nom = _val(c, "DisplayName")
                    if nom:
                        ajoute(nom, "Windows", _val(c, "Publisher"),
                               _val(c, "InstallLocation"))
                    winreg.CloseKey(c)
            except OSError:
                pass
    # Menu Démarrer : les raccourcis gardent le nom d'affichage de l'app.
    for base in ("APPDATA", "PROGRAMDATA"):
        racine = os.path.join(os.environ.get(base, ""),
                              "Microsoft", "Windows", "Start Menu", "Programs")
        if not os.path.isdir(racine):
            continue
        for dossier, _, fichiers in os.walk(racine):
            for f in fichiers:
                if f.lower().endswith(".lnk"):
                    ajoute(os.path.splitext(f)[0], T("Démarrer"))
    # Microsoft Store : le nom du dossier Packages suffit (pas de PowerShell).
    local = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages")
    if os.path.isdir(local):
        for d in os.listdir(local):
            if "_" in d:
                ajoute(d.split("_")[0], "Store")
    return sorted(out.values(), key=lambda e: e["cle"])



# -------------------------------------------------------------------__ zones
def zones_par_defaut():
    out = []
    for var in _ZONES_PAR_DEFAUT:
        p = os.environ.get(var) or os.path.expandvars(f"%{var}%")
        if p and os.path.isdir(p) and "%" not in p:
            out.append(p)
    return out


def _taillearbre(racine, deadline=None):
    """Taille et dernière activité d'un sous-dossier (sans jamais suivre de lien)."""
    total, dernier = 0, 0.0
    pile = [racine]
    while pile:
        cur = pile.pop()
        try:
            with os.scandir(cur) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            if deadline and time.time() > deadline:
                return total, dernier, True
            try:
                if e.is_symlink() or (getattr(e, "is_junction", lambda: False)()):
                    continue
                if e.is_dir(follow_symlinks=False):
                    pile.append(e.path)
                elif e.is_file(follow_symlinks=False):
                    st = e.stat(follow_symlinks=False)
                    total += st.st_size
                    dernier = max(dernier, st.st_mtime)
            except OSError:
                continue
        try:
            dernier = max(dernier, os.stat(cur, follow_symlinks=False).st_mtime)
        except OSError:
            pass
    return total, dernier, False


# -------------------------------------------------------------------__ motifs
# Comparaison normalisée des deux côtés (correction : « Microsoft Edge » ne
# correspondait jamais à « microsoft edge »).
_EXCLUSIONS_NORM = frozenset(normalise(x) for x in EXCLUSIONS_RESIDUS)
_INTERDITS_NORM = frozenset(normalise(x) for x in INTERDITS_RESIDUS)


def motif_exclusion(nom):
    """Règle 1 : exclusions absolues et dossiers interdits (sauvegardes de jeux,
    documents, navigateurs). Comparaison normalisée des deux côtés."""
    k = normalise(nom)
    if k in _EXCLUSIONS_NORM:
        return T("Exclu (dossier système)")
    if k in _INTERDITS_NORM:
        return T("Contenu ne devant jamais être proposé")
    return None


def motif_telechargement(nom):
    """Règle 3 : téléchargements inachevés."""
    if re.search(r"\.(part|crdownload|download|partial|tmp)$", nom, re.I):
        return T("Téléchargement inachevé")
    return None


def _trouve_partielle(nom, installs):
    """Correspondance « faute de frappe » (distance d'édition <= 2 sur des noms
    d'au moins 6 caractères normalisés). Sert à protéger, plus jamais à proposer."""
    cle = normalise(nom)
    if len(cle) < 6:
        return None, 100.0
    meilleur, dist = None, 99
    for e in installs:
        c = e.get("cle") or ""
        if len(c) < 6 or abs(len(c) - len(cle)) > 2:
            continue
        d = levenshtein(cle, c)
        if d <= 2 and d < dist:
            meilleur, dist = e, d
    if meilleur is None:
        return None, 100.0
    pct = round(100.0 * (1.0 - dist / float(max(len(cle), len(meilleur.get("cle") or "")))))
    return meilleur, pct


def cles_connues(installs):
    """Tous les noms qu'un logiciel installé rend « connus » : nom affiché,
    éditeur, chemin d'installation complet, chaque composante de ce chemin,
    et clé interne."""
    cles = set()
    for e in installs:
        for v in (e.get("nom"), e.get("editeur"), e.get("cle")):
            k = normalise(v) if v else ""
            if len(k) >= 3:
                cles.add(k)
        inst = str(e.get("installation") or "").strip()
        if not inst:
            continue
        k = normalise(inst)
        if len(k) >= 3:
            cles.add(k)
        for part in re.split(r"[\\/]+", inst):
            if ":" in part:
                continue  # lecteur (« C: ») : jamais un nom de dossier
            k = normalise(part)
            if len(k) >= 3:
                cles.add(k)
    return cles


def appartient_a_un_logiciel(nom, installs):
    """Le dossier appartient-il à un logiciel installé ? Dans le doute, OUI
    (on ne propose pas). Noms identiques, l'un contenu dans l'autre (>= 4
    caractères normalisés), ou très proche (Levenshtein <= 2).
    Conséquence voulue : « Google » correspond à « Google Chrome » / « Google LLC »."""
    cle = normalise(nom)
    if not cle:
        return True
    connues = cles_connues(installs)
    if cle in connues:
        return True
    if len(cle) >= 4:
        for k in connues:
            if len(k) >= 4 and (cle in k or k in cle):
                return True
    proche, _ = _trouve_partielle(nom, installs)
    return proche is not None


# Seuils et mots qui disqualifient d'office (données personnelles présumées).
TAILLE_MIN_OCTETS = 1024 * 1024
MOTS_DONNEES_PERSO = ("save", "profile", "config", "backup")


def criteres(nom, taille, age_jours, installs, jours=90):
    """Règle corrigée : un dossier n'est proposé que si AUCUN logiciel installé
    ne lui correspond ET qu'il est inactif depuis plus de `jours` jours, avec
    une taille minimale pour éviter le bruit. Retourne (motif, confiance,
    preuve_install=False) ou None."""
    if taille < TAILLE_MIN_OCTETS:
        return None
    k = normalise(nom)
    if any(m in k for m in MOTS_DONNEES_PERSO):
        return None
    if appartient_a_un_logiciel(nom, installs):
        return None
    if age_jours <= jours:
        return None
    mois = max(1, int(round(age_jours / 30.0)))
    motif = T("Aucun logiciel installé de ce nom · inactif depuis {v0} mois").format(v0=mois)
    return (motif, T("Élevée") if age_jours > 180 else "Moyenne", False)


# -------------------------------------------------------------------__ analyse
def analyse(racines=None, installs=None, jours=90, processus=(), limite_dossiers=400,
            budget_s=60, cancel=None, now=None):
    """Analyse complète (lecture seule). Retourne un dictionnaire :
    lignes, scan_partiel, non_lus, dossiers_vus, budget_s."""
    t0 = time.time()
    deadline = t0 + float(budget_s)
    now = now or time.time()
    if racines is None:
        racines = zones_par_defaut()
    if installs is None:
        installs = installes() if IS_WINDOWS else []
    if not installs or not any(e.get("source") == "Windows" for e in installs):
        # Registre illisible, compte limité, ou liste réduite aux raccourcis
        # Démarrer/Store : beaucoup de vrais installés manqueraient et
        # ressembleraient à des orphelins. On ne propose RIEN (garde-fou 3.3).
        return {"version": RESIDUS_VERSION, "lignes": [], "scan_partiel": False,
                "non_lus": [], "dossiers_vus": 0, "budget_s": 0, "jours": int(jours),
                "installs_illisibles": True}
    processus = {normalise(p) for p in (processus or ())}
    lignes, non_lus = [], []
    partiel, dossiers_vus = False, 0
    for racine in racines:
        if (cancel and cancel()) or time.time() > deadline:
            partiel = True
            break
        try:
            entrees = sorted(os.scandir(racine), key=lambda e: e.name.lower())
        except OSError:
            non_lus.append(racine)
            continue
        for e in entrees:
            if (cancel and cancel()) or time.time() > deadline:
                partiel = True
                break
            try:
                if not e.is_dir(follow_symlinks=False) or est_lien(e.path):
                    continue
            except OSError:
                non_lus.append(e.path)
                continue
            dossiers_vus += 1
            if dossiers_vus > limite_dossiers:
                partiel = True
                break
            if motif_exclusion(e.name):
                continue
            if motif_telechargement(e.name):
                continue
            if normalise(e.name) in processus:
                continue  # règle 4 : MOTIF_PROCESSUS
            if est_nuage(e.path):
                continue  # la règle nuage de TidyDeck passe avant toute autre
            try:
                age_dir = (now - os.stat(e.path, follow_symlinks=False).st_mtime) / 86400.0
            except OSError:
                non_lus.append(e.path)
                continue
            taille, mtime_fichiers, entaille = _taillearbre(e.path, deadline)
            if entaille:
                partiel = True
            age_fichiers = (now - mtime_fichiers) / 86400.0 if mtime_fichiers else age_dir
            age = min(age_dir, age_fichiers) if mtime_fichiers else age_dir
            res = criteres(e.name, taille, age, installs, jours)
            if res is None:
                continue
            motif, confiance, preuve = res
            lignes.append({
                "nom": e.name, "chemin": e.path, "zone": racine, "taille": int(taille),
                "age_jours": int(round(age)), "motif": motif,
                "confiance": confiance, "preuve_install": preuve,
                "selectable": confiance in (T("Élevée"), "Moyenne"),
                "selecte": False, "enfant": False,
            })
    lignes.sort(key=lambda r: (-r["taille"], -r["age_jours"]))
    for i, r in enumerate(lignes):
        r["id"] = i + 1
    return {"version": RESIDUS_VERSION, "lignes": lignes, "scan_partiel": partiel,
            "non_lus": sorted(set(non_lus)), "dossiers_vus": dossiers_vus,
            "budget_s": int(round(time.time() - t0)), "jours": int(jours),
            "installs_illisibles": False}


def processus_actifs():
    """Noms des processus en cours (best effort). Échoue en silence : ce n'est
    qu'un indice d'exclusion. tasklist écrit dans la page de code OEM : on
    remplace les octets invalides au lieu de faire exploser le thread de
    lecture (0xFF en sortie de tasklist a déjà été observé en vrai)."""
    if not IS_WINDOWS:
        return set()
    import subprocess
    try:
        out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True,
                             timeout=15, text=True, errors="replace").stdout or ""
    except Exception:
        return set()
    noms = set()
    for ligne in out.splitlines():
        premier = ligne.split('","')[0].strip('"')
        if premier:
            noms.add(os.path.splitext(premier)[0])
    return noms
