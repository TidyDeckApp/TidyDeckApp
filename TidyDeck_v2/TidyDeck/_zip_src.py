# -*- coding: utf-8 -*-
"""Regenerate SEULEMENT le zip de source (pas l'exe), avec son .sha256.
Utilise quand on livre le code mais pas encore le .exe."""
import os
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _zip  # noqa: E402

if os.path.isfile(_zip.ZIP_SRC):
    os.remove(_zip.ZIP_SRC)
with zipfile.ZipFile(_zip.ZIP_SRC, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    n = _zip._ajoute(z, _zip.SRC, _zip.PREFIX)
digest = _zip.sha256(_zip.ZIP_SRC)
with open(_zip.ZIP_SRC + ".sha256", "w", encoding="utf-8", newline="\n") as fh:
    fh.write(f"{digest}  {os.path.basename(_zip.ZIP_SRC)}\n")
print(f"{os.path.basename(_zip.ZIP_SRC)} : {os.path.getsize(_zip.ZIP_SRC)} octets  sha256={digest}")
print(f"source : {n} fichiers")

import tempfile as _tf  # noqa: E402
ext = _tf.mkdtemp(prefix="td_verif_")
with zipfile.ZipFile(_zip.ZIP_SRC) as z:
    z.extractall(ext)
proj = os.path.join(ext, _zip.PREFIX)
r = subprocess.run([sys.executable, "-W", "ignore::ResourceWarning", "-m", "unittest",
                    "discover", "-s", "tests", "-t", "."],
                   cwd=proj, capture_output=True, text=True, encoding="utf-8", errors="replace")
for ligne in (r.stderr or "").strip().splitlines()[-3:]:
    print("   ", ligne)
nommes = [x for x in zipfile.ZipFile(_zip.ZIP_SRC).namelist() if "assets" in x]
print("assets dans le zip :", nommes or "ABSENT")
shutil.rmtree(ext, ignore_errors=True)
