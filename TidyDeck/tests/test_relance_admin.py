"""Relance « en administrateur » : le vrai interpreteur (jamais l'alias du
Microsoft Store), des chemins absolus, et un enfant élevé qui attend le mutex
du parent au lieu de se croire « déjà ouvert »."""
import os
import sys
import unittest
from unittest import mock

from Shared.Utils import common, instance


class AliasStoreTest(unittest.TestCase):
    def test_alias_windowsapps_reconnu(self):
        self.assertTrue(common._alias_windowsapps(
            r"C:\Program Files\WindowsApps\PythonSoftwareFoundation.PythonManager_315\python.exe"))
        self.assertFalse(common._alias_windowsapps(
            r"C:\Users\x\AppData\Local\Python\pythoncore-3.15-64\python.exe"))

    def test_interpreteur_reel_existant_jamais_alias(self):
        exe = common._interpreteur_eleve()
        self.assertTrue(exe and os.path.exists(exe))
        self.assertFalse(common._alias_windowsapps(exe))
        self.assertIn(os.path.basename(exe).lower(), ("python.exe", "pythonw.exe"))


class ParametresRelanceTest(unittest.TestCase):
    SCRIPT = os.path.abspath(os.path.join("sous", "dossier", "main.py"))

    def _relance(self, rc):
        appel = {}

        def le_shell(_h, verbe, exe, params, cwd, _show):
            appel.update(verbe=verbe, exe=exe, params=params, cwd=cwd)
            return rc

        with mock.patch.object(sys, "argv", [self.SCRIPT]), \
                mock.patch("ctypes.windll") as windll:
            windll.shell32.ShellExecuteW.side_effect = le_shell
            return common.relaunch_as_admin(), appel

    def test_runas_chemins_absolus_et_marqueur(self):
        ok, appel = self._relance(42)
        self.assertTrue(ok)
        self.assertEqual(appel["verbe"], "runas")
        self.assertTrue(os.path.isabs(appel["exe"]))
        self.assertTrue(os.path.isabs(appel["cwd"]))
        self.assertIn("--relance-admin", appel["params"])
        self.assertIn(self.SCRIPT, appel["params"])

    def test_access_refuse_retourne_faux(self):
        ok, _ = self._relance(5)               # SE_ERR_ACCESSDENIED (UAC refusé)
        self.assertFalse(ok)


class AttenteMutexTest(unittest.TestCase):
    """L'enfant élevé ne doit plus croire « déjà ouvert » pendant que le
    parent meurt : attendre_instance_libre prend le mutex dès qu'il se libère."""

    def setUp(self):
        instance.liberer()

    def test_mutex_libre_est_pris(self):
        if not instance.attendre_instance_libre(1.0):
            self.skipTest("un vrai TidyDeck est ouvert sur cette machine")
        instance.liberer()
        self.assertTrue(instance.attendre_instance_libre(1.0))


if __name__ == "__main__":
    unittest.main()
