# -*- coding: utf-8 -*-
"""Lot D (visuel 0.6.2) : garde-fous source des correctifs à 900 px.

Réglages : les cases à cocher replient avec une marge (indicateur ~24 px) et
la note du volume vit sur sa propre ligne. Rappels : les lignes de rappels et
les créneaux personnalisés passent en FlowFrame (retour à la ligne) au lieu
d'être coupées au bord droit.
"""
import os
import unittest

from tests import HAS_DISPLAY  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))


def _src(*parties):
    p = os.path.join(HERE, *parties)
    with open(p, encoding="utf-8") as fh:
        return fh.read()


class ReglagesSourceTest(unittest.TestCase):
    def test_checks_en_wrap_with_marge(self):
        src = _src("..", "UI", "Pages", "settings_page.py")
        self.assertEqual(src.count("auto_wrap(cb, marge=28, maxi=820)"), 2,
                         "_check et _check_var doivent toutes deux wrap avec marge=28")

    def test_note_volume_sur_ligne_propre(self):
        src = _src("..", "UI", "Pages", "settings_page.py")
        debut = src.index("Volume du carillon")
        bloc = src[debut:src.index("self.sound_lbl", debut)]
        self.assertIn("ttk.Label(f,", bloc,
                      "la note de volume doit être enfant de la page, pas du curseur")
        self.assertNotIn("vol_row", bloc[bloc.index("aucun son"):],
                         "la note ne doit plus être packée à droite du curseur")
        self.assertIn('.pack(fill="x", padx=24)', bloc,
                      "la note doit prendre la largeur de la page")


class RappelsSourceTest(unittest.TestCase):
    def setUp(self):
        self.src = _src("..", "UI", "Pages", "reminders_page.py")

    def test_flux_importe(self):
        self.assertIn("FlowFrame", self.src, "reminders_page doit importer FlowFrame")

    def test_lignes_rappels_en_flowframe(self):
        debut = self.src.index("def frow(")
        bloc = self.src[debut:self.src.index("def put(", debut)]
        self.assertIn("FlowFrame(f)", bloc, "frow() doit retourner un FlowFrame")
        self.assertIn('fr.pack(fill="x"', bloc, "les lignes doivent remplir la largeur")
        self.assertEqual(self.src.count("= frow()"), 6,
                         "les 6 lignes de rappels fixes passent par frow()")

    def test_bloc_notif_jamais_pack_right(self):
        self.assertIn("fr.add(nf, right=True)", self.src,
                      "le bloc Son/Visuel doit être ajouté au FlowFrame à droite")
        self.assertIn("fr.remove(nf)", self.src)
        self.assertNotIn('nf.pack(side="right")', self.src,
                         "plus de pack(side=right) : le FlowFrame gère le repli")

    def test_creneaux_personnalises_en_flowframe(self):
        debut = self.src.index("def _build_extra_slot(")
        bloc = self.src[debut:self.src.index("def _add_extra_slot(", debut)]
        self.assertIn("FlowFrame(parent)", bloc)
        self.assertIn('box.pack(fill="x"', bloc)
        self.assertIn("box.add(nf, right=True)", bloc)
        self.assertIn("show_nf(), self._autosave()", bloc,
                      "les cases Son/Visuel d'un créneau perso doivent sauvegarder")

    def test_slots_frame_en_largeur(self):
        self.assertIn('self._slots_frame.pack(fill="x", anchor="w")', self.src,
                      "les créneaux personnalisés doivent remplir la largeur "
                      "(sinon le FlowFrame enfant mesure 1 px)")


if __name__ == "__main__":
    unittest.main()
