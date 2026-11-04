# -*- coding: utf-8 -*-
"""Reconstruit les livrables nomes avec la version courante :
  - TidyDeck-<version>.zip            : la source (filtre deplis, aucun __pycache__)
  - TidyDeck-<version>-win64.zip     : le dossier .exe construit par PyInstaller
Chaque zip a son .sha256 cote a cote, et la source est re-testee dans une extraction fraiche."""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

BASE = r"C:\Users\Florius\Downloads\AI\Test"
SRC = os.path.join(BASE, "TidyDeck_v2", "TidyDeck")
DIST = os.path.join(BASE, "dist", "TidyDeck")
PREFIX = "TidyDeck"
sys.path.insert(0, SRC)
from Shared.Utils.common import APP_VERSION  # noqa: E402

ZIP_SRC = os.path.join(BASE, f"TidyDeck-{APP_VERSION}.zip")
ZIP_EXE = os.path.join(BASE, f"TidyDeck-{APP_VERSION}-win64.zip")


def deplis(nom):
    if nom.startswith("_") and not nom.startswith("__"):
        return True
    if nom in ("verif_pages_windows.txt", "hardware.json", "V1-mode-discret.md",
               "audit_i18n.txt"):
        return True
    if nom.endswith(".log"):
        return True
    return False


def _ajoute(z, dossier, prefix, filtre_deplis=True):
    """filtre_deplis : True pour la source (vire les fichiers de chantier).
    False pour le dossier .exe : la, tout est necessaire, y compris _tcl_data,
    _tk_data et _internal — les enlever rend l'executable inexécutable."""
    n = 0
    for root, dirs, files in os.walk(dossier):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        if filtre_deplis:
            dirs[:] = [d for d in dirs
                       if not (d.startswith("_") and not d.startswith("__"))]
        for f in sorted(files):
            if f.endswith(".pyc"):
                continue
            if filtre_deplis and deplis(f):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, dossier).replace("\\", "/")
            z.write(p, f"{prefix}/{rel}")
            n += 1
    return n


def Construire():
    for z in (ZIP_SRC, ZIP_EXE):
        if os.path.isfile(z):
            os.remove(z)
    with zipfile.ZipFile(ZIP_SRC, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        n_src = _ajoute(z, SRC, PREFIX)
    if os.path.isdir(DIST):
        with zipfile.ZipFile(ZIP_EXE, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            n_exe = _ajoute(z, DIST, "TidyDeck", filtre_deplis=False)
    else:
        n_exe = 0
    return n_src, n_exe


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    n_src, n_exe = Construire()
    for z in (ZIP_SRC, ZIP_EXE):
        if not os.path.isfile(z):
            print(f"{os.path.basename(z)} : NON CONSTRUIT")
            continue
        digest = sha256(z)
        with open(z + ".sha256", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f"{digest}  {os.path.basename(z)}\n")
        print(f"{os.path.basename(z)} : {os.path.getsize(z)} octets  sha256={digest}")
    print(f"source : {n_src} fichiers · exe : {n_exe} fichiers")

    import tempfile
    ext = tempfile.mkdtemp(prefix="td_verif_")
    with zipfile.ZipFile(ZIP_SRC) as z:
        z.extractall(ext)
    proj = os.path.join(ext, PREFIX)
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                      cwd=proj, capture_output=True, text=True, encoding="utf-8", errors="replace")
    dernieres = (r.stderr or "").strip().splitlines()[-4:]
    print("extraction source : code", r.returncode)
    for l in dernieres:
        print("   ", l)
    leftovers = [x for x in zipfile.ZipFile(ZIP_SRC).namelist()
                if "/_" in x and not x.split("/")[-1].startswith("__")]
    print("deplis passes dans le zip source :", leftovers[:5] or "aucun")
    shutil.rmtree(ext, ignore_errors=True)
