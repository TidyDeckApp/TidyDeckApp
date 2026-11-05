"""Texte d'attente : idle() doit effacer le minuteur de busy(), et la jauge
disque « jeux » doit renvoyer une phrase complete (sans « de quoi installer » en double)."""
import os
import shutil
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401


class IdleEffaceMinuteur(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("LOCALAPPDATA")
        self.tmp = tempfile.mkdtemp(prefix="td_idle_")
        os.environ["LOCALAPPDATA"] = self.tmp

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_idle_vide_le_status_apres_busy(self):
        import tkinter as tk
        from Shared.Utils import config
        from UI import theme as theme_mod
        from UI.Pages.base import Page

        root = tk.Tk()
        root.withdraw()
        cfg = config.load()
        cfg["durations"] = {}
        cfg["sound"] = False

        class C:
            journal = None
            advanced = True

            def __init__(self):
                self.cfg = cfg
                self.theme, self.status_colors, self.symbols = theme_mod.apply(root, cfg)

            def save(self):
                config.save(self.cfg)

            def mask(self, t):
                return t

        ctx = C()
        ctx.root = root
        page = Page(root, ctx, "Test attente")
        page.after = lambda _ms, fn: None      # gele le minuteur du test
        page.busy("Analyse", "test_key")
        page._tick()
        self.assertIn("Analyse", page.status.cget("text"))
        page.idle()
        self.assertEqual(page.status.cget("text"), "")
        root.destroy()

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_say_apres_idle_garde_son_message(self):
        import tkinter as tk
        from Shared.Utils import config
        from UI import theme as theme_mod
        from UI.Pages.base import Page

        root = tk.Tk()
        root.withdraw()
        cfg = config.load()
        cfg["durations"] = {}
        cfg["sound"] = False

        class C:
            journal = None
            advanced = True

            def __init__(self):
                self.cfg = cfg
                self.theme, self.status_colors, self.symbols = theme_mod.apply(root, cfg)

            def save(self):
                config.save(self.cfg)

            def mask(self, t):
                return t

        ctx = C()
        ctx.root = root
        page = Page(root, ctx, "Test attente")
        page.after = lambda _ms, fn: None
        page.busy("Analyse", "test_key")
        page.idle()
        page.say("Bravo, terminé.")
        self.assertIn("terminé", page.status.cget("text"))
        root.destroy()


class JaugeJeuxDisque(unittest.TestCase):
    def _g(self, gb):
        from UI.Pages.info_pc_page import InfoPCPage
        return InfoPCPage._games_gauge(None, gb * (1 << 30))

    def test_grand_espacement(self):
        s = self._g(300)
        self.assertEqual(s.count("de quoi installer"), 1)
        self.assertIn("AAA", s)

    def test_petit_jeu(self):
        s = self._g(40)
        self.assertEqual(s.count("de quoi installer"), 1)
        self.assertIn("petit jeu", s)

    def test_tres_peu_de_place(self):
        s = self._g(5)
        self.assertNotIn("de quoi installer", s)
        self.assertIn("très peu de place", s)

    def test_l_appel_ajoute_plus_le_prefixe(self):
        src = open(os.path.join(ROOT, "UI", "Pages", "info_pc_page.py"), encoding="utf-8").read()
        self.assertNotIn('f"de quoi installer {self._games_gauge', src)
