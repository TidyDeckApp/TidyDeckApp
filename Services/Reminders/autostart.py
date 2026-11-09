"""Lancer TidyDeck avec Windows (réduit) : nécessaire pour que les rappels fonctionnent sans y penser.
Simple entrée « Run » de ton compte, visible et modifiable dans l'onglet Démarrage."""
import os
import re
import sys
from Shared.Utils import registry
from Services.Logger.journal import register_undo
from Shared.Utils.lang import T

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
NAME = "TidyDeck"


def command():
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        w = exe[:-10] + "pythonw.exe"
        exe = w if os.path.exists(w) else exe
    script = os.path.abspath(sys.argv[0])
    return f'"{exe}" "{script}" --minimized' if not getattr(sys, "frozen", False) else f'"{exe}" --minimized'


def is_enabled():
    return registry.read("HKCU", RUN, NAME) is not None


def cible():
    """Le fichier que l'entrée « Run » essaie de lancer ('' si aucune entrée)."""
    val = registry.read("HKCU", RUN, NAME) or ""
    m = re.match(r'^"([^"]+)"', val) or re.match(r"^([^\s]+)", val)
    return m.group(1) if m else ""


def entree_orpheline():
    """Vrai si l'entrée de démarrage pointe vers un fichier qui n'existe plus.

    Cas réel : l'utilisateur supprime le dossier TidyDeck à la main sans avoir
    décoché « Lancer avec Windows ». Windows rejoue alors une erreur à chaque
    démarrage, pour un logiciel qui n'est plus là."""
    c = cible()
    return bool(c) and not os.path.exists(c)


def reparer_entree_orpheline(journal=None):
    """Supprime l'entrée morte. Renvoie le chemin visé, ou '' s'il n'y avait rien
    à réparer. On le fait au démarrage : c'est le dernier moment où TidyDeck est
    encore présent pour nettoyer après lui."""
    if not entree_orpheline():
        return ""
    mort = cible()
    registry.delete("HKCU", RUN, NAME)
    if journal is not None:
        try:
            journal.add("autostart",
                       "Lancement automatique retiré : le fichier visé n'existait plus",
                       ("{v0} — valeur « {v1} » pointait sur « {v2} ». Windows aurait cherché "
                        "ce fichier à chaque démarrage."
                        ).format(v0=registry.full_path('HKCU', RUN), v1=NAME, v2=mort),
                       None)
        except Exception:
            from Shared.Utils import depannage
            depannage.noter("Services/Reminders/autostart.py:60")
    return mort


def set_enabled(on, journal):
    prev = registry.read("HKCU", RUN, NAME)
    if on:
        registry.write("HKCU", RUN, NAME, command(), kind=1)       # REG_SZ
    else:
        registry.delete("HKCU", RUN, NAME)
    ok = is_enabled() == on
    if ok:
        journal.add("autostart", "TidyDeck " + ("se lancera avec Windows (réduit)" if on else "ne se lance plus avec Windows"),
                    f"{registry.full_path('HKCU', RUN)} — valeur « {NAME} »", {"prev": prev})
    return ok


@register_undo("autostart")
def _undo(d):
    if d["prev"] is None:
        registry.delete("HKCU", RUN, NAME)
    else:
        registry.write("HKCU", RUN, NAME, d["prev"], kind=1)
    return "Lancement automatique de TidyDeck remis comme avant."
