"""Rangement : tri des Téléchargements, fichiers oubliés, clips.
Rien n'est supprimé : les déplacements sont journalisés, les mises de côté vont en quarantaine."""
import heapq
import os
import shutil
import time
from pathlib import Path
from Shared.Utils import quarantine
from Shared.Utils import cloud
from Shared.Utils import dossiers
from Shared.Utils.common import IS_WINDOWS
from Shared.Utils.lang import T

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".svg"},
    "Documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".odt", ".csv"},
    "Vidéos": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Musique": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Programmes": {".exe", ".msi"},
}
EXT_TO_CAT = {e: c for c, es in CATEGORIES.items() for e in es}
IN_PROGRESS = {".crdownload", ".part", ".tmp", ".download", ".partial"}


# Les dossiers « ou ca s'accumule », vus par leur identite Windows et non par un
# nom : le nom reel depend de la langue du PC et de l'utilisateur.
DOSSIERS_PAR_DEFAUT = ("downloads", "documents", "desktop", "pictures")
DOSSIERS_GROS = ("downloads", "documents", "desktop", "videos", "pictures")


def default_folders():
    """Dossiers a scanner par defaut, quel que soit le nom que Windows leur donne.

    Le nom affiche n'est pas le nom reel, et le dossier peut etre renomme ou
    bascule sur OneDrive : deviner le nom ferait rater le dossier sans le dire.
    On le demande a Windows (Shared/Utils/dossiers.py)."""
    return dossiers.tous(DOSSIERS_PAR_DEFAUT)


# ---------------------------------------------------------------------------
# Les plus gros elements — LECTURE SEULE.
# Aucune ecriture, aucune suppression, rien n'est enregistre dans le journal.
# ---------------------------------------------------------------------------

# Dossiers systemes : ignores a la racine d'un disque (jamais scannes, jamais touches).
SYSTEM_DIR_NAMES = {"windows", "program files", "program files (x86)", "winsxs",
                   "system32", "syswow64", "boot", "recovery", "efi",
                   "$recycle.bin", "system volume information", "windowsapps",
                   "programdata", "documents and settings", "recovery"}
# Fichiers systemes verrouilles / a ne jamais compter ni toucher.
SYSTEM_FILE_NAMES = {"pagefile.sys", "hiberfil.sys", "swapfile.sys"}


class _Cancelled(Exception):
    """Signale interrompt : remonte a travers le scan sans rien laisser derriere."""


def _is_link(path):
    """Lien symbolique OU jonction Windows. On ne les suit jamais : ils feraient
    compter deux fois les memes octets, et pourraient sortir de la zone analysee."""
    try:
        if os.path.islink(path):
            return True
        j = getattr(os.path, "isjunction", None)
        if j is not None and j(path):
            return True
    except OSError:
        return True
    return False


def _at_drive_root(path):
    """Vrai seulement pour un element place DIRECTEMENT sous la racine du
    disque (« C:\\Windows »), pas pour « C:\\Users\\x\\Windows ».

    os.path.dirname renvoie « C:\\ » (3 caracteres) pour « C:\\Users » : le
    test sur la longueur du parent ne marchait jamais, le garde-fou systeme
    etait donc mort en pratique.
    """
    p = str(path).rstrip("\\/")
    if IS_WINDOWS:
        drive, rest = os.path.splitdrive(p)
        if not drive:
            return False
        inner = rest.strip("\\/")
        return bool(inner) and "\\" not in inner and "/" not in inner
    return os.path.isabs(p) and os.path.dirname(p) == "/"


def is_system_dir(name, path):
    """Systeme seulement si c'est un dossier systeme EN RACINE DE DISQUE : un
    dossier « windows » perdu dans les Documents du user n'est pas systeme."""
    if not _at_drive_root(path):
        return False
    return str(name).lower() in SYSTEM_DIR_NAMES


def largest_zone():
    """Zone par defaut : le dossier utilisateur, jamais le disque entier."""
    zs = [str(p) for p in dossiers.tous(DOSSIERS_GROS)]
    return zs or [str(Path.home())]


