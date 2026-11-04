# -*- coding: utf-8 -*-
"""Audit i18n : ecrit audit_i18n.txt avec 3 sections.
A = litteraux FR non enrobés dans T() (candidats ; vrais defauts = f-strings FR)
B = cles francaises sans traduction EN (doit etre 0)
C = defauts du dictionnaire EN (doit etre 0)
Lancer depuis la racine du projet : python audit_i18n.py"""
import ast
import json
import os
import re
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from Shared.Utils.translations import EN  # noqa: E402

ACCENTS = re.compile(r"[àâçéèêëîïôùûüœÀÂÇÉÈÊËÎÏÔÙÛÜŒ]")
FORM = string.Formatter()
UP_RE = re.compile(r"[A-ZÀÂÇÉÈÊËÎÏÔÙÛÜ]{4,}")
UP_OK = {"ADHD", "GPL", "SSD", "CPU", "GPU", "RAM", "ROM", "BIOS", "UEFI", "NVIDIA",
         "AMD", "INTEL", "MICROSOFT", "WINDOWS", "INTERNET", "PDF", "URL", "USB",
         "HDD", "NVMe", "SSDS", "DPI", "SDK", "API", "OEM", "UAC", "NTFS", "OneDrive".upper(),
         "TIDYDECK", "YES", "OK", "AAA", "WPA", "DNS", "DHCP", "LAN", "WLAN", "HTTP",
         "HTTPS", "JSON", "XML", "CSV", "UTF", "ASCII", "VBCABLE", "REALTEK", "XBOX",
         "DIRECTX", "WDDM", "BETA", "PRO", "MAX", "ECO", "PC", "PCs".upper(), "FR", "EN",
         "D'UN", "HKEY", "HKCU", "HKLM", "GUID", "GPO", "UWP", "CPU's", "OK"}
CODE_RE = re.compile(r"Select-Object|Get-AppxPackage|Get-Partition|Get-PhysicalDisk|Get-Disk|\$null|NOTFOUND|DriveLetter")
UNIT_RE = re.compile(r"(?<=\d)\s?(Mo|Go|Ko|To)(?![\wÀ-ÿ])")
PLACE = re.compile(r"\{[a-z0-9]+\}")
PH_ANY = re.compile(r"[{}]")


def is_fr(s):
    return bool(ACCENTS.search(s)) or s.lower() in {"nettoyer", "nettoyage", "corbeille"}


def parse_ph(s):
    try:
        return sorted(p[1] for p in FORM.parse(s) if p[1] is not None)
    except Exception as e:  # noqa: BLE001
        return ["ERROR:" + type(e).__name__ + "(" + str(e) + ")"]


def audit_dict():
    bad = []
    for k, v in EN.items():
        if not isinstance(v, str):
            continue
        if CODE_RE.search(k):
            bad.append(("CLE-CODE", k[:70]))
        if "e. " in v and "detected.e." in v:
            bad.append((" detected.e.", k[:60]))
        if ".." in v.replace("...", ""):
            bad.append(("..", k[:60]))
        if v.endswith(":."):
            bad.append((":. fin", k[:60]))
        if (k.startswith(" ") != v.startswith(" ")) or (k.endswith(" ") != v.endswith(" ")):
            bad.append(("ESPACES", k[:60]))
        if (k.count("(") != k.count(")")) is False and v.count("(") != v.count(")"):
            bad.append(("PARENTHESES", k[:60]))
        if parse_ph(k) != parse_ph(v):
            bad.append(("ACCOLADES", k[:60], parse_ph(k), parse_ph(v)))
        for w in UP_RE.findall(v):
            if w not in UP_OK and not re.search(r"\b" + w + r"\b", k):
                bad.append(("MAJ", w, k[:60]))
        for u in UNIT_RE.findall(v):
            bad.append(("UNITE-FR", u, k[:60]))
        v2 = v.replace("Français", "").replace("francais", "")
        if ACCENTS.search(v2):
            bad.append(("ACCENT", k[:60]))
    return bad


def audit_missing():
    keys_path = os.path.join(HERE, "_keys_exact.json")
    exact = json.load(open(keys_path, encoding="utf-8")) if os.path.exists(keys_path) else []
    missing = []
    for k in exact:
        if k in EN and EN[k]:
            continue
        base = k.strip()
        if base in EN and EN[base]:
            continue
        missing.append(k)
    return missing


def _t_spans(src):
    """positions des litteraux deja dans un appel T(...)"""
    spans = set()
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "T":
            for a in n.args:
                for c in ast.walk(a):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str):
                        spans.add(getattr(c, "lineno", 0))
    return spans


def audit_unwrapped():
    out = []
    roots = ("UI", "Core", "Services", "Shared", "main.py")
    for root in roots:
        paths = []
        if os.path.isfile(os.path.join(HERE, root)):
            paths = [os.path.join(HERE, root)]
        else:
            for d, dirs, fs in os.walk(os.path.join(HERE, root)):
                dirs[:] = [x for x in dirs if x != "__pycache__" and not x.startswith("_")]
                paths += [os.path.join(d, f) for f in fs if f.endswith(".py") and not f.startswith("_")]
        for p in paths:
            if p.endswith("translations.py"):
                continue
            src = open(p, encoding="utf-8").read()
            inT = _t_spans(src)
            tree = ast.parse(src)
            for n in ast.walk(tree):
                if isinstance(n, ast.JoinedStr) and not hasattr(n, "_seen"):
                    n._seen = True
                    frags = "".join(v.value for v in n.values if isinstance(v, ast.Constant))
                    if is_fr(frags) and n.lineno not in inT:
                        out.append(("F-STRING", os.path.relpath(p, HERE), n.lineno, frags[:90]))
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and is_fr(n.value) \
                        and len(n.value.strip()) > 2 and n.lineno not in inT:
                    if re.match(r"^[\s]*[-•·]", n.value):
                        continue
                    out.append(("LITTERAL", os.path.relpath(p, HERE), n.lineno, n.value[:90]))
    return out


def main():
    c = audit_dict()
    b = audit_missing()
    a = audit_unwrapped()
    lines = []
    lines.append("=== A. Non enrobés dans T() (candidats ; vrais défauts = F-STRING) ===")
    fstr = [x for x in a if x[0] == "F-STRING"]
    lines.append(f"candidats: {len(a)} | vrais défauts (f-strings FR): {len(fstr)}")
    for x in a:
        lines.append("  " + " | ".join(str(i) for i in x))
    lines.append("=== B. Clés sans traduction EN (doit être 0) ===")
    lines.append(f"manquantes: {len(b)}")
    for k in b:
        lines.append("  " + k[:90].replace("\n", "\\n"))
    lines.append("=== C. Défauts du dictionnaire (doit être 0) ===")
    lines.append(f"défauts: {len(c)}")
    for x in c:
        lines.append("  " + " | ".join(str(i) for i in x))
    txt = "\n".join(lines) + "\n"
    open(os.path.join(HERE, "audit_i18n.txt"), "w", encoding="utf-8").write(txt)
    print(txt[-6000:])
    print("OK: audit_i18n.txt")


if __name__ == "__main__":
    main()
