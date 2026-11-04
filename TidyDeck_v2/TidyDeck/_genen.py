"""Squelette EN = perimetre « interface d'abord » (~379) : libelles UI + descriptions
tweaks/services/jeux/rappels. PAS les 786 conseils demarrage (repli FR)."""
import ast
import glob
import json
import os
import re

BAD_START = ("HKEY", "HK", "Software", "%", "ms-", "SOFTWARE", "{", "0x")
ID_RE = re.compile(r"^[a-z0-9_./\\:%\-#*·→\s]+$")
CODE_RE = re.compile(r"Select-Object|Get-AppxPackage|Get-Partition|Get-PhysicalDisk|Get-Disk|\$null|NOTFOUND|DriveLetter")


def keep(s):
    s = s.strip()
    if len(s) < 3 or len(s) > 400:
        return False
    if s.startswith(BAD_START):
        return False
    if CODE_RE.search(s):
        return False
    if ID_RE.match(s):
        return False
    return True


keys = set(); exact = set()
# libelles UI : litteraux des appels d'affichage
UIF = [f for f in glob.glob("UI/**/*.py", recursive=True) if "__pycache__" not in f]
STYLE_RE = re.compile(r"\.(T[A-Za-z]+|TButton|TLabel|TFrame|TNotebook|TProgressbar|TCheckbutton|TRadiobutton)$")
DOCS = set()
for path in UIF:
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            b = node.body
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) \
                    and isinstance(b[0].value.value, str):
                DOCS.add(id(b[0].value.value))
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
            if fn in ("T", "askyesno", "askyesnocancel", "showinfo", "showwarning", "showerror",
                      "say", "configure"):
                for a in n.args + [k.value for k in n.keywords]:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str) and keep(a.value) \
                            and id(a.value) not in DOCS:
                        keys.add(a.value.strip()); exact.add(a.value)
    # labels text= en dur (ttk/tk Label/Button/Checkbutton/Radiobutton)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            for k in n.keywords:
                if k.arg in ("text", "title", "subtitle", "detail", "info") and isinstance(k.value, ast.Constant) \
                        and isinstance(k.value.value, str) and keep(k.value.value) \
                        and id(k.value.value) not in DOCS:
                    keys.add(k.value.value.strip()); exact.add(k.value.value)

# descriptions services (name/what/risk) et tweaks (name + 3 textes)
for path, fieldset in [("Core/Health/services.py", ("name", "what", "risk")),
                       ("Core/Games/games.py", None)]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    for n in ast.walk(tree):
        if fieldset and isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value in fieldset and isinstance(v, ast.Constant) \
                        and isinstance(v.value, str) and keep(v.value):
                    keys.add(v.value.strip()); exact.add(v.value)
    if not fieldset:
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value.split()) > 1 and keep(n.value):
                keys.add(n.value.strip()); exact.add(n.value)
tree = ast.parse(open("Core/Tweaks/tweaks.py", encoding="utf-8").read())
for n in ast.walk(tree):
    if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "Tweak":
        for a in n.args[1:5]:
            if isinstance(a, ast.Constant) and isinstance(a.value, str) and keep(a.value):
                keys.add(a.value.strip()); exact.add(a.value)
# textes des rappels (scheduler MESSAGES)
tree = ast.parse(open("Services/Reminders/scheduler.py", encoding="utf-8").read())
for n in ast.walk(tree):
    if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value.split()) > 1 and keep(n.value):
        keys.add(n.value.strip()); exact.add(n.value)

# constantes passees en variable aux chokepoints (nav, niveaux, filtres)
NAVCONST = {"NAV_ITEMS": "UI/app.py", "SERENE_TOP": "UI/app.py", "ADVANCED_ONLY": "UI/app.py",
            "LEVEL": "UI/Pages/startup_page.py", "LV": "UI/Pages/services_page.py",
            "FILTERS": "UI/Pages/services_page.py"}
for cname, cpath in NAVCONST.items():
    tree = ast.parse(open(cpath, encoding="utf-8").read())
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == cname for t in n.targets):
            for s in ast.walk(n.value):
                if isinstance(s, ast.Constant) and isinstance(s.value, str) and keep(s.value):
                    keys.add(s.value.strip()); exact.add(s.value); exact.add(s.value)

# every T("...") literal of the shipped code (UI + Shared + Core + Services + main)
for _r in ("UI", "Shared", "Core", "Services"):
    for _d, _dirs, _fs in os.walk(_r):
        _dirs[:] = [x for x in _dirs if x != "__pycache__" and not x.startswith("_")]
        for _f in _fs:
            if _f.endswith(".py") and not _f.startswith("_") and _f != "translations.py":
                _tree = ast.parse(open(os.path.join(_d, _f), encoding="utf-8").read())
                for _n in ast.walk(_tree):
                    if isinstance(_n, ast.Call) and getattr(_n.func, "id", None) == "T" \
                            and _n.args:
                        for _c in ast.walk(_n.args[0]):
                            if isinstance(_c, ast.Constant) and isinstance(_c.value, str):
                                _v = _c.value
                                if "{" not in _v and len(_v.strip()) < 3:
                                    continue
                                keys.add(_v); exact.add(_v)
                    if isinstance(_n, ast.Call) and isinstance(_n.func, ast.Attribute) \
                            and _n.func.attr == "__init__" and len(_n.args) >= 2 \
                            and isinstance(_n.args[0], ast.Name) and _n.args[0].id == "master":
                        for _c in _n.args[1:4]:
                            if isinstance(_c, ast.Constant) and isinstance(_c.value, str) and keep(_c.value):
                                keys.add(_c.value); exact.add(_c.value)

srt = [k for k in sorted(keys) if not STYLE_RE.search(k)
       and not re.match(r"^[\W\d_()!:.,'\" ]+$", k)
       and not k.startswith("(Get-") and not k.startswith("(guid")]
EXACT = sorted(exact)
json.dump(EXACT, open("_keys_exact.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
open("_keys_exact.txt", "w", encoding="utf-8").write("\n".join(EXACT))
out = "EN = {\n"
for k in srt:
    out += json.dumps(k, ensure_ascii=False) + ": " + json.dumps("", ensure_ascii=False) + ",\n"
out += "}\n"
open("_skel_ui.py", "w", encoding="utf-8").write(out)
print("interface keys:", len(srt))
