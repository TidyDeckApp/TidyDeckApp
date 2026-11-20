# -*- coding: utf-8 -*-
"""Lot « Sécurité résidus » (0.6.2) : zéro risque de toucher une donnée précieuse.

Couvre les cinq règles du lot C (profondeur corrigée en C2) :
  R1 profondeur : seul le niveau directement sous la zone est proposé
     (comme en 0.6.1) ; tout sous-dossier est refusé, jamais proposé ;
  R2 sauvegardes et données personnelles : jamais proposées ni cochées,
     quelle que soit la casse (noms unicode inclus), et tout leur contenu ;
  R3 liens et jonctions : jamais suivis, comptés ni proposés ;
  R4 doute : rien n'est coché par défaut, et Sérénité ne propose rien ;
  R5 quarantaine des résidus toujours désactivée (M1-M6 non faits).

Python pur, aucun tkinter, aucun registre : fausses arborescences dans un
temporaire, liens simulés par monkeypatch — les tests tournent aussi sous Linux.
"""
import os
import shutil
import tempfile
import time
import unittest
from unittest import mock

from Core.Storage import residus

JOUR = 86400.0
MO = 1024 * 1024

INSTALLS = [{"nom": "Zother App", "cle": "zotherapp", "source": "Windows",
             "editeur": "Zother", "installation": "", "jeu": ""}]


def _dossier(base, rel, taille=3 * MO, age=400):
    """Crée (si besoin) un sous-dossier filled, puis le vieillit. Si des
    enfants sont créés dedans après, rappeler _ajeune() à la fin."""
    p = os.path.join(base, *rel.split("/"))
    os.makedirs(p, exist_ok=True)
    f = os.path.join(p, "data.bin")
    with open(f, "wb") as fh:
        fh.truncate(taille)
    _ajeune(p, age)
    return p


def _ajeune(p, age=400):
    """Vieillit un dossier et son data.bin (un mtime de dossier change quand
    on crée un enfant dedans : on re-age en dernière passe)."""
    f = os.path.join(p, "data.bin")
    if os.path.isdir(p) and not os.path.exists(f):
        with open(f, "wb") as fh:
            fh.truncate(3 * MO)
    t = time.time() - age * JOUR
    if os.path.exists(f):
        os.utime(f, (t, t))
    os.utime(p, (t, t))


def _noms(res):
    return {r["nom"] for r in res["lignes"]}


def _chemins(res):
    return " || ".join(r["chemin"] for r in res["lignes"])


