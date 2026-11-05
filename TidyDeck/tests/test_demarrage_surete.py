"""Sûreté de la liste « démarrage » : ce que le bouton « Désactiver les
programmes inutiles » propose doit être vraiment inutile — jamais un
antivirus, jamais un logiciel dont le lancement automatique protège l'utilisateur.
"""
import os
import unittest

from Core.Startup import startup

# Fragments qui n'ont rien à faire dans un niveau « safe » (désactivable sans risque).
NUISIBLES = ("defender", "securityhealth", "bitdefender", "kaspersky", "avast",
             "avg", "mcafee", "eset", "nod32", "firewall", "ctfmon")
# Les navigateurs homonymes d'antivirus (avastbrowser…) sont de vrais
# programmes « safe » : ils ne doivent pas faire échouer le test.
SUFFIXES_INOFFENSIFS = ("browser", "chrome", "update", "updater")


class HintSureteTest(unittest.TestCase):
    def test_safe_ne_jamais_antivirus_ou_coeur_windows(self):
        for frag, _txt, lvl in startup.HINTS:
            if lvl != "safe":
                continue
            f = frag.lower()
            if f.endswith(SUFFIXES_INOFFENSIFS):
                continue
            for n in NUISIBLES:
                self.assertNotIn(n, f, f"« {frag} » classé safe alors qu'il touche à {n}")

    def test_vpn_jamais_safe(self):
        """Un VPN qui ne se lance plus au démarrage laisse l'utilisateur sans
        protection réseau jusqu'à l'ouverture manuelle : c'est un choix, pas
        un « sans risque » -> niveau « maybe » au mieux."""
        niveaux = {}
        for frag, _txt, lvl in startup.HINTS:
            niveaux.setdefault(frag, lvl)
        for v in ("vpn", "nordvpn", "expressvpn", "mullvad", "cisco", "anyconnect"):
            if v in niveaux:
                self.assertNotEqual(niveaux[v], "safe", f"« {v} » ne doit pas être « safe »")


if __name__ == "__main__":
    unittest.main()
