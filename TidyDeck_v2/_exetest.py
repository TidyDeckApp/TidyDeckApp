# -*- coding: utf-8 -*-
"""Lance le .exe construit, avec une LOCALAPPDATA deplacersee pour ne pas toucher
aux donnees reelles, verifie qu'une fenetre apparait, la capture, puis tue.
A lancer avec le python du build_env (3.12) depuis n'importe ou."""
import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, r"C:\Users\Florius\Downloads\AI\Test\TidyDeck_v2\TidyDeck")
from Shared.Utils import config

EXE = r"C:\Users\Florius\Downloads\AI\Test\dist\TidyDeck\TidyDeck.exe"
tmp = tempfile.mkdtemp(prefix="td_exe_")
os.makedirs(os.path.join(tmp, "TidyDeck"), exist_ok=True)
cfg = dict(config.DEFAULTS)
cfg.update({"first_run": False, "sound": False, "reminder": False, "theme": "sombre",
            "text_size": "normale", "advanced": True, "serenity": False})
with open(os.path.join(tmp, "TidyDeck", "config.json"), "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False)

env = dict(os.environ)
env["LOCALAPPDATA"] = tmp
p = subprocess.Popen([EXE], env=env)
print("pid lance :", p.pid, flush=True)

u = ctypes.windll.user32
hwnd_vu = None
for _ in range(60):
    time.sleep(0.5)
    if p.poll() is not None:
        print("LE PROCESSUS EST MORT : code", p.returncode, flush=True)
        break
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def probe(h, lparam):
        pid = ctypes.wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value == p.pid and u.IsWindowVisible(h):
            r = ctypes.wintypes.RECT()
            u.GetWindowRect(h, ctypes.byref(r))
            if r.right - r.left > 200 and r.bottom - r.top > 200:
                found.append((h, r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True
    u.EnumWindows(probe, 0)
    if found:
        hwnd_vu = found[0][0]
        print(f"fenetre trouvee : hwnd={int(hwnd_vu)} {found[0][3]}x{found[0][4]}", flush=True)
        with open(os.path.join(tmp, "hwnd.txt"), "w") as f:
            f.write(str(int(hwnd_vu)))
        break
if hwnd_vu is None:
    print("AUCUNE FENETRE au bout de 30 s", flush=True)
print("temp :", tmp, flush=True)
with open(os.path.join(tmp, "pid.txt"), "w") as f:
    f.write(str(p.pid))
