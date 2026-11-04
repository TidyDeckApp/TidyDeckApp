# -*- coding: utf-8 -*-
"""#42 : le compte « trouvés, dont actifs » du Démarrage doit coller au Gestionnaire
des tâches. Bytes StartupApproved impairs = désactivés (Windows écrit parfois 7,
pas seulement 3), un exe disparu compte comme « introuvable » (jamais actif),
doublons UWP fusionnés."""
import os
import tempfile
import unittest
from unittest import mock

from Core.Startup import startup


class IsDisabledTest(unittest.TestCase):
    def _etat(self, octet):
        with mock.patch.object(startup.registry, "read",
                               lambda h, k, n: bytes([octet]) + b"\x00" * 11):
            return startup.is_disabled("HKCU", "cle", "x")

    def test_valeur_clasique_3_desactive(self):
        self.assertTrue(self._etat(3))

    def test_valeur_impaire_7_desactive(self):
        self.assertTrue(self._etat(7))

    def test_pair_inconnu_jamais_actif(self):
        self.assertTrue(self._etat(6))

    def test_valeur_2_actif(self):
        self.assertFalse(self._etat(2))

    def test_absent_considere_active(self):
        with mock.patch.object(startup.registry, "read", lambda h, k, n: None):
            self.assertFalse(startup.is_disabled("HKCU", "cle", "x"))


def _entrees_simulees(tmp):
    vivant = os.path.join(tmp, "vivant.exe")
    open(vivant, "wb").close()
    mort = os.path.join(tmp, "plus_la.exe")
    etats = {("HKCU", startup.APPR + r"\Run", "Vivant"): b"\x02" + b"\x00" * 11,
             ("HKCU", startup.APPR + r"\Run", "Ancien3"): b"\x03" + b"\x00" * 11,
             ("HKCU", startup.APPR + r"\Run", "Bizarre7"): b"\x07" + b"\x00" * 11,
             ("HKCU", startup.APPR + r"\Run", "Fantome"): b"\x02" + b"\x00" * 11}

    def fake_list_values(hive, key):
        if hive == "HKCU" and key.endswith(r"\Run") and "WOW" not in key:
            return [("Vivant", f'"{vivant}"'), ("Ancien3", "x"), ("Bizarre7", "y"),
                    ("Fantome", f'"{mort}"')]
        return []

    def fake_read(hive, key, name):
        return etats.get((hive, key, name))

    uwp_twice = [
        {"kind": "uwp", "hive": "HKCU", "name": "Mobile connecté (Lien avec Windows)",
         "command": "x", "key": "k1", "approved": None, "scope": "s", "where": "w",
         "hint": "h", "level": "safe", "enabled": True, "policy": False},
        {"kind": "uwp", "hive": "HKCU", "name": "Mobile connecté (Lien avec Windows)",
         "command": "x", "key": "k2", "approved": None, "scope": "s", "where": "w",
         "hint": "h", "level": "safe", "enabled": True, "policy": False},
    ]
    with mock.patch.object(startup.registry, "list_values", fake_list_values), \
            mock.patch.object(startup.registry, "read", fake_read), \
            mock.patch.object(startup.registry, "full_path", lambda h, k: "w"), \
            mock.patch.object(startup, "dossiers_demarrage", lambda: []), \
            mock.patch.object(startup, "_uwp_entries", lambda: list(uwp_twice)):
        return startup.list_entries()


class CompteDemarrageTest(unittest.TestCase):
    def test_compte_sur_liste_simulee(self):
        with tempfile.TemporaryDirectory() as tmp:
            entries = _entrees_simulees(tmp)
            par = {e["name"]: e for e in entries}
            self.assertIn("Vivant", par)
            self.assertTrue(par["Vivant"]["enabled"])
            self.assertFalse(par["Ancien3"]["enabled"])
            self.assertFalse(par["Bizarre7"]["enabled"])
            self.assertTrue(par["Fantome"].get("missing"))
            self.assertFalse(par["Fantome"]["enabled"])
            mobiles = [e for e in entries if e["name"].startswith("Mobile connecté")]
            self.assertEqual(len(mobiles), 1, "doublon UWP non fusionné")
            actifs = {e["name"] for e in entries if e["enabled"]}
            self.assertEqual(actifs, {"Vivant", "Mobile connecté (Lien avec Windows)"})
            self.assertEqual((len(entries), len(actifs)), (5, 2))


class ExeExisteTest(unittest.TestCase):
    """#42 bis : un chemin sans guillemets mais avec des espaces (C:\\Program Files\\...)
    ne doit plus être un faux « introuvable » : on teste les préfixes croissants + .exe."""

    def test_chemin_espace_sans_guillemets(self):
        with tempfile.TemporaryDirectory() as tmp:
            dossier = os.path.join(tmp, "Program Files")
            os.makedirs(dossier)
            exe = os.path.join(dossier, "app.exe")
            open(exe, "wb").close()
            self.assertTrue(startup._exe_existe(exe + " -min"))
            self.assertTrue(startup._exe_existe(f'"{exe}" -min'))
            self.assertFalse(startup._exe_existe(os.path.join(dossier, "absent.exe") + " -min"))
            self.assertTrue(startup._exe_existe("https://x.example"))
            self.assertTrue(startup._exe_existe("notepad"))


if __name__ == "__main__":
    unittest.main()
