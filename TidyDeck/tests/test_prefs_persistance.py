"""Un réglage changé dans « Configuration » doit devenir une préférence :
fermer puis relancer TidyDeck le retrouve tel quel (mode Discret, Son,
Rappel, Ne pas déranger…)."""
import os
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401


class PersistanceConfigTest(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("LOCALAPPDATA")
        self.tmp = tempfile.mkdtemp()
        os.environ["LOCALAPPDATA"] = self.tmp

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self._saved

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def _page(self):
        import tkinter as tk
        from Shared.Utils import config
        from UI import theme as theme_mod
        from UI.Pages.settings_page import ConfigPage

        cfg = config.load()
        cfg["stream_mode"] = False
        cfg["reminders"]["dnd_enabled"] = False

        class C:
            journal = None
            advanced = True

            def __init__(self):
                self.cfg = cfg
                self.theme, self.status_colors, self.symbols = theme_mod.apply(root, cfg)

            def save(self):
                config.save(self.cfg)

        root = tk.Tk()
        root.withdraw()
        ctx = C()
        ctx.root = root
        page = ConfigPage(root, ctx, on_apply=lambda prev: ctx.save())
        page.after = lambda _ms, fn: fn()  # la « debounce » de 250 ms devient immédiate
        return root, ctx, page

    def test_mode_discret_survit_au_redemarrage(self):
        from Shared.Utils import config
        root, ctx, page = self._page()
        try:
            page.vars["stream_mode"].set(True)
            relu = config.load()
            self.assertTrue(relu["stream_mode"],
                            "le Mode Discret doit être enregistré comme préférence")
        finally:
            root.destroy()

    def test_ne_pas_deranger_survit_au_redemarrage(self):
        from Shared.Utils import config
        root, ctx, page = self._page()
        try:
            page.dnd_var.set(True)
            relu = config.load()
            self.assertTrue(relu["reminders"]["dnd_enabled"],
                            "« Ne pas déranger » doit être enregistré comme préférence")
        finally:
            root.destroy()

    def test_son_rappel_et_fenetre_survivent(self):
        from Shared.Utils import config
        root, ctx, page = self._page()
        try:
            page.vars["sound"].set(False)
            page.vars["reminder"].set(False)
            page.vars["close_action"].set("quit")
            relu = config.load()
            self.assertFalse(relu["sound"])
            self.assertFalse(relu["reminder"])
            self.assertEqual(relu["close_action"], "quit")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
