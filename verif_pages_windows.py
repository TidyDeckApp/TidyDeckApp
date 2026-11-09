# -*- coding: utf-8 -*-
"""Vérification des pages « Paramètres » sur la machine courante (Windows 10 / 11).

La liste des adresses n'est PAS recopiée à la main : elle est lue dans le code du
projet. Tout ce qui peut mener a une page Windows est capte :
  - les mots-cles `settings="..."` et `settings=["...", "..."]`
  - les appels directs `open_windows_settings("...")`
  - les litteraux `ms-settings:...` passes a ces appels
Si quelqu'un ajoute une page, elle apparait ici ; si elle n'est pas documentee,
le script le signale comme un souci.

    python verif_pages_windows.py            # verification automatique (rien ne s'ouvre)
    python verif_pages_windows.py --ouvrir   # ouvre chaque page pour controle visuel

Aucune dependance. Aucune ecriture dans le registre. Le seul fichier produit est le
rapport, et la config TidyDeck de la machine est isolee pendant la verification.
"""
import ast
import atexit
import os
import shutil
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)

SKIP_DIRS = {"__pycache__", "packaging", "vendor", ".git", ".idea", ".vscode", "tests"}
FICHIER_RAPPORT = "verif_pages_windows.txt"

# Ce que chaque adresse est censee afficher, et ce qui change entre Windows 10 et 11.
DOC = {
    "startupapps": ("Applications > Applications au demarrage",
                    "identique Windows 10 / 11"),
    "nightlight": ("Systeme > Affichage > Lumiere nocturne",
                   "identique Windows 10 / 11"),
    "windowsupdate": ("Windows Update",
                      "identique Windows 10 / 11"),
    "gaming-gamemode": ("Jeux > Mode jeu",
                        "existe sur les deux ; la page < Modes de capture > a bouge"),
    "gaming-gamedvr": ("Jeux > Captures",
                       "existe sur les deux"),
    "display-advancedgraphics": ("Systeme > Affichage > Graphiques > Parametres graphiques",
                                 "Windows 10 : la liste d'applications peut etre vide selon le pilote"),
    "control:Microsoft.PowerOptions": ("Panneau de configuration > Options d'alimentation",
                                       "passe par control.exe, pas par ms-settings"),
}


def adresses_du_code():
    """Toutes les adresses de page Windows utilisees par le produit.

    Renvoie une liste de (valeur_declaree, [fichier:ligne, ...])."""
    trouvees = {}

    def consigne(val, d):
        trouvees.setdefault(val, [])
        if d not in trouvees[val]:
            trouvees[val].append(d)

    def depuis_expr(n, d):
        """Constantes string d'une expression : chaine, liste, tuple."""
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            consigne(n.value, d)
        elif isinstance(n, (ast.List, ast.Tuple)):
            for e in n.elts:
                if isinstance(e, ast.Constant) and isinstance(e.value, str):
                    consigne(e.value, d)

    for r, dirs, fs in os.walk(RACINE):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in sorted(fs):
            if not f.endswith(".py") or f.startswith("_"):
                continue
            p = os.path.join(r, f)
            rel = os.path.relpath(p, RACINE).replace("\\", "/")
            try:
                with open(p, encoding="utf-8") as fh:
                    source = fh.read()
                arbre = ast.parse(source, p)
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(arbre):
                # settings="..." / settings=[...]
                if isinstance(node, ast.keyword) and node.arg == "settings":
                    depuis_expr(node.value, "%s:%d" % (rel, node.lineno))
                # open_windows_settings("...")
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "open_windows_settings" and node.args):
                    depuis_expr(node.args[0], "%s:%d" % (rel, node.lineno))
    return sorted(trouvees.items())


def machine():
    v = sys.getwindowsversion()
    # .major vaut 10 meme sous Windows 11 (recoin de compatibilite) :
    # seul le numero de build distingue les deux.
    nom = ("Windows 11" if v.build >= 22000
           else "Windows 10" if v.build >= 10240 else "Windows (inconnu)")
    return nom, v.build


def sonde(ouvre, addr):
    """(ok, cible_transmise, exception) sans rien ouvrir reellement."""
    cible = []
    vrai_startfile = getattr(os, "startfile", None)
    vrai_popen = subprocess.Popen

    os.startfile = lambda p: cible.append(str(p))
    subprocess.Popen = lambda a, *x, **k: cible.append(
        " ".join(str(i) for i in (a if isinstance(a, (list, tuple)) else [a])))
    try:
        ok = bool(ouvre(addr))
    except Exception as exc:  # noqa: BLE001
        return False, (cible[0] if cible else "(rien)"), repr(exc)
    finally:
        if vrai_startfile is not None:
            os.startfile = vrai_startfile
        subprocess.Popen = vrai_popen
    return ok, (cible[0] if cible else "(rien)"), None


def phase_auto(common, adresses):
    lignes, soucis = [], 0
    for addr, sources in adresses:
        ok, cible, exc = sonde(common.open_windows_settings, addr)
        préfixe_ok = cible.startswith("ms-settings:") or cible.startswith("control.exe")
        documentée = addr in DOC
        att, note = DOC.get(addr, ("(page non documentee : a ajouter dans DOC)", "inconnue"))
        if (not ok) or (not préfixe_ok) or (not documentée) or exc:
            soucis += 1
        lignes.append({
            "declaree": addr, "cible": cible, "prefixe": préfixe_ok, "vue": "non testee",
            "attendue": att, "note": note, "sources": sources,
            "souci": bool((not ok) or (not préfixe_ok) or (not documentée) or exc),
            "exc": exc,
        })
    return lignes, soucis