def _push(heap, item, limit):
    if len(heap) < limit:
        heapq.heappush(heap, item)
    elif item[0] > heap[0][0]:
        heapq.heapreplace(heap, item)


def find_largest(root, cancel=None, limit=20):
    """Les plus gros elements sous `root`.

    Retourne un dict :
      files    : [(taille, chemin, mtime), ...] les `limit` plus gros fichiers, recursif
      folders  : [(nom, chemin, taille), ...] les `limit` plus gros dossiers
                 DIRECTEMENT sous root — taille totale comprise. On descend dans un
                 dossier en cliquant dessus, ce qui evite qu'un dossier et ses
                 sous-dossiers apparaissent en doublon.
      system   : dossiers systeme rencontres (non scannes, marques « ne pas toucher »)
      locked   : dossiers illisibles (acces refuse) — non classes, car leur taille est
                 impossible a mesurer ; signales dans le pied de page
      scanned  : nombre de fichiers parcourus
      cancelled: True si l'analyse a ete interrompue

    Les acces refuses, liens symboliques et jonctions sont ignores sans erreur.
    Windows / Program Files / pagefile.sys / hiberfil.sys sont ignores aussi.
    """
    zones = [str(p) for p in (root if isinstance(root, (list, tuple)) else [root])
             if p and os.path.isdir(str(p))]
    files, folders, sysd, locked = [], [], [], []
    scanned = [0]
    nuage = [0]

    def chk():
        if cancel is not None and cancel():
            raise _Cancelled()

    def walk(path):
        """Taille totale du contenu. Renvoie None si le dossier lui-meme est
        illisible : on n'affiche pas un dossier inaccessible comme s'il pesait
        0 octet. Un refus plus bas dans l'arbre reste tolere (on compte le reste).

        Le drapeau « est_racine » evite de scanner deux fois : seul l'echec au
        premier niveau rend le dossier non mesurable.
        """
        total = 0
        stack = [(path, True)]
        while stack:
            chk()
            cur, est_racine = stack.pop()
            try:
                entries = list(os.scandir(cur))
            except OSError:
                if est_racine:
                    return None
                continue
            for e in entries:
                chk()
                try:
                    if e.is_file(follow_symlinks=False):
                        if e.name.lower() in SYSTEM_FILE_NAMES:
                            continue
                        if cloud.est_hors_ligne(e.path):
                            nuage[0] += 1
                            continue
                        st = e.stat()
                        total += st.st_size
                        scanned[0] += 1
                        _push(files, (st.st_size, len(files), e.path, st.st_mtime), limit)
                    elif e.is_dir(follow_symlinks=False):
                        if _is_link(e.path):
                            continue
                        stack.append((e.path, False))
                except OSError:
                    continue
        return total

    cancelled = False
    for z in zones:
        try:
            entries = list(os.scandir(z))
        except OSError:
            continue
        for e in entries:
            try:
                if e.is_file(follow_symlinks=False):
                    if e.name.lower() in SYSTEM_FILE_NAMES:
                        continue
                    if cloud.est_hors_ligne(e.path):
                        nuage[0] += 1
                        continue
                    st = e.stat()
                    # les fichiers places directement dans la zone comptent aussi :
                    # sans eux le pied de page « fichiers parcourus » etait faux.
                    scanned[0] += 1
                    _push(files, (st.st_size, len(files), e.path, st.st_mtime), limit)
                elif e.is_dir(follow_symlinks=False):
                    if _is_link(e.path):
                        continue
                    if is_system_dir(e.name, e.path):
                        sysd.append((e.name, e.path, None))
                        continue
                    chk()
                    taille = walk(e.path)
                    if taille is None:
                        locked.append((e.name, e.path))
                        continue
                    folders.append((e.name, e.path, taille))
            except _Cancelled:
                cancelled = True
                break
            except OSError:
                continue
        if cancelled:
            break

    ranked = sorted(folders, key=lambda t: -t[2])[:limit]
    return {"files": [(s, p, m) for s, _, p, m in sorted(files, key=lambda t: -t[0])],
            "folders": ranked + sysd,
            "system": sysd,
            "locked": locked,
            "scanned": scanned[0],
            "nuage": nuage[0],
            "cancelled": cancelled}


