"""Traduit les boîtes messagebox à un seul endroit (titre + message).

Les appels restent en français partout dans le code ; T() remplace seulement
quand la langue est « en ». Les titres « TidyDeck » (marque) sont laissés tels quels.
"""
from tkinter import messagebox as _mb

from Shared.Utils.lang import T

NOMS = ("showinfo", "showwarning", "showerror", "askyesno", "askyesnocancel")

_DEJA = False


def installe():
    global _DEJA
    if _DEJA:
        return
    _DEJA = True

    def _fabrique(orig):
        def _guide(title="TidyDeck", message="", *a, **k):
            if title != "TidyDeck":
                title = T(title)
            return orig(title, T(str(message)), *a, **k)
        return _guide

    for nom in NOMS:
        setattr(_mb, nom, _fabrique(getattr(_mb, nom)))
