# -*- coding: utf-8 -*-
"""Lot F : phrase douce du minuteur RDV muet + placement de la phrase
« Sans notification ni son » directement sous la ligne du rappel.

Garde-fous source + vérification de la traduction EN, comme les lots D.
"""
import json
import os
import shutil
import tempfile
import tkinter as tk
import unittest

from Shared.Utils import lang
from tests import HAS_DISPLAY
from tests.test_round3 import BASE_CFG

HERE = os.path.dirname(os.path.abspath(__file__))
PHRASE_RDV = "Aucune alerte : le minuteur ne te préviendra pas."
PHRASE_RAPPEL = "Sans notification ni son, tu ne verras rien."


def _src(*parties):
    p = os.path.join(HERE, *parties)
    with open(p, encoding="utf-8") as fh:
        return fh.read()


class RdvSilencieuxTest(unittest.TestCase):
    def setUp(self):
        self.src = _src("..", "UI", "Pages", "reminders_page.py")

    def test_la_phraseexiste_dans_la_page(self):
        self.assertIn(PHRASE_RDV, self.src,
                      "la phrase douce RDV doit exister dans la page Rappels")

    def test_affichee_uniquement_les_deux_cases_decochees(self):
        debut = self.src.index("def refresh_rdv_soft")
        bloc = self.src[debut:self.src.index("refresh_rdv_soft()", debut + 60)]
        self.assertIn("if not self.rdv_visual.get() and not self.rdv_sound.get():", bloc,
                      "la phrase doit dépendre des deux cases, pas d'une seule")
        self.assertIn("self.rdv_soft.pack(anchor=\"w\", after=fr_notif)", bloc,
                      "la phrase doit se loger sous la rangée des cases")
        self.assertNotIn("after=fr)", bloc,
                         "after=fr suivrait la dernière réassignation de fr (bug lot F : "
                         "la phrase partait sous « Volume du son RDV »)")
        self.assertIn("self.rdv_soft.pack_forget()", bloc)

    def test_rangee_notif_capturee_une_seule_fois(self):
        # « fr_notif » ne doit être affecté qu'une fois : la fermeture du
        # closure doit rester scellée sur la rangée « Notification RDV : ».
        debut = self.src.index("def refresh_rdv_soft")
        bloc = self.src[debut:self.src.index("refresh_rdv_soft()", debut + 60)]
        self.assertEqual(self.src.count("fr_notif = "), 1,
                         "une seule affectation de fr_notif (la rangée Notification RDV)")
        self.assertIn("fr_notif = row(", self.src)
        self.assertNotIn("cfg", bloc,
                         "le minuteur ne doit rien écrire : seule l'affichage change")
        self.assertIn("self.rdv_visual.trace_add(\"write\", refresh_rdv_soft)", self.src)
        self.assertIn("self.rdv_sound.trace_add(\"write\", refresh_rdv_soft)", self.src)

    def test_traduction_anglaise(self):
        from Shared.Utils import lang
        try:
            lang.set_lang("en")
            self.assertEqual(lang.T(PHRASE_RDV),
                             "No alert: the timer won't notify you.")
        finally:
            lang.set_lang("fr")


class PlacementSoftTest(unittest.TestCase):
    def test_phrase_attachee_apres_sa_rangee(self):
        src = _src("..", "UI", "Pages", "reminders_page.py")
        debut = src.index("def _notif_ui(")
        bloc = src[debut:src.index("def _apply_all_notif", debut)]
        self.assertIn('soft.pack(anchor="w", pady=(0, 2), after=fr)', bloc,
                      "la phrase doit être packée juste sous la rangée du rappel (after=fr)")
        self.assertIn(PHRASE_RAPPEL, bloc)


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
class PlacementEcranTest(unittest.TestCase):
    """Lot G : après un cochage/décochage des cases RDV, la phrase « Aucune
    alerte… » doit rester sous la rangée « Notification RDV : ». En thème
    sombre, le lot F la faisait filer en bas de page (bug Florent) : la
    closure suivait la dernière réassignation de fr (« Volume du son RDV »)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="td_g_")
        self._saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp
        cfg = json.loads(json.dumps(BASE_CFG))
        cfg.update({"theme": "sombre", "lang": "fr", "rdv_notif": "none"})
        d = os.path.join(self.tmp, "TidyDeck")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        from UI.app import App
        self.app = App()
        lang.set_lang("fr")
        self.app.root.geometry("1000x700+0+0")
        self._pump(60)

    def tearDown(self):
        try:
            self.app.root.destroy()
        except tk.TclError:
            pass
        if self._saved is not None:
            os.environ["LOCALAPPDATA"] = self._saved
        else:
            os.environ.pop("LOCALAPPDATA", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _pump(self, n=30):
        for _ in range(n):
            self.app.root.update()
        self.app.root.update_idletasks()

    def _rangee_notif(self, page):
        stack = [page]
        while stack:
            w = stack.pop()
            try:
                t = w.cget("text")
            except tk.TclError:
                t = ""
            if isinstance(t, str) and t.startswith("Notification RDV"):
                return w.master
            stack.extend(w.winfo_children())
        self.fail("rangée « Notification RDV : » introuvable")

    def _apres_rangee(self, page, rangee):
        slaves = page.rdv_soft.master.pack_slaves()
        return slaves.index(page.rdv_soft) == slaves.index(rangee) + 1

    def test_phrase_reste_sous_la_rangee_meme_apres_cochage(self):
        self.app.goto("Rappels bien-être")
        self._pump(60)
        page = self.app.pages["Rappels bien-être"]
        rangee = self._rangee_notif(page)
        self.assertTrue(self._apres_rangee(page, rangee),
                        "au chargement, la phrase doit suivre la rangée Notification RDV")
        y_rangee = rangee.winfo_y()
        page.rdv_visual.set(True)
        self._pump()
        page.rdv_visual.set(False)
        self._pump()
        self.assertTrue(self._apres_rangee(page, rangee),
                        "après cocher/décocher, la phrase doit rester sous la "
                        "rangée Notification RDV (bug lot F : elle filait en bas)")
        self.assertGreaterEqual(page.rdv_soft.winfo_y(), y_rangee,
                                "la phrase s'affiche bien sous sa rangée")
        self.assertLess(page.rdv_soft.winfo_y(), y_rangee + 60,
                        "la phrase est collée sous sa rangée, pas en bas de page")


if __name__ == "__main__":
    unittest.main()
