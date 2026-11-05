# -*- coding: utf-8 -*-
"""Instance unique et sensibilisation DPI.

Deux accidents reels evites ici :
  * deux fenetres ouvertes = deux rappels qui sonnent et une quarantaine
    manipulee par deux mains ;
  * un portable regle a 125 % qui rend TidyDeck tout flou parce que le
    processus n'a jamais declare qu'il sait lire le DPI.
"""
import ctypes
import os
import shutil
import tempfile
import unittest

from tests import ROOT  # noqa: F401

from Shared.Utils import instance


class InstanceUniqueTest(unittest.TestCase):
    def setUp(self):
        if os.name != "nt":
            self.skipTest("mutex Windows only")
        instance.liberer()
        if instance.deja_ouvert():
            self.skipTest("un TidyDeck deja ouvert sur cette machine holds the mutex")
        instance.liberer()   # la sonde precedente ne doit pas letenir le mutex

    def tearDown(self):
        instance.liberer()

    def test_premiere_ouverture_libre(self):
        self.assertFalse(instance.deja_ouvert())

    def test_seconde_ouverture_detectee(self):
        instance.deja_ouvert()
        self.assertTrue(instance.deja_ouvert(),
                        "un deuxieme TidyDeck doit etre refuse a l'ouverture")

    def test_apres_liberation_redevient_libre(self):
        instance.deja_ouvert()
        instance.liberer()
        self.assertFalse(instance.deja_ouvert(),
                        "le mutex doit se liberer quand le logiciel se ferme")

    def test_le_nom_du_mutex_n_est_pas_generique(self):
        from Shared.Utils.instance import _MUTEX
        self.assertIn("TidyDeck", _MUTEX, "un nom generique entrerair en conflit "
                                         "avec un autre logiciel")
        self.assertTrue(_MUTEX.startswith("Local\\"),
                        "Local\\ = par session : deux comptes connectes peuvent "
                        "chacun avoir leur TidyDeck")


class DpiTest(unittest.TestCase):
    def setUp(self):
        if os.name != "nt":
            self.skipTest("DPI Windows only")

    def testdpi_renvoie_un_vrai_nombre(self):
        d = instance.dpi_systeme()
        self.assertIsInstance(d, int)
        self.assertGreaterEqual(d, 96)
        self.assertLessEqual(d, 480)

    def test_activer_dpi_ne_casse_rien_et_est_idempotent(self):
        a = instance.activer_dpi()
        b = instance.activer_dpi()
        self.assertEqual(a, b)
        self.assertNotEqual(a, "non déclaré",
                           "si les deux API Windows echouent, le reste du code "
                           "n'est pas teste : le signaler plutot que passer inapercu")

    def test_main_declare_le_dpi_avant_de_creer_l_appli(self):
        src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
        self.assertLess(src.index("activer_dpi"), src.index("App("),
                        "SetProcessDpiAwareness apres tk.Tk() ne sert plus a rien")

    def test_app_declare_le_dpi_avant_tk(self):
        src = open(os.path.join(ROOT, "UI", "app.py"), encoding="utf-8").read()
        self.assertLess(src.index("instance.activer_dpi"), src.index("tk.Tk()"))


class PasDeDeuxiemeOuvertureDansLeCodeTest(unittest.TestCase):
    def test_main_sort_si_une_instance_exists(self):
        src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
        self.assertIn("deja_ouvert", src)
        self.assertIn("sys.exit", src)

    def test_lanceur_minimise_ne_sonne_pas_une_fenetre_de_dialogue(self):
        """Un lancement automatique qui trouverait une fenetre ouverte ne doit pas
        reveiller l'utilisateur avec une boite de dialogue."""
        src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
        self.assertIn("minimized", src)
        self.assertRegex(src.replace("\n", " "), r"if minimized:\s+return")


if __name__ == "__main__":
    unittest.main()
