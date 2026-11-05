# -*- coding: utf-8 -*-
"""Refus de Windows : le message doit dire la vraie cause et la conduite a tenir.

Cas critique : le PC d'entreprise. Une ecriture refusee ALORS QU'ON EST ADMIN
n'est pas un probleme de droits, c'est une regle de groupe. Dire « relance en
admin » dans ce cas la envoye l'utilisateur dans un mur.
"""
import unittest

from tests import ROOT  # noqa: F401

from Shared.Utils import refus


class MotifRefusTest(unittest.TestCase):
    def setUp(self):
        from Shared.Utils import common
        self.common = common
        self._admin = common.is_admin

    def tearDown(self):
        self.common.is_admin = self._admin

    def _sans_droits(self):
        self.common.is_admin = lambda: False

    def _avec_droits(self):
        self.common.is_admin = lambda: True

    def test_refus_sans_droits_pointe_vers_admin(self):
        self._sans_droits()
        m = refus.motif_refus("désactiver « Truc »", code=5)
        self.assertIn("administrateur", m)
        self.assertIn("désactiver", m)
        self.assertNotIn("organisation", m, "sans les droits, on ne doit pas incriminer la GPO")

    def test_refus_alors_qu_on_est_admin_nomme_la_gpo(self):
        self._avec_droits()
        m = refus.motif_refus("désactiver « Truc »", code=5)
        self.assertIn("règle de groupe", m)
        self.assertIn("organisation", m)
        self.assertIn("gestionnaire du poste", m)
        self.assertNotIn("Relancer en administrateur", m,
                        "relancer en admin ne changerait rien : ne pas le proposer")

    def test_code_de_connu_traduit(self):
        self._sans_droits()
        m = refus.motif_refus("démarrer « Spouleur »", code=1060)
        self.assertIn("n'existe pas", m)
        self.assertIn("1060", m, "le code brut doit rester visible pour qui aide a distance")

    def test_out_of_the_box_pas_de_message_en_anglais(self):
        self._avec_droits()
        m = refus.motif_refus("modifier ce réglage", erreur=OSError("Access is denied"))
        self.assertFalse(m.startswith("OSError"), "un nom d'exception brut ne doit pas finir a l'ecran")
        self.assertIn("Impossible", m)

    def test_le_code_vient_de_la_sortie_de_sc_exe(self):
        self._avec_droits()
        sortie = "[SC] ChangeServiceConfig FAILED 5: Access is denied.\r\n"
        self.assertEqual(refus.numero(sortie=sortie), 5)
        m = refus.motif_refus("désactiver « Truc »", sortie=sortie)
        self.assertIn("règle de groupe", m)

    def test_raison_inconnue_restait_lisible(self):
        self._sans_droits()
        m = refus.motif_refus("tester « machin »")
        self.assertIn("Impossible", m)
        self.assertTrue(m.endswith("."), "une phrase complete, pas un fragment")

    def _admin(self):
        return refus


class RelanceAdminTest(unittest.TestCase):
    """Le remede « relance en admin » ne doit pas etre une impasse : le
    processus eleve recoit des chemins ABSOLUS et un dossier de travail
    explicite, sinon il meurt sans bruit pendant que la fenetre est fermee."""

    import os
    import unittest.mock as mock
    from Shared.Utils import common

    def _faux_windll(self, ret):
        appels = {}

        def shell(hwnd, op, exe, params, cwd, show):
            appels.update(op=op, exe=exe, params=params, cwd=cwd)
            return ret

        class S:
            ShellExecuteW = staticmethod(shell)

        class W:
            shell32 = S()
        return W, appels

    @unittest.skipUnless(common.IS_WINDOWS, "Windows uniquement")
    def test_la_relance_part_en_chemins_absolus(self):
        W, appels = self._faux_windll(42)
        with self.mock.patch.object(self.common.ctypes, "windll", W):
            self.assertTrue(self.common.relaunch_as_admin())
        self.assertEqual(appels["op"], "runas")
        self.assertTrue(self.os.path.isabs(appels["exe"]))
        self.assertTrue(self.os.path.isdir(appels["cwd"]),
                        "le dossier de travail doit exister (jamais None)")
        import re
        tokens = re.findall(r'"([^"]*)"', appels["params"])
        self.assertTrue(tokens, "au moins le script doit etre passe")
        for token in tokens:
            self.assertTrue(token.startswith("-") or self.os.path.isabs(token),
                            f"argument relatif refuse : {token}")

    @unittest.skipUnless(common.IS_WINDOWS, "Windows uniquement")
    def test_annulation_uac_renvoie_faux(self):
        W, _ = self._faux_windll(0)  # ShellExecuteW renvoie <=32 en erreur
        with self.mock.patch.object(self.common.ctypes, "windll", W):
            self.assertFalse(self.common.relaunch_as_admin())
