# -*- coding: utf-8 -*-
"""Extrait le bundle .exe et le lance depuis l'extraction : prouve que le zip est
complet (Tcl/Tk compris) et que l'executable demarre ailleurs que dans dist\\."""
import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, r"C:\Users\Florius\Downloads\AI\Test\TidyDeck_v2\TidyDeck")
from Shared.Utils.common import APP_VERSION

ZIP = rf"C:\Users\Florius\Downloads\AI\Test\TidyDeck-{APP_VERSION}-win64.zip"
ext = tempfile.mkdtemp(prefix="td_w64_")
with zipfile.ZipFile(ZIP) as z:
    z.extractall(ext)
exe = os.path.join(ext, "TidyDeck", "TidyDeck.exe")
interne = os.path.join(ext, "TidyDeck", "_internal")
n = sum(len(f) for _, _, f in os.walk(interne))
print("extrait :", exe)
print("fichiers dans _internal :", n)
for d in ("_tcl_data", "_tk_data", "vendor"):
    p = os.path.join(interne, d)
    print(f"   {d} : {'PRESENT (' + str(len(os.listdir(p))) + ' entrees)' if os.path.isdir(p) else 'ABSENT'}")

tmp = tempfile.mkdtemp(prefix="td_w64_local_")
os.makedirs(os.path.join(tmp, "TidyDeck"), exist_ok=True)
from Shared.Utils import config
cfg = dict(config.DEFAULTS)
cfg.update({"first_run": False, "sound": False, "theme": "clair", "text_size": "normale",
            "advanced": True, "serenity": False})
with open(os.path.join(tmp, "TidyDeck", "config.json"), "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False)

env = dict(os.environ)
env["LOCALAPPDATA"] = tmp
p = subprocess.Popen([exe], env=env)
print("pid :", p.pid, flush=True)

u = ctypes.windll.user32
trouve = None
for _ in range(60):
    time.sleep(0.5)
    if p.poll() is not None:
        print("PROCESSUS MORT : code", p.returncode, flush=True)
        break
    vus = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def probe(h, lp):
        pid = ctypes.wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value == p.pid and u.IsWindowVisible(h):
            r = ctypes.wintypes.RECT()
            u.GetWindowRect(h, ctypes.byref(r))
            if r.right - r.left > 200 and r.bottom - r.top > 200:
                vus.append(h)
        return True
    u.EnumWindows(probe, 0)
    if vus:
        trouve = vus[0]
        print("fenetre OK hwnd =", int(trouve), flush=True)
        with open(os.path.join(ext, "hwnd.txt"), "w") as f:
            f.write(str(int(trouve)))
        break
if trouve is None:
    print("AUCUNE FENETRE", flush=True)
print("TEMP :", ext, flush=True)
print("LOCALAPPDATA deplace : ", tmp, flush=True)
