"""Contrôles pour joueurs : des CONSEILS, aucune modification automatique."""
import os
import re
from Shared.Models.models import Check
from Shared.Utils.common import IS_WINDOWS, run_cmd, run_ps
from Shared.Utils import registry
from Shared.Utils.lang import T

PLANS = {"381b4222-f694-41f0-9685-ff5bb260df2e": "Utilisation normale (équilibré)",
         "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "Performances élevées",
         "a1841308-3541-4fab-bc81-f71556f20b4a": "Économie d'énergie",
         "e9a42b02-d5df-448d-aa00-03f14749eb61": "Performances maximales"}


def _plan():
    """(guid, nom lisible). Ne renvoie jamais « illisible » : on retombe sur un message utile."""
    rc, out = run_cmd(["powercfg", "/getactivescheme"], 10)
    m = re.search(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", out or "")
    if not m:
        return None, T("Non lisible automatiquement")
    guid = m.group(0).lower()
    if guid in PLANS:
        return guid, T(PLANS[guid])
    custom = re.search(r"\(([^)]+)\)", out)
    return guid, T("Plan personnalisé : {v0}").format(v0=T(custom.group(1))) if custom else T("Plan personnalisé")


def _steam_libraries():
    path = registry.read("HKCU", r"Software\Valve\Steam", "SteamPath")
    libs = []
    if path:
        p = path.replace("/", "\\")
        libs.append(p)
        try:
            txt = open(os.path.join(p, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace").read()
            libs += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', txt)]
        except OSError:
            pass
    # Vraie casse Windows affichée (SteamPath du registre est souvent en minuscules).
    return [_joli_chemin(p) for p in dict.fromkeys(libs)]


def _joli_chemin(chemin):
    """Chemin réaffiché avec la vraie casse des dossiers (Windows ignore la casse,
    mais un « games » tout petit à l'écran fait négligé). Pur cosmétique."""
    if not IS_WINDOWS or not chemin:
        return chemin
    parts = chemin.replace("/", "\\").split("\\")
    out = []
    for part in parts:
        if not part:
            continue
        if not out:
            out.append(part.upper() if part.endswith(":") else part)
            continue
        real = part
        try:
            for e in os.scandir("\\".join(out)):
                if e.name.lower() == part.lower():
                    real = e.name
                    break
        except OSError:
            pass
        out.append(real)
    return "\\".join(out)


def _media_type(letter):
    _, out = run_ps(f"(Get-Partition -DriveLetter {letter} | Get-Disk | Get-PhysicalDisk).MediaType", 20)
    return out.strip()


def game_disk_checks(serenity=False):
    out, seen = [], set()
    for lib in _steam_libraries():
        letter = lib[:1].upper()
        if not letter.isalpha() or letter in seen:
            continue
        seen.add(letter)
        mt = _media_type(letter)
        if mt.upper() == "HDD":
            out.append(Check(T("Tes jeux Steam sont sur un disque classique") if serenity
                             else T("Tes jeux Steam sont sur {v0}: (disque dur lent)").format(v0=letter), "warn",
                             (T("Un disque classique, un peu plus lent au chargement des gros jeux.") if serenity
                              else T("Bibliothèque : {v0} — type de disque : HDD.").format(v0=_joli_chemin(lib))),
                             T("Les jeux récents (monde ouvert surtout) chargent bien plus vite sur un SSD. Dans Steam : "
                             "clic droit sur le jeu > Propriétés > Fichiers installés > Déplacer le dossier d'installation. "
                             "TidyDeck ne déplace pas les jeux lui-même : Steam le fait proprement, sans perdre tes sauvegardes."),
                             path=lib, location=T("le dossier de la bibliothèque Steam")))
        elif mt:
            out.append(Check(T("Tes jeux Steam sont sur {v0}: ({v1})").format(v0=letter, v1=mt), "ok",
                             T("Bibliothèque : {v0}").format(v0=_joli_chemin(lib)), "",
                            path=lib, location=T("le dossier de la bibliothèque Steam")))
    return out


def run_checks(serenity=False):
    if not IS_WINDOWS:
        return [Check("Windows requis", "info", "Ces contrôles lisent les réglages de Windows.")]
    out = []
    gm = registry.read("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled")
    if gm == 0:
        out.append(Check("Mode jeu Windows", "warn", T("Désactivé."),
                         "Paramètres > Jeux > Mode jeu : active-le. Il limite les tâches de fond pendant que tu joues.",
                         settings="gaming-gamemode", location="Paramètres > Jeux (Mode jeu)"))
    else:
        out.append(Check("Mode jeu Windows", "ok", "Actif (ou réglage par défaut de Windows).",
                         "", settings="gaming-gamemode", location="Paramètres > Jeux (Mode jeu)"))
    guid, name = _plan()
    if guid is None:
        out.append(Check("Mode d'alimentation", "info", name,
                         "Pas d'inquiétude : ouvre Démarrer > « Choisir un mode d'alimentation » et vérifie "
                         "que « Performances élevées » (ou Équilibré) est sélectionné pour jouer.",
                         settings="control:Microsoft.PowerOptions", location="Options d'alimentation (Panneau de configuration)"))
    elif guid in ("a1841308-3541-4fab-bc81-f71556f20b4a",):
        out.append(Check("Mode d'alimentation", "warn", name,
                         "Panneau de configuration > Options d'alimentation : choisis « Performances élevées » "
                         "pour jouer (surtout sur secteur). Sur portable, branche-le.",
                         settings="control:Microsoft.PowerOptions", location="Options d'alimentation (Panneau de configuration)"))
    else:
        out.append(Check("Mode d'alimentation", "ok", name, "",
                        settings="control:Microsoft.PowerOptions", location="Options d'alimentation (Panneau de configuration)"))
    dvr = registry.read("HKCU", r"System\GameConfigStore", "GameDVR_Enabled")
    out.append(Check("Enregistrement de jeu en arrière-plan (Captures)", "info" if dvr == 1 else "ok",
                     "Actif." if dvr == 1 else "Inactif.",
                     "Si tu n'enregistres pas tes parties : Paramètres > Jeux > Captures, désactive "
                     "« Enregistrer en arrière-plan » (gain de FPS possible, surtout sur PC modeste)." if dvr == 1 else "",
                     settings="gaming-gamedvr", location="Paramètres > Jeux > Captures"))
    hw = registry.read("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode")
    if hw == 2:
        etat_gpu, txt_gpu = "ok", T("Activée.")
    elif hw == 1:
        etat_gpu, txt_gpu = "info", T("Désactivée.")
    else:
        # Valeur absente = réglage par défaut du pilote : beaucoup de pilotes
        # récents l'activent d'office sans rien écrire dans le registre.
        # Windows peut donc l'afficher « activée » alors que la clé est absente.
        etat_gpu, txt_gpu = "info", ("Réglée par le pilote (valeur par défaut) : "
                                     "fie-toi à l'affichage de Windows.")
    out.append(Check("Planification GPU accélérée", etat_gpu, txt_gpu,
                     "Paramètres > Système > Affichage > Graphiques. Selon le jeu, l'effet peut être positif "
                     "ou négatif : teste, et garde ce qui marche le mieux.",
                     settings="display-advancedgraphics", location="Paramètres > Système > Affichage > Graphiques"))
    out += game_disk_checks(serenity)
    return out
