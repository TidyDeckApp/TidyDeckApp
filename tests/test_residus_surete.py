# -*- coding: utf-8 -*-
"""Renforcement « Fichiers et résidus » : un dossier pouvant contenir des
données de l'utilisateur n'est JAMAIS proposé (exclusion par contenu et par
emplacement, avant toute confiance). Tout sur dossiers factices en temporaire.
"""
import os
import shutil
import tempfile
import time
import unittest
from unittest import mock

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Core.Storage import residus

JOUR = 86400.0
MO = 1024 * 1024

INSTALLS = [
    {"nom": "Zother App", "cle": "zotherapp", "source": "Windows",
     "editeur": "Zother", "installation": "", "jeu": ""},
]


def _dossier(base, nom, taille=3 * MO, age_jours=400):
    p = os.path.join(base, nom)
    os.makedirs(p, exist_ok=True)
    f = os.path.join(p, "data.bin")
    with open(f, "wb") as fh:
        fh.truncate(taille)
    t = time.time() - age_jours * JOUR
    os.utime(f, (t, t))
    os.utime(p, (t, t))
    return p


def _empreinte(base):
    etat = {}
    for racine, _, fichiers in os.walk(base):
        for f in fichiers:
            p = os.path.join(racine, f)
            st = os.stat(p)
            etat[p] = (st.st_size, st.st_mtime)
    return etat


class ExclusionParContenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="tidydeck_surete_")
        cls.roam = os.path.join(cls.base, "Roaming")
        os.makedirs(cls.roam)
        cls.game = _dossier(cls.roam, "GameFakeX")
        os.makedirs(os.path.join(cls.game, "Saved", "SaveGames"))
        open(os.path.join(cls.game, "Saved", "SaveGames", "profil.sav"), "wb").close()
        cls.stock = _dossier(cls.roam, "StockX")
        open(os.path.join(cls.stock, "local.sqlite"), "wb").close()
        cls.vide = _dossier(cls.roam, "VideX", 0)
        os.remove(os.path.join(cls.vide, "data.bin"))
        cls.pur = _dossier(cls.roam, "CachePurX")

    def test_analyse_exclut_et_seulement_le_pur_passe(self):
        avant = _empreinte(self.base)
        res = residus.analyse(racines=[self.roam], installs=INSTALLS, jours=90)
        apres = _empreinte(self.base)
        noms = {r["nom"] for r in res["lignes"]}
        self.assertEqual(noms, {"CachePurX"},
                         f"seul le cache pur doit être proposé, reçu {noms}")
        self.assertEqual(avant, apres, "l'analyse doit rester en lecture seule")

    def test_illisible_jamais_propose(self):
        with mock.patch.object(residus.os, "scandir", side_effect=OSError("accès refusé")):
            self.assertTrue(residus.contient_donnees_utilisateur(self.pur))
            res = residus.analyse(racines=[self.roam], installs=INSTALLS, jours=90)
        self.assertEqual([r["nom"] for r in res["lignes"]], [])

    def test_marqueurs_contenus(self):
        tmp = tempfile.mkdtemp(prefix="td_marqueurs_")
        for nom in ("profiles", "userdata", "Characters", "config", "backup"):
            d = os.path.join(tmp, nom)
            os.makedirs(d)
            self.assertTrue(residus.contient_donnees_utilisateur(tmp), nom)
            os.rmdir(d)
        open(os.path.join(tmp, "blob.sl2"), "wb").close()
        self.assertTrue(residus.contient_donnees_utilisateur(tmp))


class IllisibleEtDoute(unittest.TestCase):
    def test_chemin_inexistant_consider_protege(self):
        self.assertTrue(residus.contient_donnees_utilisateur(r"C:\n\existant\n\du\tout"))


class ProfondeurEtLimites(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="td_prof_")
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)

    def _cree(self, *rels):
        for rel in rels:
            p = os.path.join(self.base, *rel.split("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb"):
                pass
        return self.base

    def test_marqueur_en_profondeur_detecte(self):
        d = self._cree("Jeu/Data/profiles/x.txt")
        self.assertTrue(residus.contient_donnees_utilisateur(d))

    def test_marqueur_au_dela_de_quatre_niveaux_ignore(self):
        d = self._cree("a/b/c/d/sauvegarde/x.bin")
        self.assertFalse(residus.contient_donnees_utilisateur(d))

    def test_cache_pur_sans_marqueur(self):
        d = self._cree("tmp1.tmp", "chunks/b0.x", "f.bin")
        self.assertFalse(residus.contient_donnees_utilisateur(d))

    def test_plafond_entrees_force_vrai(self):
        noms = tuple("f%02d.bin" % i for i in range(5))
        d = self._cree(*noms)
        with mock.patch.object(residus, "LIMIT_ENTREES_RESIDUS", 3):
            self.assertTrue(residus.contient_donnees_utilisateur(d))
        self.assertFalse(residus.contient_donnees_utilisateur(d))

    def test_sous_dossier_illisible_force_vrai(self):
        d = self._cree("f.bin")
        sous = os.path.join(d, "sous")
        os.makedirs(sous)
        vrai = os.scandir

        def faux(chemin, *a, **kw):
            if os.path.normcase(str(chemin)) == os.path.normcase(sous):
                raise OSError("accès refusé")
            return vrai(chemin, *a, **kw)

        with mock.patch.object(residus.os, "scandir", side_effect=faux):
            self.assertTrue(residus.contient_donnees_utilisateur(d))

    def test_lien_symbolique_force_vrai(self):
        d = self._cree("app/f.bin")
        cible = os.path.join(self.base, "cible")
        os.makedirs(cible, exist_ok=True)
        try:
            os.symlink(cible, os.path.join(d, "relais"))
        except (OSError, NotImplementedError):
            self.skipTest("création de lien symbolique non autorisée")
        self.assertTrue(residus.contient_donnees_utilisateur(d))


if __name__ == "__main__":
    unittest.main()
