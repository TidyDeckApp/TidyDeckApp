# -*- coding: utf-8 -*-
"""Fichiers « dans le nuage » : OneDrive et consorts.

Un fichier placeholder n'existe pas vraiment sur le disque : ses octets sont chez
le fournisseur. Le toucher = le telecharger. Deux degats a eviter absolument :

  1. la recherche de doublons qui hachie un fichier de 40 Go « pour rien » et le
     telecharge du coup en entier ;
  2. « Gros elements » qui affiche un fichier du nuage comme s'il pesait sur ton
     disque, alors qu'il n'occupe presque rien localement.

Detection par les attributs Windows :
    0x400000  FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS   (OneDrive, donnees pas la)
    0x40000   FILE_ATTRIBUTE_RECALL_ON_OPEN          (rappel a l'ouverture)
    0x1000    FILE_ATTRIBUTE_OFFLINE
Et on les ignore dans les doublons, les oublies, les gros elements, les clips.
"""
import ctypes
import os
import shutil
import tempfile
import unittest

from tests import ROOT  # noqa: F401  (place le projet sur sys.path)

OFFLINE = 0x1000
RECALL_OPEN = 0x40000
RECALL_DATA = 0x400000
k32 = ctypes.windll.kernel32 if os.name == "nt" else None


class NuageTest(unittest.TestCase):
    def setUp(self):
        if os.name != "nt":
            self.skipTest("attributs Windows only")
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="td_nuage_"))
        self._saved = dict(os.environ)
        from Shared.Utils import cloud
        self.cloud = cloud

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers ---------------------------------------------------------------
    def _fichier(self, nom, taille=4096, contenu=None):
        p = os.path.join(self.tmp, nom)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(contenu if contenu is not None else b"x" * taille)
        return os.path.realpath(p)

    def _attributs(self, p):
        a = k32.GetFileAttributesW(p)
        self.assertNotEqual(a, 0xFFFFFFFF, "GetFileAttributesW a echoue sur " + p)
        return a

    def _marquer(self, p, bits=OFFLINE):
        """SetFileAttributesW accepte silencieusement 0x40000/0x400000 sans les
        poser : ces deux bits sont reserves au filtre du driver de synchro.
        On verification faite, on skippe proprement ce qu'on ne peut pas simuler."""
        k32.SetFileAttributesW(p, self._attributs(p) | bits)
        if not (self._attributs(p) & bits):
            self.skipTest(f"attribut {hex(bits)} reserve au driver : non simulable "
                         "par un utilisateur normal (masque verifie par test_masque_complet)")
        return p

    # -- lecture de l'attribut -------------------------------------------------
    def test_un_fichier_normal_n_est_pas_hors_ligne(self):
        self.assertFalse(self.cloud.est_hors_ligne(self._fichier("normal.bin")))

    def test_attribut_offline_est_detecte(self):
        self.assertTrue(self.cloud.est_hors_ligne(self._marquer(self._fichier("off.bin"), OFFLINE)))

    def test_recall_on_open_est_detecte(self):
        self.assertTrue(self.cloud.est_hors_ligne(self._marquer(self._fichier("ro.bin"), RECALL_OPEN)))

    def test_recall_on_data_access_est_detecte(self):
        self.assertTrue(self.cloud.est_hors_ligne(self._marquer(self._fichier("rd.bin"), RECALL_DATA)))

    def test_masque_complet(self):
        for bit in (OFFLINE, RECALL_OPEN, RECALL_DATA):
            self.assertTrue(self.cloud.NUAGE & bit, "bit %s absent du masque NUAGE" % hex(bit))

    def test_chemin_absent_ne_explose_pas(self):
        self.assertFalse(self.cloud.est_hors_ligne(os.path.join(self.tmp, "inexistant.bin")))

    # -- fichiers oublies ------------------------------------------------------
    def test_oublies_ignorent_un_placeholder(self):
        from Core.Storage import storage
        p = self._fichier("vieux.bin", taille=4096)
        os.utime(p, (0, 0))
        self.assertEqual(len(storage.find_forgotten([self.tmp], days=30, min_size=1024)), 1)
        self._marquer(p)
        self.assertEqual(storage.find_forgotten([self.tmp], days=30, min_size=1024), [])

    # -- gros elements ---------------------------------------------------------
    def test_gros_elements_ne_comptent_pas_un_placeholder(self):
        from Core.Storage import storage
        gros = self._fichier("gros.bin", taille=100_000)
        petit = self._fichier(os.path.join("Sous", "petit.bin"), taille=10_000)
        self._marquer(gros)

        r = storage.find_largest(self.tmp, limit=5)
        chimins = [os.path.realpath(p) for _s, p, _m in r["files"]]
        self.assertNotIn(gros, chimins, "un fichier du nuage ne doit pas etre annonce comme gros")
        self.assertIn(os.path.realpath(petit), chimins)
        self.assertGreaterEqual(r.get("nuage", 0), 1,
                               "le resultif doit dire combien de fichiers sont dans le nuage")

    def test_taille_d_un_dossier_ne_gonfle_pas_avec_le_nuage(self):
        from Core.Storage import storage
        lourd = self._fichier(os.path.join("Sous", "lourd.bin"), taille=500_000)
        self._marquer(lourd)
        r = storage.find_largest(self.tmp, limit=5)
        tailles = {n: t for n, t in [(nom, taille) for nom, _c, taille in r["folders"]]}
        self.assertEqual(tailles.get("Sous", -1), 0,
                         "« Sous » ne contient que du nuage : 0 octet reel sur le disque")

    # -- quarantaine -----------------------------------------------------------
    def test_mettre_en_quarantaine_un_placeholder_est_refuse(self):
        from Shared.Utils import quarantine
        p = self._marquer(self._fichier("qn.bin"))
        with self.assertRaises(OSError):
            quarantine.move_in(p, "run_nuage", 1)
        self.assertTrue(os.path.exists(p), "le fichier doit rester en place, jamais telecharge ni deplace")

    def test_mettre_en_quarantaine_un_fichier_local_passe(self):
        from Shared.Utils import quarantine
        p = self._fichier("ok.bin")
        self.assertTrue(os.path.exists(quarantine.move_in(p, "run_ok", 1)))

    # -- dossiers synchronises -------------------------------------------------
    def test_repertoire_onedrive_reconnu_comme_synchronise(self):
        os.environ["OneDrive"] = self.tmp
        dedans = self._fichier("un.bin")
        self.assertEqual(self.cloud.racine_synchronisee(dedans), self.tmp)
        self.assertTrue(self.cloud.est_synchronise(dedans))

    def test_hors_d_un_dossier_synchronise(self):
        os.environ["OneDrive"] = os.path.join(self.tmp, "cloud")
        os.makedirs(os.environ["OneDrive"], exist_ok=True)
        ailleurs = self._fichier("ailleurs.bin")
        self.assertIsNone(self.cloud.racine_synchronisee(ailleurs))
        self.assertFalse(self.cloud.est_synchronise(ailleurs))

    def test_message_d_avertissement_pour_une_mise_en_quarantaine(self):
        os.environ["OneDrive"] = os.path.join(self.tmp, "cloud")
        os.makedirs(os.environ["OneDrive"], exist_ok=True)
        dans_cloud = self._fichier(os.path.join("cloud", "a.bin"))
        local = self._fichier("b.bin")
        msg = self.cloud.avertissement([dans_cloud, local])
        self.assertIn("nuage", msg.lower())
        self.assertIn(os.path.basename(dans_cloud), msg)
        self.assertNotIn(os.path.basename(local), msg, "un fichier local ne doit pas etre cite")
        self.assertEqual(self.cloud.avertissement([local]), "", "rien a signaler sans fichier synchronise")


if __name__ == "__main__":
    unittest.main()