class _AvecNettoyage(unittest.TestCase):
    """Nettoie le dossier temporaire créé par setUpClass."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)


class Profondeur(_AvecNettoyage):
    """R1 : 4 niveaux proposés, le 5e jamais."""

    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="td_lotc_prof_")
        cls.zone = os.path.join(cls.base, "Zone")
        os.makedirs(cls.zone)
        cls.empile()

    @classmethod
    def empile(cls):
        for rel in ("Prof1", "Prof1/Prof2", "Prof1/Prof2/Prof3",
                    "Prof1/Prof2/Prof3/Prof4", "Prof1/Prof2/Prof3/Prof4/Prof5"):
            _dossier(cls.zone, rel)
        for rel in ("Prof1", "Prof1/Prof2", "Prof1/Prof2/Prof3",
                    "Prof1/Prof2/Prof3/Prof4", "Prof1/Prof2/Prof3/Prof4/Prof5"):
            _ajeune(os.path.join(cls.zone, *rel.split("/")))

    def _analyse(self):
        return residus.analyse(racines=[self.zone], installs=INSTALLS, jours=90)

    def test_seul_le_niveau_un_est_propose(self):
        n = _noms(self._analyse())
        self.assertIn("Prof1", n, "directement sous la zone : il a vocation à être vu")
        for refuse in ("Prof2", "Prof3", "Prof4", "Prof5"):
            self.assertNotIn(refuse, n,
                             "la proposition s'arrête au niveau 1 : aucun sous-dossier ne sort")

    def test_aucune_ligne_plus_profond_que_le_niveau_un(self):
        for r in self._analyse()["lignes"]:
            self.assertEqual(r["profondeur"], 1)

    def test_plafond_de_la_constante(self):
        self.assertEqual(residus.PROFONDEUR_PROPOSITION_MAX, 1)


class ProtectionsNom(unittest.TestCase):
    """R2 : chaque motif protégé, en majuscules, minuscules, cas mixtes, accents."""

    PROTEGES = ("saves", "SAVES", "SaVeS", "savegames", "SAVEGAMES", "save",
                "Save", "sauvegardes", "Sauvegardes", "SAUVEGARDES", "backup",
                "backups", "BACKUPS", "my games", "MY GAMES", "My Games",
                "profiles", "PROFILES", "userdata", "UserData",
                "Mes_Sauvegardes", "Game Backup X", "My Games Old",
                "Éco Sauvegardes", "Épluchures de saves", "User Data",
                "partie.sav", "Plan.SAVE", "notes.bak", "jeu.sl2", "data.dat",
                "sauvegarde", "Sauvegarde", "savegame", "profile")

    NON_PROTEGES = ("CachePurX", "VieuxLogiciel", "TrucReste", "WindowsOld",
                    "Zother", "chunkb0", "tmpcache", "Relief")

    def test_chaque_motif_protege(self):
        for nom in self.PROTEGES:
            self.assertTrue(residus.est_protege(nom), f"{nom} doit être protégé")

    def test_les_sains_ne_sont_pas_bloques(self):
        for nom in self.NON_PROTEGES:
            self.assertFalse(residus.est_protege(nom), f"{nom} n'a rien d'une sauvegarde")


class ProtectionsAnalyse(_AvecNettoyage):
    """R2 côté analyse : le dossier protégé et tout son contenu ne sortent jamais."""

    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="td_lotc_prot_")
        cls.zone = os.path.join(cls.base, "Zone")
        os.makedirs(cls.zone)
        for nom in ("Saves", "SAUVEGARDES", "My Games", "sauvegardes",
                    "UserData", "Backups", "profiles"):
            _dossier(cls.zone, nom)
            _dossier(cls.zone, nom + "/CacheQuiPasseBien")
            _ajeune(os.path.join(cls.zone, nom))
        _dossier(cls.zone, "OrphelinTemoins")

    def _analyse(self):
        return residus.analyse(racines=[self.zone], installs=INSTALLS, jours=90)

    def test_dossiers_proteges_jamais_proposes(self):
        n = _noms(self._analyse())
        for nom in ("Saves", "SAUVEGARDES", "My Games", "sauvegardes",
                    "UserData", "Backups", "profiles"):
            self.assertNotIn(nom, n, f"{nom} est une sauvegarde : jamais proposé")
        self.assertIn("OrphelinTemoins", n,
                      "le témoin orphelin doit rester proposé, sinon le test est vide")

    def test_contenu_dun_dossier_protege_jamais_propose(self):
        res = self._analyse()
        self.assertNotIn("CacheQuiPasseBien", _noms(res),
                         "un dossier d'apparence cache dans un dossier protégé "
                         "est protégé aussi, à n'importe quelle profondeur")
        self.assertNotIn("CacheQuiPasseBien", _chemins(res))


class FichiersProteges(_AvecNettoyage):
    """R2 : fichier de sauvegarde dans un sous-dossier ordinaire = dossier jamais proposé."""

    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="td_lotc_fic_")
        cls.zone = os.path.join(cls.base, "Zone")
        os.makedirs(cls.zone)
        _dossier(cls.zone, "DosSav")
        os.makedirs(os.path.join(cls.zone, "DosSav", "sous"))
        for nom in ("partie.sav", "slot.save", "jeu.sl2", "vieil_enregistreur.dat"):
            open(os.path.join(cls.zone, "DosSav", "sous", nom), "wb").close()
        _ajeune(os.path.join(cls.zone, "DosSav"))
        _dossier(cls.zone, "DosBak")
        os.makedirs(os.path.join(cls.zone, "DosBak", "sous"))
        open(os.path.join(cls.zone, "DosBak", "sous", "notes.bak"), "wb").close()
        _ajeune(os.path.join(cls.zone, "DosBak"))
        _dossier(cls.zone, "DosTemoins")

    def test_sav_save_sl2_dat_protegent_le_dossier(self):
        n = _noms(residus.analyse(racines=[self.zone], installs=INSTALLS, jours=90))
        self.assertNotIn("DosSav", n)
        self.assertNotIn("DosBak", n, "*.bak est une sauvegarde : le dossier qui "
                                      "contient notes.bak ne doit jamais sortir")
        self.assertIn("DosTemoins", n)

    def test_extensions_de_sauvegarde_declarees(self):
        for ext in (".sav", ".save", ".bak", ".sl2", ".dat"):
            self.assertIn(ext, residus.EXTENSIONS_SAUVEGARDE, ext)


class LienJamaisSuivi(_AvecNettoyage):
    """R3 : ni suivi, ni compté, ni proposé (monkeypatch : pas d'admin requis)."""

    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="td_lotc_lien_")
        cls.zone = os.path.join(cls.base, "Zone")
        os.makedirs(cls.zone)
        _dossier(cls.zone, "LienTest")
        _dossier(cls.zone, "LienTest/PropreEnfant")
        _ajeune(os.path.join(cls.zone, "LienTest"))
        _dossier(cls.zone, "Ordinaire")

    def _analyse(self):
        return residus.analyse(racines=[self.zone], installs=INSTALLS, jours=90)

    def test_sans_lien_le_niveau_un_sort(self):
        n = _noms(self._analyse())
        self.assertIn("LienTest", n)
        self.assertIn("Ordinaire", n)
        self.assertNotIn("PropreEnfant", n, "le niveau 2 ne sort jamais, lien ou pas")
        self.assertEqual(self._analyse()["dossiers_vus"], 2)

    def test_avec_lien_rien_ne_le_traverse(self):
        vrai = residus.est_lien

        def faux(chemin):
            return True if "LienTest" in str(chemin) else vrai(chemin)

        with mock.patch.object(residus, "est_lien", faux):
            res = self._analyse()
        n = _noms(res)
        self.assertNotIn("LienTest", n, "un lien n'est jamais proposé")
        self.assertNotIn("PropreEnfant", n, "on ne descend jamais dans un lien")
        self.assertEqual(res["dossiers_vus"], 1,
                         "le lien ne doit même pas être compté (seul Ordinaire est compté)")