def phase_manuelle(lignes):
    print("\n--- Controle visuel ---")
    print("Entree = ouvrir la page. Puis : o = la bonne page s'affiche, n = mauvaise page,")
    print("s = passer sans ouvrir, q = terminer (le rapport part quand meme).\n")
    for it in lignes:
        if it["souci"]:
            it["vue"] = "a revoir d'abord"
            continue
        while True:
            try:
                c = input("%s\n   attendue : %s\n   (Entree ouvrir / o / n / s / q) > "
                         % (it["cible"], it["attendue"])).strip().lower()
            except (EOFError, KeyboardInterrupt):
                it["vue"] = "non testee"
                raise
            if c in ("q", "quit"):
                it["vue"] = "non testee"
                raise KeyboardInterrupt
            if c in ("s", "p"):
                it["vue"] = "passee"
                break
            if c in ("o", "oui"):
                it["vue"] = "oui"
                break
            if c in ("n", "non"):
                it["vue"] = "non"
                break
            if c == "":
                try:
                    if it["cible"].startswith("ms-settings:"):
                        os.startfile(it["cible"])
                    else:
                        subprocess.Popen(["control.exe", "/name",
                                         it["declaree"].split(":", 1)[1]])
                    it["vue"] = "ouverte, pas encore confirmee"
                except Exception as exc:  # noqa: BLE001
                    print("   ouverture impossible :", exc)
                    it["vue"] = "ouverture impossible"
                    break
                continue
            print("   reponse non comprise.")


def adresses_doc_inutilisees(adresses):
    """Pages decrites dans DOC mais plus utilisees nulle part dans le code : la doc a
    derive. Ce n'est pas un erreur metier, mais c'est a nettoyer."""
    utilisees = {a for a, _ in adresses}
    return sorted(p for p in DOC if p not in utilisees)


def rapport(lignes, soucis, nom, build, repli, doc_morte=()):
    w_cible = max([len(it["cible"]) for it in lignes] + [len("ADRESSE REELLE TRANSMISE")])
    entetes = [
        "Verification des pages < Parametres >",
        "Machine : %s (build %d)" % (nom, build),
        "Repli de version applique ici : " + repli,
        "",
        "%-*s  %-8s  %-12s  %s" % (w_cible, "ADRESSE REELLE TRANSMISE", "PREFIXE",
                                     "VUE A LA MAIN", "PAGE ATTENDUE"),
        "-" * (w_cible + 60),
    ]
    corps = []
    for it in lignes:
        corps.append("%-*s  %-8s  %-12s  %s" % (
            w_cible, it["cible"],
            "oui" if it["prefixe"] else "NON",
            it["vue"], it["attendue"]))
        corps.append("    declaree : %s   (%s)" % (it["declaree"], ", ".join(it["sources"])))
        corps.append("    note     : %s" % it["note"])
        if it["exc"]:
            corps.append("    EXCEPTION : %s" % it["exc"])
    queue = [
        "",
        "Verifie seul par ce script : l'adresse transmise a Windows porte le prefixe",
        "ms-settings: (ou passe par control.exe), et tout repli de page declare est",
        "signale. Verifiable uniquement a l'oeil : que la page affichee est la bonne -> colonne",
        "< VUE A LA MAIN >, obtenue avec --ouvrir.",
        "",
        "Adresses testees : %d | soucis automatiques : %d" % (len(lignes), soucis),
        "Refusees a l'oeil (vue = non) : %d" % sum(1 for it in lignes if it["vue"] == "non"),
    ]
    if doc_morte:
        queue.append("Pages decrites dans DOC mais plus utilisees dans le code (a nettoyer) : "
                    + ", ".join(doc_morte))
    return "\n".join(entetes + corps + queue) + "\n"


def ecrire(texte):
    for dossier in (os.getcwd(), RACINE, tempfile.gettempdir()):
        try:
            chemin = os.path.join(dossier, FICHIER_RAPPORT)
            with open(chemin, "w", encoding="utf-8") as fh:
                fh.write(texte)
            return chemin
        except OSError:
            continue
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        from Shared.Utils import depannage
        depannage.noter("verif_pages_windows.py:244")
    if sys.platform != "win32":
        print("reserve a Windows : ce script teste des URI ms-settings:.")
        return 2
    bac = tempfile.mkdtemp(prefix="td_pagechk_")
    atexit.register(lambda: shutil.rmtree(bac, ignore_errors=True))
    os.environ["LOCALAPPDATA"] = os.path.join(bac, "LocalAppData")
    os.environ["APPDATA"] = os.path.join(bac, "RoamingAppData")

    from Shared.Utils import common

    adresses = adresses_du_code()
    if not adresses:
        print("Aucune adresse trouvee dans le code : perimetre de scan a verifier.")
        return 2
    lignes, soucis = phase_auto(common, adresses)
    if "--ouvrir" in sys.argv:
        try:
            phase_manuelle(lignes)
        except (KeyboardInterrupt, EOFError):
            print("\nInterrompu — le rapport part avec ce qui est deja coche.")
    nom, build = machine()
    if common.MS_SETTINGS_ALIASES:
        repli = " ; ".join("%s remplacee par %s" % (a, b)
                           for a, b in common.MS_SETTINGS_ALIASES.items())
    else:
        repli = ("aucun repli de page declare (aucune page utilisee n'a ete retiree "
                 "par Windows a ce jour)")
    refusées = sum(1 for it in lignes if it["vue"] == "non")
    texte = rapport(lignes, soucis, nom, build, repli, adresses_doc_inutilisees(adresses))
    chemin = ecrire(texte)
    print(texte)
    print(("Rapport ecrit : " + chemin) if chemin
          else "Rapport non ecrit (dossier en lecture seule ?) — contenu affiche ci-dessus.")
    return 1 if (soucis or refusées) else 0


if __name__ == "__main__":
    sys.exit(main())
