# -*- coding: utf-8 -*-
"""La sélection du bas ne doit plus annoncer des Mo déjà rangés ; ce qui reste
(fichiers en cours d'utilisation) doit être expliqué à l'utilisateur."""
import os
import sys
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Shared.Utils import config, lang
from UI import theme
from UI import components
from UI.Pages.clean_page import CleanPage


def _item(id_, name, special=None, preselect=True):
    return SimpleNamespace(id=id_, name=name, what="", special=special,
                           preselect=preselect, simple=True, needs_admin=False)


def _res(item, size, blocked=None, count=3):
    return SimpleNamespace(item=item, size=size, blocked=blocked, count=count)


class _Ctx:
    advanced = True

    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.theme, self.status_colors, self.symbols = theme.apply(root, cfg)
        self.cache, self.loading, self.app = {}, set(), self

    def mask(self, t):
        return t

    def save(self):
        pass


class SelectionNettoyeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lang.set_lang("fr")
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.tmp = os.path.join(os.environ.get("TEMP", "."), "td_sel_test")
        os.makedirs(os.path.join(self.tmp, "TidyDeck"), exist_ok=True)
        self._old = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp
        self.cfg = config.load()
        self.cfg["serenity"] = False
        self.cfg["advanced"] = True
        self.page = CleanPage(self.root, _Ctx(self.root, self.cfg))
        self.items = [_item("temp_user", "Fichiers temporaires (utilisateur)"),
                      _item("chrome", "Cache Chrome")]
        self.page.items = self.items
        self.page.cards = {i.id: components.CleanCard(self.page.cards_frame, self.page.ctx, i)
                           for i in self.items}
        self.page.analyse = lambda: None      # aucun vrai scan pendant le test
        self._no_dialog = mock.patch("UI.Pages.clean_page.score_dialog", lambda *a, **k: None)
        self._no_dialog.start()
        self.addCleanup(self._no_dialog.stop)

    def tearDown(self):
        self.page.destroy()
        if self._old is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self._old

    def _coche(self, sizes):
        self.page.results = {i.id: _res(i, sizes[i.id]) for i in self.items}
        for iid, r in self.page.results.items():
            self.page.cards[iid].set_result(r)
            # L'analyse ne coche plus rien toute seule : ici, l'utilisateur coche.
            self.page.cards[iid].var.set(True)
        self.page._update_selection()

    def test_apres_nettoyage_plus_rien_de_coche(self):
        self._coche({"temp_user": 5 << 20, "chrome": 2 << 20})
        self.assertIn("7", self.page.sel_lbl.cget("text"))
        self.page._cleaned({"moved": 7 << 20, "n": 6, "skipped": 0,
                            "irreversible": 0, "pairs": None}, None)
        self.assertFalse(any(c.var.get() for c in self.page.cards.values()))
        self.assertEqual(self.page.sel_lbl.cget("text"), "Sélection : 0 o")

    def test_reste_explique_fichiers_utilises(self):
        self._coche({"temp_user": 5 << 20, "chrome": 2 << 20})
        self.page._cleaned_sel = ["temp_user", "chrome"]
        self.page._cleaned({"moved": 5 << 20, "n": 5, "skipped": 3,
                            "irreversible": 0, "pairs": None}, None)
        # re-scan : Chrome n'a pas pu tout déplacer (fichiers ouverts)
        self.page.results = {"temp_user": _res(self.items[0], 0),
                             "chrome": _res(self.items[1], 2 << 20)}
        for r in self.page.results.values():
            pass
        for iid, r in self.page.results.items():
            self.page.cards[iid].set_result(r)
        self.page._analysed(self.page.results, None)
        self.assertIn("programme ouvert", self.page.status.cget("text"))
        self.assertIn("utilisation", self.page.cards["chrome"].note_lbl.cget("text"))
        self.assertIn("2", self.page.sel_lbl.cget("text"))
        self.assertEqual(self.page.cards["temp_user"].note_lbl.cget("text"), "")

    def test_message_lance_parle_des_fichiers_utilises(self):
        msg = self.page._msg_apres_nettoyage({"moved": 1 << 20, "n": 2, "skipped": 4,
                                              "irreversible": 0, "pairs": None})
        self.assertIn("4 fichier", msg)
        self.assertIn("utilisation", msg)

    def test_message_en_anglais(self):
        lang.set_lang("en")
        try:
            msg = self.page._msg_apres_nettoyage({"moved": 1 << 20, "n": 2, "skipped": 4,
                                                  "irreversible": 0, "pairs": None})
            self.assertIn("4 file", msg)
            self.assertIn("in use", msg)
        finally:
            lang.set_lang("fr")


if __name__ == "__main__":
    unittest.main()
