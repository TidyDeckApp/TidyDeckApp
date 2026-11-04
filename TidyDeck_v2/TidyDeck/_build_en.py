import json
import re

exact = json.load(open("_keys_exact.json", encoding="utf-8"))
tr = {}
tr_files = tuple(f"_trans{i}.json" for i in range(1, 14))
for f in tr_files:
    try:
        tr.update(json.load(open(f, encoding="utf-8")))
    except FileNotFoundError:
        pass

final, missing, bad = {}, [], []
for k in sorted(set(exact) | set(tr)):
    v = tr.get(k)
    if v is None:
        base = k.strip()
        if base in tr:
            i = k.find(base)
            v = k[:i] + tr[base] + k[i + len(base):]   # preserve leading/trailing spaces
        else:
            base = k.rstrip()
            if base in tr:
                v = tr[base] + k[len(base):]
    if not v:
        missing.append(k)
        continue
    ph_k = re.findall(r"\{[a-z0-9]+\}", k)
    ph_v = re.findall(r"\{[a-z0-9]+\}", v)
    if sorted(ph_k) != sorted(ph_v):
        bad.append((k[:70], ph_k, ph_v))
    final[k] = v

unused = [k for k in tr if k not in final and k.strip() not in {x.strip() for x in final}]
out = ('"""Dictionnaire FR -> EN (genere, complete a la main). Cles = texte francais exact.\n'
       "\nGLOSSAIRE FIGE (interface, README, site : une seule traduction par terme) :\n"
       '  Calmer Windows = "Calm Windows" | Nettoyage = "Cleanup" | Nettoyer = "Clean up"\n'
       '  Rangement = "Tidy-up" | Démarrage = "Startup" | Journaux = "Logs"\n'
       '  Annuler = "Undo" (fermer une fenetre = "Cancel") | Quarantaine = "Quarantine"\n'
       '  Résidus = "Leftovers" | Applications préinstallées = "Preinstalled apps"\n'
       '  Rappels bien-être = "Wellness reminders" | Minuteur de rendez-vous = "Appointment timer"\n'
       '  modes = "Serenity mode" / "Advanced mode" / "Colorblind mode" / "Discreet mode"\n'
       '  Corbeille = "Recycle Bin" | Mises à jour = "Updates" / "Check for updates"\n'
       '  Aperçu = "Preview" | Appliquer mes choix = "Apply my choices" | Introuvable = "Not found"\n'
       '  Variantes INTERDITES : "Clean-up", "Quiet Windows", "Journal", "Trash", "tab".\n'
       '  Ne jamais ajouter de tiret "—" absent du texte francais.\n'
       '  """\nEN = {\n')
for k in sorted(final):
    out += "    " + json.dumps(k, ensure_ascii=False) + ": " + json.dumps(final[k], ensure_ascii=False) + ",\n"
out += "}\n"
open("Shared/Utils/translations.py", "w", encoding="utf-8", newline="\n").write(out)
print("EN entries:", len(final), "| untranslated keys:", len(missing), "| template mismatch:", len(bad), "| unused:", len(unused))
for m in missing:
    print("  FR-only:", m[:90].replace("\n", "\\n"))
for b in bad:
    print("  BAD TEMPLATE:", b)
for u in unused:
    print("  UNUSED:", u[:80])
json.dump({"missing": missing, "bad": bad, "unused": unused}, open("_missing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
