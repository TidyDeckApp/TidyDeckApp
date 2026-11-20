"""Logique pure de l'interface « Visuel / Son » des rappels bien-être.

Aucun import tkinter : ces fonctions sont testables partout, headless,
sans dépendre de la construction d'une page.
"""


def banner_utile(r, rdv_actif=False):
    """Vrai si au moins un rappel (ou le minuteur RDV) est actif : le bandeau
    « TidyDeck doit rester ouvert » est alors affiché. r est le dictionnaire
    « reminders » de la config."""
    if rdv_actif:
        return True
    for key in ("hydration", "eyes", "stretch"):
        if r.get(key, {}).get("on"):
            return True
    m = r.get("meals", {})
    if m.get("on") or m.get("snack_am_on") or m.get("snack_pm_on"):
        return True
    return any(e.get("on") for e in m.get("extra_slots", []))


def apply_visible(on_flags):
    """Le lien « Appliquer à tous les rappels » n'a de sens qu'à partir de
    deux rappels activés."""
    return sum(1 for x in on_flags if x) >= 2
