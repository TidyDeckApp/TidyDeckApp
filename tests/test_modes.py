"""Mode Jeu et Mode Discret : independance stricte + banniere unique."""
import json
import os
import shutil
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Shared.Utils import lang


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage disponible")
class ModesIndependenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="td_modes_")
        self._saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp
        cfg = {"first_run": False, "theme": "sombre", "text_size": "normale",
               "colorblind": False, "advanced": True, "quarantine_days": 7,
               "serenity": False, "close_action": "minimize", "durations": {},
               "last_calm": "2026-01-01 00:00:00", "sound": False, "reminder": False,
               "stream_mode": False, "installed": "2026-01-01 00:00:00",
               "last_reminder": None, "toasts_prev": None, "game_mode_on": False,
               "meals_done": [], "express_mode": False, "custom_sound": "",
               "sound_volume": 0, "rdv_volume": 0, "toast_position": "bottom-right",
               "rdv_time": "", "rdv_at": "", "dnd_enabled": False,
               "reminders": {"hydration": {"on": False, "every": 60},
                            "meals": {"on": False, "lunch": "12:30", "dinner": "19:30",
                                       "snack_am_on": False, "snack_am": "10:30",
                                       "snack_pm_on": False, "snack_pm": "16:00",
                                       "extra_slots": []},
                            "eyes": {"on": False, "every": 20},
                            "stretch": {"on": False, "every": 90},
                            "defer": "wait", "auto_detect": False, "sound": False,
                            "dnd_enabled": False}}
        d = os.path.join(self.tmp, "TidyDeck")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        from UI.app import App
        self.app = App()
        lang.set_lang("fr")
        self.app.root.geometry("1200x750+0+0")
        self.app.root.deiconify()
        self.app.root.update()
        self.app.root.update_idletasks()

    def tearDown(self):
        try:
            self.app.root.destroy()
        except Exception:
            pass
        if self._saved is not None:
            os.environ["LOCALAPPDATA"] = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_both_off_no_banner(self):
        self.assertFalse(self.app.banner.shown)

    def test_game_only(self):
        self.app.ctx.cfg["game_mode_on"] = True
        self.app.banner.refresh()
        self.assertTrue(self.app.banner.shown)
        self.assertEqual([k for k, *_ in self.app.banner.active()], ["game_mode_on"])
        self.assertFalse(self.app.ctx.cfg["stream_mode"], "le discret ne doit pas s'activer tout seul")

    def test_discret_only(self):
        self.app.ctx.cfg["stream_mode"] = True
        self.app.banner.refresh()
        self.assertTrue(self.app.banner.shown)
        self.assertEqual([k for k, *_ in self.app.banner.active()], ["stream_mode"])
        self.assertFalse(self.app.ctx.cfg["game_mode_on"], "le jeu ne doit pas s'activer tout seul")

    def test_both_active_one_banner_two_buttons(self):
        self.app.ctx.cfg["game_mode_on"] = True
        self.app.ctx.cfg["stream_mode"] = True
        self.app.banner.refresh()
        self.app.root.update_idletasks()
        self.assertEqual(len(self.app.banner.active()), 2)
        self.assertEqual(len(self.app.banner.btns.winfo_children()), 2)
        self.assertEqual(self.app.banner.winfo_manager(), "pack")

    def test_exit_game_leaves_discret(self):
        self.app.ctx.cfg["game_mode_on"] = True
        self.app.ctx.cfg["stream_mode"] = True
        self.app.exit_mode("game_mode_on")
        self.assertFalse(self.app.ctx.cfg["game_mode_on"])
        self.assertTrue(self.app.ctx.cfg["stream_mode"], "le discret doit rester actif")
        self.app.root.update()
        self.assertTrue(self.app.banner.shown)
        self.assertEqual(len(self.app.banner.active()), 1)

    def test_exit_discret_leaves_game(self):
        self.app.ctx.cfg["game_mode_on"] = True
        self.app.ctx.cfg["stream_mode"] = True
        self.app.exit_mode("stream_mode")
        self.assertTrue(self.app.ctx.cfg["game_mode_on"], "le jeu doit rester actif")
        self.assertFalse(self.app.ctx.cfg["stream_mode"])
        self.app.root.update()
        self.assertTrue(self.app.banner.shown)

    def test_exit_is_one_click_no_dialog(self):
        """Aucune boite de confirmation sur la sortie : on sort direct."""
        from tkinter import messagebox
        called = []
        orig = messagebox.askyesno
        messagebox.askyesno = lambda *a, **k: (called.append(a), True)[1]
        try:
            self.app.ctx.cfg["game_mode_on"] = True
            self.app.banner.refresh()
            self.app.exit_mode("game_mode_on")
        finally:
            messagebox.askyesno = orig
        self.assertFalse(self.app.ctx.cfg["game_mode_on"])
        self.assertEqual(called, [], "la sortie ne doit JAMAIS demander de confirmation")

    def test_banner_is_unique(self):
        self.app.ctx.cfg["game_mode_on"] = True
        self.app.ctx.cfg["stream_mode"] = True
        self.app.banner.refresh()
        banners = [w for w in self.app.content.winfo_children()
                  if w.__class__.__name__ == "ModeBanner"]
        self.assertEqual(len(banners), 1)

    def test_banner_fits_under_30px(self):
        self.app.ctx.cfg["game_mode_on"] = True
        self.app.ctx.cfg["stream_mode"] = True
        self.app.banner.refresh()
        self.app.root.update()
        self.assertLessEqual(self.app.banner.winfo_reqheight(), 30,
                            "la banniere ne doit pas manger la hauteur des pages")

    def test_game_toggle_from_page_leaves_discret(self):
        self.app.ctx.cfg["stream_mode"] = True
        page = self.app.pages["Jeu et live"]
        page.toggle_mode()
        self.assertTrue(self.app.ctx.cfg["game_mode_on"])
        self.assertTrue(self.app.ctx.cfg["stream_mode"], "toggle jeu ne touche pas au discret")
        page.toggle_mode()
        self.assertFalse(self.app.ctx.cfg["game_mode_on"])
        self.assertTrue(self.app.ctx.cfg["stream_mode"])


if __name__ == "__main__":
    unittest.main()
