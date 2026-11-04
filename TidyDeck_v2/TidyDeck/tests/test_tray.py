# -*- coding: utf-8 -*-
"""Option « réduire à côté de l'horloge » (zone de notification / tray).

Le comportement existing (réduire dans la barre des tâches) reste le defaut ;
une case a cocher permet de passer par l'icone pres de l'horloge, avec retour
par double-clic. Zero dependance : ctypes seul (UI/tray.py).
"""
import os
import unittest

from tests import ROOT  # noqa: F401

from Shared.Utils import config
from UI.Profile import profile


class ConfigDefaultTest(unittest.TestCase):
    def test_tray_exists_et_teint_par_defaut(self):
        import inspect
        import Shared.Utils.config as c
        src = inspect.getsource(c)
        self.assertIn('"tray": False', src, "la nouvelle option doit exister par defaut a off")


class ProfileSanitizeTest(unittest.TestCase):
    def test_tray_exporte_et_valide(self):
        self.assertIn("tray", profile.EXPORT_KEYS)
        self.assertIn("tray", profile.BOOL_KEYS)
        ok, skipped = profile.sanitize({"tray": "pas un booleen"})
        self.assertNotIn("tray", ok)
        ok, skipped = profile.sanitize({"tray": True})
        self.assertEqual(ok.get("tray"), True)


class TrayModuleTest(unittest.TestCase):
    def test_module_tray_importable_sans_dependance(self):
        from UI import tray
        self.assertTrue(hasattr(tray, "afficher") and hasattr(tray, "retirer"))
        self.assertTrue(hasattr(tray, "events") and hasattr(tray, "visible"))

    def test_cordiste_app_branche_le_tray(self):
        src = open(os.path.join(ROOT, "UI", "app.py"), encoding="utf-8").read()
        self.assertIn("tray", src)
        self.assertIn("withdraw", src, "reduire a cote de l'horloge = fenetre masquee")


if __name__ == "__main__":
    unittest.main()
