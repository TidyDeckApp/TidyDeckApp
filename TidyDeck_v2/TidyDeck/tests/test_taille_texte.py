"""« Très grande » (1.5x) a ete supprime sur demande : la taille de texte ne
propose plus que Normale et Grande, partout ou elle etait proposee."""
import json
import os
import shutil
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Shared.Utils import lang

BASE_CFG = {
    "first_run": False, "theme": "clair", "text_size": "normale", "colorblind": False,
    "advanced": True, "quarantine_days": 7, "serenity": False, "close_action": "minimize",
    "durations": {}, "last_calm": "2026-01-01 00:00:00", "sound": False, "reminder": False,
    "stream_mode": False, "installed": "2026-01-01 00:00:00", "last_reminder": None,
    "toasts_prev": None, "game_mode_on": False, "meals_done": [], "express_mode": False,
    "custom_sound": "", "sound_volume": 70, "rdv_volume": 70, "toast_position": "bottom-right",
    "rdv_time": "", "rdv_at": "", "dnd_enabled": False,
    "reminders": {"hydration": {"on": False, "every": 60},
                  "meals": {"on": False, "lunch": "12:30", "dinner": "19:30",
                             "snack_am_on": False, "snack_am": "10:30",
                             "snack_pm_on": False, "snack_pm": "16:00", "extra_slots": []},
                  "eyes": {"on": False, "every": 20}, "stretch": {"on": False, "every": 90},
                  "defer": "wait", "auto_detect": False, "sound": False, "dnd_enabled": False},
}


class _Case(unittest.TestCase):
    def _with_cfg(self, **over):
        tmp = tempfile.mkdtemp(prefix="td_ts_")
        saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = tmp
        cfg = json.loads(json.dumps(BASE_CFG))
        cfg.update(over)
        d = os.path.join(tmp, "TidyDeck")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        return tmp, saved

    def _restore(self, tmp, saved):
        if saved is not None:
            os.environ["LOCALAPPDATA"] = saved
        else:
            os.environ.pop("LOCALAPPDATA", None)
        shutil.rmtree(tmp, ignore_errors=True)


class TailleTexteSupprimeeTest(_Case):
    def test_sizes_ne_contiennent_plus_tres_grande(self):
        from UI import theme
        self.assertEqual(set(theme.SIZES), {"normale", "grande"})
        self.assertNotIn("tres_grande", theme.SIZES)

    def test_profile_nautorise_plus_tres_grande(self):
        from UI.Profile.profile import CHOICES
        self.assertEqual(CHOICES["text_size"], {"normale", "grande"})

    def test_config_migre_une_ancienne_valeur(self):
        from Shared.Utils import config
        tmp, saved = self._with_cfg(text_size="tres_grande")
        try:
            self.assertEqual(config.load()["text_size"], "grande")
        finally:
            self._restore(tmp, saved)

    def test_theme_ne_casse_pas_sur_une_valeur_inconnue(self):
        import tkinter as tk
        from UI import theme
        root = tk.Tk()
        try:
            root.withdraw()
            for bad in ("tres_grande", "normale", "", None, "nimporte"):
                theme.apply(root, {"theme": "clair", "colorblind": False,
                                  "serenity": False, "text_size": bad})
        finally:
            root.destroy()

    def test_aucun_source_ne_mentionne_tres_grande(self):
        targets = [os.path.join("UI", "Pages", "settings_page.py"),
                   os.path.join("UI", "PreInstall", "appearance.py"),
                   os.path.join("UI", "theme.py"),
                   os.path.join("UI", "Profile", "profile.py")]
        for rel in targets:
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                src = fh.read()
            self.assertNotIn("tres_grande", src, f"{rel} mentionne encore tres_grande")
            self.assertNotIn("Très grande", src, f"{rel} propose encore « Très grande »")

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_page_theme_deux_tailles_seulement(self):
        tmp, saved = self._with_cfg(advanced=True)
        try:
            from UI.app import App
            app = App()
            lang.set_lang("fr")
            try:
                app.goto("Apparence et modes")
                app.root.update()
                labels = []

                def walk(w):
                    for c in w.winfo_children():
                        try:
                            labels.append(str(c.cget("text")))
                        except Exception:
                            pass
                        walk(c)
                walk(app.pages["Apparence et modes"])
                self.assertIn("Normale", labels)
                self.assertIn("Grande", labels)
                self.assertNotIn("Très grande", labels,
                                "« Très grande » est encore propose sur la page Theme")
            finally:
                try:
                    app.root.destroy()
                except Exception:
                    pass
        finally:
            self._restore(tmp, saved)


if __name__ == "__main__":
    unittest.main()
