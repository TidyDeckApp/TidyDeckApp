# -*- coding: utf-8 -*-
"""Captures EN de chaque page pour controle visuel « tout rentre dans le bloc »."""
import json
import os
import sys
import tempfile
import time

tmp = tempfile.mkdtemp(prefix="td_shot_")
os.makedirs(os.path.join(tmp, "TidyDeck"), exist_ok=True)
with open(os.path.join(tmp, "TidyDeck", "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"lang": "en", "advanced": True, "serenity": False, "theme": "sombre",
               "text_size": "normale", "first_run": False, "close_action": "minimize",
               "sound": False, "reminder": False, "stream_mode": True,
               "installed": "2026-01-01 00:00:00"}, fh)
os.environ["LOCALAPPDATA"] = tmp
sys.path.insert(0, os.path.abspath("."))

from PIL import ImageGrab
from UI.app import App, flatten_nav

app = App()
app.root.geometry("1200x750+0+0")
app.root.attributes("-topmost", True)
app.root.deiconify()
app.root.update()
time.sleep(0.4)

os.makedirs("_shots", exist_ok=True)
pages = sys.argv[1:] or []
for i, (name, _b) in enumerate(flatten_nav(app._nav_items())):
    if pages and name not in pages:
        continue
    app._on_nav(name)
    for _ in range(150):
        app.root.update()
        time.sleep(0.01)
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    img = ImageGrab.grab((x, y, x + app.root.winfo_width(), y + app.root.winfo_height()))
    out = f"_shots/en_{i:02d}_{name.replace(' ', '_').replace('/', '_')}.png"
    img.save(out)
    print("saved", out)
app.root.destroy()
