# -*- coding: utf-8 -*-
"""Typographie : l'apostrophe doit rester droite (').

Les noms de reglages s'affichent dans des labels Tk, se copient dans le
presse-papiers et se collent dans un terminal : l'apostrophe typographique
« ' » (U+2019) s'y affiche mal et ne se cherche pas au clavier francais.
La convention du projet est donc l'apostrophe droite, partout.

Ce test balaie tout le code livre dans le zip : un seul caractere courbe
trouve fait rougir la build.
"""
import os
import unittest

from tests import ROOT

COURBES = {"\u2019": "apostrophe courbe ' (U+2019)",
           "\u2018": "guillemet simple ouvrant ' (U+2018)"}
REPERTOIRES = ("UI", "Core", "Shared", "Services", "vendor")
RACINE = ("main.py", "README.md", "DISTRIBUTION.md")


def _fichiers_a_balayer():
    for d in REPERTOIRES:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in files:
                if f.endswith((".py", ".md", ".json", ".txt")):
                    yield os.path.join(root, f)
    for f in RACINE:
        p = os.path.join(ROOT, f)
        if os.path.isfile(p):
            yield p


class TypographieTest(unittest.TestCase):
    def test_aucune_apostrophe_courbe_dans_le_projet(self):
        fautifs = []
        for p in _fichiers_a_balayer():
            try:
                with open(p, encoding="utf-8") as fh:
                    for n, ligne in enumerate(fh, 1):
                        for c, nom in COURBES.items():
                            if c in ligne:
                                fautifs.append(f"{os.path.relpath(p, ROOT)}:{n} {nom}")
            except (OSError, UnicodeDecodeError):
                continue
        self.assertEqual(fautifs, [],
                         "utilise ' (apostrophe droite) : " + "; ".join(fautifs[:12]))

    def test_les_noms_de_reglages_sont_en_apostrophe_droite(self):
        from Core.Tweaks import tweaks
        noms = [t.name for t in tweaks.TWEAKS]
        self.assertTrue(noms, "liste de reglages vide")
        mauvais = [n for n in noms if any(c in n for c in COURBES)]
        self.assertEqual(mauvais, [], f"noms avec apostrophe courbe : {mauvais}")

    def test_la_convention_est_bien_visible_dans_les_noms(self):
        from Core.Tweaks import tweaks
        avec_apos = [t.name for t in tweaks.TWEAKS if "'" in t.name]
        self.assertGreater(len(avec_apos), 0,
                          "l'apostrophe droite doit etre effectivement utilisee dans les noms")


if __name__ == "__main__":
    unittest.main()