class UneRegressionParRegle(_AvecNettoyage):
    """Un test de non-régression par règle du lot C."""

    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="td_lotc_regl_")
        cls.zone = os.path.join(cls.base, "Zone")
        os.makedirs(cls.zone)
        for rel in ("R1", "R1/R1a", "R1/R1a/R1b", "R1/R1a/R1b/R1c", "R1/R1a/R1b/R1c/R1d"):
            _dossier(cls.zone, rel)
        for rel in ("R1", "R1/R1a", "R1/R1a/R1b", "R1/R1a/R1b/R1c"):
            _ajeune(os.path.join(cls.zone, *rel.split("/")))
        _dossier(cls.zone, "My Games")
        _dossier(cls.zone, "Saves/CacheDedans")
        _ajeune(os.path.join(cls.zone, "Saves"))

    def _analyse(self):
        return residus.analyse(racines=[self.zone], installs=INSTALLS, jours=90)

    def test_regle1_profondeur(self):
        res = self._analyse()
        self.assertIn("R1", _noms(res))
        for refuse in ("R1a", "R1b", "R1c", "R1d"):
            self.assertNotIn(refuse, _noms(res),
                             "le niveau 2 et au-delà ne sont jamais proposés")
        for r in res["lignes"]:
            self.assertEqual(r["profondeur"], 1)

    def test_regle2_protection(self):
        res = self._analyse()
        n = _noms(res)
        self.assertNotIn("My Games", n)
        self.assertNotIn("CacheDedans", n)
        for r in res["lignes"]:
            self.assertFalse(residus.est_protege(r["nom"]),
                             f"{r['nom']} est protégé, il n'aurait jamais dû sortir")

    def test_regle3_jamais_de_lien(self):
        with mock.patch.object(residus, "est_lien", lambda p: True):
            res = self._analyse()
        self.assertEqual(res["lignes"], [])
        self.assertEqual(res["dossiers_vus"], 0)

    def test_regle4_rien_de_coche_par_defaut(self):
        res = self._analyse()
        self.assertTrue(res["lignes"])
        for r in res["lignes"]:
            self.assertIs(r["selecte"], False)
        src = open(os.path.join(os.path.dirname(residus.__file__),
                                os.pardir, os.pardir, "UI", "Pages",
                                "storage_page.py"), encoding="utf-8").read()
        self.assertIn('if ctx.advanced and not ctx.cfg.get("serenity")', src,
                      "en Sérénité, la vue Résidus ne doit même pas exister")

    def test_regle5_quarantaine_des_residus_toujours_interdite(self):
        racine = os.path.join(os.path.dirname(residus.__file__), os.pardir, os.pardir)
        for f in (residus.__file__,
                  os.path.join(racine, "UI", "Pages", "residus_view.py")):
            src = open(f, encoding="utf-8").read().lower()
            for mot in ("quarantine", "shutil", "rmtree", "os.remove", "winreg.delete"):
                self.assertNotIn(mot, src, f"{mot} est interdit ici")
        self.assertEqual(residus.JOURS_QUARANTAINE_RESIDUS, 30)
        src = open(residus.__file__, encoding="utf-8").read()
        self.assertIn("M1-M6", src, "la condition M1-M6 sur 5 machines doit rester écrite")


if __name__ == "__main__":
    unittest.main()
