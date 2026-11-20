# -*- coding: utf-8 -*-
"""Lot B (visuel 0.6.2) : wraplength lié à la largeur du panneau, bouton
« Relancer » remonté dans la barre, espace icône Discret normalisé.

Tests mixtes : comportement tkinter (skipUnless affichage) + garde-fous source,
comme le reste de la suite.
"""
import os
import time
import unittest

from tests import HAS_DISPLAY  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))


def _src(*parties):
    p = os.path.join(HERE, *parties)
    with open(p, encoding="utf-8") as fh:
        return fh.read()


class AutoWrapTest(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from UI.components import auto_wrap
        self.auto_wrap = auto_wrap
        self.root = tk.Tk()
        self.root.geometry("500x300+0+0")

    def tearDown(self):
        self.root.destroy()

    def _run(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            time.sleep(0.01)

    def test_suit_la_largeur(self):
        import tkinter as tk
        lbl = tk.Label(self.root, text="x" * 400, justify="left")
        self.auto_wrap(lbl, delai=20)
        lbl.pack(fill="x", expand=True)
        self.root.update()
        self._run(0.3)
        self.root.update()
        w = lbl.winfo_width()
        self.assertGreater(w, 50)
        self.assertEqual(int(str(lbl.cget("wraplength"))), max(w - 4, 40))

    def test_plafond_maxi(self):
        import tkinter as tk
        lbl = tk.Label(self.root, text="y" * 10, justify="left")
        self.auto_wrap(lbl, delai=20, maxi=150)
        lbl.pack(fill="x", expand=True)
        self.root.update()
        self._run(0.3)
        self.root.update()
        self.assertEqual(int(str(lbl.cget("wraplength"))), 150)


class FlowFrameRightTest(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from UI.components import FlowFrame
        self.tk = tk
        self.root = tk.Tk()
        self.root.geometry("600x200+0+0")
        self.bar = FlowFrame(self.root)
        self.bar.pack(fill="x")
        self.root.update()
        self._run(0.2)

    def tearDown(self):
        self.root.destroy()

    def _run(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            time.sleep(0.01)

    def test_bouton_a_droite(self):
        a = self.tk.Button(self.bar, text="AAA")
        b = self.tk.Button(self.bar, text="BBB")
        c = self.tk.Button(self.bar, text="RELANCER")
        self.bar.add(a)
        self.bar.add(b)
        self.bar.add(c, right=True)
        self.root.update()
        self._run(0.3)
        self.root.update()
        width = self.bar.winfo_width()
        cx = int(c.place_info()["x"])
        self.assertGreater(cx, width - c.winfo_reqwidth() - 3)
        self.assertLess(cx, width)
        self.assertEqual(int(b.place_info()["x"]),
                         int(a.place_info()["x"]) + a.winfo_reqwidth() + 8)

    def test_groupe_droit_avant_apres(self):
        a = self.tk.Button(self.bar, text="AAA")
        stop = self.tk.Button(self.bar, text="STOP")
        rel = self.tk.Button(self.bar, text="RELANCER")
        self.bar.add(a)
        self.bar.add(rel, right=True)
        self.bar.add(stop, right=True, before=rel)
        self.root.update()
        self._run(0.3)
        self.root.update()
        width = self.bar.winfo_width()
        sx = int(stop.place_info()["x"])
        rx = int(rel.place_info()["x"])
        self.assertLess(sx, rx, "STOP doit precéder RELANCER dans le groupe de droite")
        self.assertGreaterEqual(rx + rel.winfo_reqwidth(), width - 3)

    def test_remove(self):
        a = self.tk.Button(self.bar, text="AAA")
        b = self.tk.Button(self.bar, text="BBB")
        self.bar.add(a)
        self.bar.add(b)
        self.root.update()
        self._run(0.2)
        self.bar.remove(b)
        self.root.update()
        self._run(0.2)
        self.assertEqual(b.winfo_manager(), "")
        self.assertNotEqual(a.winfo_manager(), "")


class VisuelSourceTest(unittest.TestCase):
    def test_discret_sans_variation_selector(self):
        src = _src("..", "UI", "Pages", "settings_page.py")
        line = [l for l in src.splitlines() if "Mode Discret" in l and "stream_mode" in l]
        self.assertTrue(line, "ligne Mode Discret introuvable")
        self.assertNotIn("\U0001F576\uFE0F", line[0],
                         "FE0F force la largeur emoji : retirer U+FE0F de la ligne Réglages")

    def test_storage_reparente_le_bouton(self):
        src = _src("..", "UI", "Pages", "storage_page.py")
        self.assertIn("bar=self.bar", src, "la vue doit créer ses boutons dans la barre")
        self.assertIn("right=True", src)

    def test_vue_isolee_garde_son_pack(self):
        for page in ("largest_view.py", "residus_view.py"):
            src = _src("..", "UI", "Pages", page)
            self.assertIn("if self._bar is None:", src, page)

    def test_vues_exposent_bar(self):
        for page in ("largest_view.py", "residus_view.py"):
            src = _src("..", "UI", "Pages", page)
            self.assertIn("_show_stop", src, page)
            self.assertIn("_hide_stop", src, page)

    def test_checks_en_largeur(self):
        src = _src("..", "UI", "Pages", "settings_page.py")
        self.assertIn("auto_wrap", src)
        build = src[src.index("def _check("):src.index("def _apply_common")]
        self.assertIn('fill="x"', build)

    def test_case_detect_jamais_en_pack_left(self):
        """Lot C2 : la case « Détecter le jeu / plein écran automatiquement »
        vit dans un FlowFrame et passe à la ligne — jamais un pack(side=left)
        qui la ferait couper au bord droit."""
        src = _src("..", "UI", "Pages", "settings_page.py")
        debut = src.index("dnd_row = FlowFrame")
        bloc = src[debut:src.index("Sans détection auto", debut)]
        self.assertNotIn('pack(side="left")', bloc,
                         "la rangée dnd ne doit plus packer en side=left")
        self.assertIn("dnd_row.add(ttk.Checkbutton", bloc,
                      "la case de détection doit être ajoutée au FlowFrame")


if __name__ == "__main__":
    unittest.main()
