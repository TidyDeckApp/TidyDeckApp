# -*- coding: utf-8 -*-
import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from Shared.Utils.translations import EN

out = []

# --- catalog items (nettoyage) ---
from Shared.Constants import catalog
seen = set()
def scan_obj(o):
    for f in ("name", "what", "label", "desc", "hint"):
        v = getattr(o, f, None)
        if isinstance(v, str) and v.strip() and v not in EN and v not in seen:
            seen.add(v)
            out.append(("catalog-attr", v))
    if isinstance(o, dict):
        for f in ("name", "what", "label", "desc", "hint"):
            v = o.get(f)
            if isinstance(v, str) and v.strip() and v not in EN and v not in seen:
                seen.add(v)
                out.append(("catalog-dict", v))

for root, dirs, files in [(0, 0, 0)]:
    pass
def walk(x):
    if isinstance(x, (list, tuple, set)):
        for i in x:
            walk(i)
    elif isinstance(x, dict):
        scan_obj(x)
        for v in x.values():
            walk(v)
    else:
        scan_obj(x)

for attr in dir(catalog):
    if attr.startswith("_"):
        continue
    v = getattr(catalog, attr)
    if isinstance(v, (list, tuple)):
        for it in v:
            walk(it)
    elif isinstance(v, dict):
        walk(v)

# --- services / tweaks ---
from Core.Health import services
from Core.Tweaks import tweaks
for s in services.SERVICES:
    for f in ("name", "what", "risk"):
        if s[f] not in EN:
            out.append(("service", s[f]))
for t in tweaks.TWEAKS:
    for f in ("name", "group", "what", "benefit", "risk"):
        v = getattr(t, f)
        if v and v not in EN:
            out.append(("tweak", v))

# --- niveaux confiance residus + divers ---
for v in ["Moyenne", "Faible", "Élevée", "Inactif.", "Actif.",
          "Actif (ou réglage par défaut de Windows).",
          "Réglée par le pilote (valeur par défaut) : fie-toi à l'affichage de Windows.",
          "Dossier", "Taille · Confiance", "Ce que je vois", "Rien, tout va bien.",
          "📂 Ouvrir l'emplacement (pour vérifier)",
          "Clique sur une ligne pour voir : ce que c'est, où ça se trouve, le risque.",
          "Rien à changer.", "⏻ À DÉSACTIVER", "↩ À RÉACTIVER",
          "services.msc — service « {v0} »"]:
    if v not in EN:
        out.append(("divers", v))

# --- startup UNKNOWN ---
from Core.Startup import startup
if startup.UNKNOWN[0] not in EN:
    out.append(("startup", startup.UNKNOWN[0]))

groups = {}
for kind, s in out:
    groups.setdefault(kind, []).append(s)
for kind, lst in groups.items():
    print(f"===== {kind} ({len(lst)})")
    for s in lst:
        print(repr(s))
json.dump({k: v for k, v in groups.items()}, open("_gap_out.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
