# -*- coding: utf-8 -*-
"""Sonde GUI langue=EN : textes des boutons/libelles par page, mots francais restants,
libelles hors-fenetre (#34). Sortie : _probe_lang_out.txt"""
import os, sys, tempfile, json, time, traceback
sys.path.insert(0, os.path.abspath("."))

tmp = tempfile.mkdtemp(prefix="td_lang_")
os.makedirs(os.path.join(tmp, "TidyDeck"), exist_ok=True)
with open(os.path.join(tmp, "TidyDeck", "config.json"), "w", encoding="utf-8") as fh:
    json.dump({"lang": "en", "advanced": True, "serenity": bool(os.environ.get("SEREN")), "theme": "sombre",
               "text_size": "normale", "first_run": False, "close_action": "minimize",
               "sound": False, "reminder": False, "stream_mode": False,
               "installed": "2026-01-01 00:00:00"}, fh)
os.environ["LOCALAPPDATA"] = tmp

from UI.app import App, flatten_nav

lignes = []


def log(s):
    lignes.append(str(s))


app = App()
app.root.geometry("1200x750+0+0")
app.root.deiconify()
app.root.update()
log(f"TITRE FENETRE: {app.root.title()!r}")

ACCENTS = set("àâäçéèêëîïôöùûüœÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŒ")
MOTS_FR = {"le", "la", "les", "des", "du", "aux", "un", "une", "est", "sont", "pas",
           "pour", "avec", "dans", "votre", "vos", "tes", "ton", "ce", "cette",
           "faire", "mettre", "voir", "ici", "tout", "tous", "toutes", "aucun",
           "aucune", "analyser", "analyse", "annuler", "enregistrer", "suivant",
           "fermer", "ouvrir", "choisir", "langue", "thème", "applis", "ménage",
           "rangement", "rappels", "démarrage", "nettoyage", "configuration",
           "sauvegarde", "journal", "disponible", "télécharger",
           "fichier", "terminé", "pages", "sélection", "activer", "désactivé",
           "activé", "petit", "toujours", "jamais", "chemin", "vrai", "dossier",
           "place", "toutes", "sans", "sous", "notre", "nous", "vous",
           "fichiers", "temporaires", "corbeille", "paramètres", "lecture", "en attente",
           "restant", "restants", "déplace", "conçu", "plutôt", "vois", "trouvé", "trouvés",
           "serveur", "sont là", "mémoire", "chauffe", "souffle", "pile", "branché"}
HOMO = {"journal", "pages", "options", "info", "details", "detail", "category", "error",
        "audio", "video", "menu", "control", "controls", "mode", "modes", "plan", "plans",
        "restart", "status", "ideal", "data", "design", "format", "library", "check"}


def sent_fr(t):
    """Vrai si la chaine courte sent le francais (accents ou mots-outils).

    Les mots en -tion/-sion sont des homographes FR/EN : ils ne trahissent pas
    le francais (« configuration », « information »... en anglais aussi)."""
    if any(c in ACCENTS for c in t):
        return True
    mots = [m.lower() for m in __import__("re").findall(r"[a-zA-Zà-ÿ']+", t)]
    mots = [m for m in mots if not m.endswith(("tion", "sion"))]
    return bool(set(mots) & (MOTS_FR - HOMO))


def sous_canvas(w):
    while w:
        try:
            c = w.winfo_class()
        except Exception:
            return False
        if c in ("Canvas", "TkCanvas"):
            return True
        w = w.master
    return False


def marche(w, out, top=True):
    for c in w.winfo_children():
        t = ""
        try:
            t = str(c.cget("text"))
        except Exception:
            pass
        if t:
            out.append((c, t))
        try:
            if c.winfo_class() == "Text":
                out.append((c, c.get("1.0", "end-1c")[:400]))
        except Exception:
            pass
        try:
            if c.winfo_class() == "Treeview":
                for col in c.cget("columns"):
                    out.append((c, str(c.heading(col, "text"))))
                for iid in c.get_children():
                    for v in c.item(iid, "values"):
                        out.append((c, str(v)))
        except Exception:
            pass
        marche(c, out, top)


def pump(n=3):
    for _ in range(n):
        app.root.update()
        time.sleep(0.01)


boutons_fr = []
labels_fr = []
hors_vue = []

for name, _badge in flatten_nav(app._nav_items()):
    try:
        app._on_nav(name)
    except Exception:
        log(f"ERREUR nav {name}: {traceback.format_exc()}")
        continue
    pump(150)
    page = app.pages[name]
    fen_bas = app.root.winfo_rooty() + app.root.winfo_height()
    objs = []
    marche(page, objs)
    marche(app.banner, objs)
    if name == "Accueil":
        marche(app.sidebar, objs)
    nb_boutons = 0
    for w, t in objs:
        try:
            cls = w.winfo_class()
        except Exception:
            continue
        bouton = cls in ("TButton", "Button")
        interactive = bouton or cls in ("TCheckbutton", "TRadiobutton")
        if bouton:
            nb_boutons += 1
        if interactive and len(t) < 250 and sent_fr(t):
            boutons_fr.append(f"{name:22s} [{cls:14s}] {t!r}")
        if (not interactive) and cls in ("TLabel", "Label", "Treeview", "Text") and len(t) < 400 and sent_fr(t):
            labels_fr.append(f"{name:22s} [{cls:14s}] {t!r}")
        try:
            if w.winfo_ismapped() and not sous_canvas(w) and len(t) < 250:
                if w.winfo_rooty() + w.winfo_height() > fen_bas + 1:
                    hors_vue.append(f"{name:22s} [{cls:14s}] bas={w.winfo_rooty()+w.winfo_height()} > {fen_bas} {t!r}")
        except Exception:
            pass
    log(f"PAGE {name:22s} widgets-texte={len(objs):4d} boutons={nb_boutons}")

log("\n== BOUTONS/CASES RESTES EN FRANCAIS ==")
for x in boutons_fr:
    log(x)
log(f"({len(boutons_fr)})")
log("\n== LABELS COURTS RESTES EN FRANCAIS (peut inclure bilingue voulu) ==")
for x in labels_fr:
    log(x)
log(f"({len(labels_fr)})")
log("\n== LIBELLES COURTS HORS-FENETRE (candidats #34) ==")
for x in hors_vue:
    log(x)
log(f"({len(hors_vue)})")

app.root.destroy()
with open("_probe_lang_out.txt" if not os.environ.get("SEREN") else "_probe_seren_out.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lignes))
print("OK", len(lignes), "lignes -> _probe_lang_out.txt")
