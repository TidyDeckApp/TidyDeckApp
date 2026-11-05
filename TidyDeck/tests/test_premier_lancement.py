"""Premier lancement : tout part désactivé, et le choix de la fenêtre
« Bienvenue » devient une préférence enregistrée pour les lancements suivants."""
import json
import os
import tempfile
import unittest

from Shared.Utils import config
from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Shared.Utils import lang

INTERUPTEURS = ("colorblind", "advanced", "serenity", "sound", "reminder",
                "stream_mode", "express_mode", "game_mode_on")


def _walk(w):
    yield w
    for c in w.winfo_children():
        yield from _walk(c)


class DefaultsToutDesactiveTest(unittest.TestCase):
    def test_tous_les_interupteurs_partent_desactives(self):
        for cle in INTERUPTEURS:
            self.assertFalse(config.DEFAULTS[cle],
                             f"« {cle} » doit être désactivé au premier lancement")

    def test_rappels_partent_desactives(self):
        r = config.DEFAULTS["reminders"]
        for cle in ("hydration", "eyes", "stretch"):
            self.assertFalse(r[cle]["on"], f"rappel « {cle} » ne doit pas partir activé")
        self.assertFalse(r["meals"]["snack_am_on"])
        self.assertFalse(r["meals"]["snack_pm_on"])
        self.assertFalse(r["sound"])
        self.assertFalse(r["auto_detect"])
        self.assertFalse(r["dnd_enabled"])


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage disponible")
class WelcomeEnregistreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="td_welcome_")
        self._saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp

    def tearDown(self):
        if self._saved is not None:
            os.environ["LOCALAPPDATA"] = self._saved
        else:
            os.environ.pop("LOCALAPPDATA", None)

    def test_choix_bienvenue_survivent_au_redemarrage(self):
        from UI.app import App
        from UI.PreInstall.appearance import AppearancePanel
        app = App()          # premier lancement : first_run forcé à False
        lang.set_lang("fr")
        try:
            self.assertTrue(app.ctx.cfg["first_run"] is False)
            win = next(w for w in app.root.winfo_children()
                       if w.winfo_class() == "Toplevel")
            panel = next(w for w in _walk(win) if isinstance(w, AppearancePanel))
            bouton = next(w for w in _walk(win)
                          if w.winfo_class() == "TButton"
                          and str(w.cget("text")) == "C'est parti")
            panel.vars["theme"].set("sombre")
            panel.vars["serenity"].set(True)
            panel.vars["sound"].set(True)
            bouton.invoke()
            app.root.update()
            chemin = os.path.join(self.tmp, "TidyDeck", "config.json")
            with open(chemin, encoding="utf-8") as fh:
                sauve = json.load(fh)
            self.assertEqual(sauve["theme"], "sombre")
            self.assertTrue(sauve["serenity"])
            self.assertTrue(sauve["sound"])
            self.assertFalse(sauve["first_run"])
            self.assertEqual(sauve["colorblind"], config.DEFAULTS["colorblind"])
        finally:
            try:
                app.root.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
