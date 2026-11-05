"""TidyDeck — point d'entrée.  Lancer :  python main.py   (Python 3.10+, aucune dépendance)
Option : --minimized  (démarre réduit dans la barre des tâches, utilisé par le lancement avec Windows)
Version empaquetee : TidyDeck.exe (PyInstaller, Python 3.12) — voir DISTRIBUTION.md"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Shared.Utils import instance  # noqa: E402


def _avertir_deja_ouvert(minimized):
    """Rien ne se passe en silencieux lance par Windows ; sinon on ramene la
    fenetre existante, a defaut on le dit."""
    if minimized:
        return
    if instance.ramener_existant():
        return
    try:
        import tkinter as tk
        from tkinter import messagebox
        from Shared.Utils import config
        r = tk.Tk()
        r.withdraw()
        from Shared.Utils.common import appliquer_icone
        appliquer_icone(r)
        from Shared.Utils import tkmsg
        from Shared.Utils.lang import set_lang
        set_lang(config.load().get("lang", "fr"))
        tkmsg.installe()
        messagebox.showinfo("TidyDeck",
                           "TidyDeck est déjà ouvert dans une autre fenêtre.\n\n"
                           "Deux instances en même temps se marcheraient sur les pieds "
                           "(deux rappels, une seule quarantaine) : c'est la première qui "
                           "continue.")
        r.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    instance.activer_dpi()          # avant tk.Tk(), sinon tout reste flou a 125/150 %
    if instance.deja_ouvert():
        if "--relance-admin" in sys.argv:
            # Relance elevee : l'ancienne fenetre n'a pas encore rendu son mutex.
            # On l'attend jusqu'a 8 s au lieu de se croire « deja ouvert ».
            if not instance.attendre_instance_libre(8.0):
                _avertir_deja_ouvert("--minimized" in sys.argv)
                sys.exit(0)
        else:
            _avertir_deja_ouvert("--minimized" in sys.argv)
            sys.exit(0)
    from UI.app import App
    App(minimized="--minimized" in sys.argv).run()