def downloads_folder():
    """Le vrai dossier de telechargements, dans la langue du PC."""
    return dossiers.trouver("downloads")


def _unique(p: Path) -> Path:
    if not p.exists():
        return p
    i = 1
    while True:
        q = p.with_name(f"{p.stem} ({i}){p.suffix}")
        if not q.exists():
            return q
        i += 1


def plan_downloads(folder):
    """Liste de déplacements proposés (source, destination, catégorie)."""
    moves = []
    if not folder:
        return moves
    now = time.time()
    for e in os.scandir(folder):
        if not e.is_file() or e.name.startswith("."):
            continue
        ext = os.path.splitext(e.name)[1].lower()
        cat = EXT_TO_CAT.get(ext)
        if ext in IN_PROGRESS or not cat or now - e.stat().st_mtime < 120:
            continue    # inconnu ou en cours de téléchargement : on n'y touche pas
        moves.append((e.path, str(_unique(Path(folder) / cat / e.name)), cat))
    return moves


def apply_moves(moves, journal, title=None):
    title = title or T("Rangement des Téléchargements")
    pairs = []
    for src, dst, _ in moves:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            pairs.append([src, dst])
        except OSError:
            pass
    if pairs:
        journal.add("pairs", title, ("{v0} fichier déplacé." if len(pairs) == 1
                                     else "{v0} fichiers déplacés.").format(v0=len(pairs)),
                    {"pairs": [[a, b] for a, b in pairs]})
    return len(pairs)


def find_forgotten(folders, days=365, min_size=20 << 20, limit=100, ignores=None):
    cutoff = time.time() - days * 86400
    res = []
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in files:
                p = os.path.join(root, n)
                try:
                    if cloud.est_hors_ligne(p):
                        # Inutile et dangereux : « oublié » ne veut rien dire pour un
                        # fichier qui n'occupe pas de place ici.
                        if ignores is not None:
                            ignores.append(p)
                        continue
                    st = os.stat(p)
                    if st.st_size >= min_size and st.st_mtime < cutoff:
                        res.append((st.st_size, p, st.st_mtime))
                except OSError:
                    pass
    return sorted(res, reverse=True)[:limit]


def quarantine_files(paths, journal, title):
    run_id = time.strftime("%Y%m%d-%H%M%S")
    pairs, refuses = [], []
    for i, p in enumerate(paths, 1):
        try:
            pairs.append([p, quarantine.move_in(p, run_id, i)])
        except quarantine.FichierDansLeNuage as e:
            refuses.append((p, str(e)))
        except OSError as e:
            refuses.append((p, T("Déplacement impossible : {v0}").format(v0=e)))
    if pairs:
        journal.add("pairs", title, ("{v0} fichier mis en quarantaine." if len(pairs) == 1
                                     else "{v0} fichiers mis en quarantaine.").format(v0=len(pairs)), {"pairs": pairs})
    return len(pairs), refuses


VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}


def _clip_source(path):
    low = str(path).lower()
    if "captures" in low:
        return "Xbox Game Bar"
    if "relive" in low or "radeon" in low:
        return "AMD Radeon ReLive"
    return T("Clip de jeu (NVIDIA ShadowPlay / autre)")


def find_clips(min_size=100 << 20, limit=200):
    """Grosses vidéos dans Vidéos/ (là où Game Bar, ShadowPlay, ReLive enregistrent par défaut).

    Le dossier est resolu par son identite Windows : son nom affiche peut etre
    « Vidéos » alors que le dossier s'appelle Videos, et il a pu etre deplace."""
    res = []
    for root_dir in dossiers.tous(("videos",)):
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in files:
                if os.path.splitext(n)[1].lower() in VIDEO_EXT:
                    p = os.path.join(root, n)
                    try:
                        if cloud.est_hors_ligne(p):
                            continue
                        st = os.stat(p)
                        if st.st_size >= min_size:
                            res.append((st.st_size, p, st.st_mtime, _clip_source(root)))
                    except OSError:
                        pass
    return sorted(res, reverse=True)[:limit]
