# -*- coding: utf-8 -*-
"""Les noms que Windows rend ne sont pas garantis : ne jamais les deviner.

Trois cas verifiables sur CE poste, sans installer quoi que ce soit :

  * un dossier utilisateur porte un nom different de l'affichage (« Downloads »
    existe vraiment alors que l'Explorateur ecrit « Telechargements »), et il peut
    etre renomme, bascule sur OneDrive ou deplace sur un autre disque ;
  * sc.exe ecrit « Échec(s) 1060 » sur un Windows francais : chercher « FAILED »
    ne rapporte jamais rien ici ;
  * le nom d'un plan d'alimentation est traduit lui aussi.

Dans les trois cas la parade est la meme : demander a Windows (dossier connu par
GUID, code de retour du processus, GUID du plan) au lieu de comparer du texte.
Le texte ne reste qu'un repli quand l'appel repond mal.
"""
import os
import re
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Core.Games import power  # noqa: E402
from Core.Health import services  # noqa: E402
from Core.Startup import startup  # noqa: E402
from Core.Storage import storage  # noqa: E402
from Shared.Utils import cloud  # noqa: E402
from Shared.Utils import dossiers  # noqa: E402
from Shared.Utils import refus  # noqa: E402
from Shared.Utils.common import IS_WINDOWS  # noqa: E402

# Noms francais qui ne doivent plus servir a TROUVER un dossier dans le moteur :
# leur place est dans un libelle affiche, pas dans une resolution de chemin.
NOMS_LOCAUX_INTERDITS = ("Téléchargements", "Bureau", "Vidéos", "Mes Documents")

_ENV_VIDES = {n: "" for n in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial",
                              "Dropbox", "GOOGLE_DRIVE_PATH", "GDRIVE_ROOT")}


def _nc(chemin):
    return os.path.normcase(str(chemin))


class _Machine(unittest.TestCase):
    """Profil fictif + API detournee : une machine ou les noms ne sont pas ceux attendu.

    `noms_par_cle` associe chaque dossier connu au nom que cette machine lui donne
    (chemin absolu accepte pour simuler une redirection hors du profil). Le profil
    ne contient AUCUN nom connu : si le moteur en trouvait un, c'est qu'il devine.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.profil = self.tmp / "profil"
        self.profil.mkdir(parents=True)
        self.rendu = {}
        self.env = None
        self.api = None
        dossiers.vider_cache()

    def monte(self, noms_par_cle, fichiers=None):
        """Repart d'un profil VIDE : monter deux fois ne doit pas laisser trainer
        les dossiers du montage precedent."""
        self.arrete()
        shutil.rmtree(self.profil, ignore_errors=True)
        self.profil.mkdir(parents=True)
        self.rendu = {}
        for cle, nom in noms_par_cle.items():
            if not nom:
                self.rendu[cle] = None
                continue
            self.rendu[cle] = nom if os.path.isabs(nom) else str(self.profil / nom)
        for chemin in self.rendu.values():
            if chemin:
                Path(chemin).mkdir(parents=True, exist_ok=True)
        for rel, taille in (fichiers or {}).items():
            f = self.profil / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"x" * taille)
        env = dict(_ENV_VIDES)
        env.update({"USERPROFILE": str(self.profil), "HOME": str(self.profil)})
        self.env = mock.patch.dict(os.environ, env, clear=False)
        self.env.start()
        self.api = mock.patch.object(dossiers, "_api", lambda cle: self.rendu.get(cle))
        self.api.start()
        dossiers.vider_cache()
        return self.rendu

    def arrete(self):
        for nom in ("api", "env"):
            patch = getattr(self, nom, None)
            if patch is not None:
                try:
                    patch.stop()
                except Exception:
                    pass
        setattr(self, "api", None)
        setattr(self, "env", None)

    def tearDown(self):
        self.arrete()
        dossiers.vider_cache()
        shutil.rmtree(self.tmp, ignore_errors=True)


class IdentifiantsTest(unittest.TestCase):
    def setUp(self):
        dossiers.vider_cache()

    def tearDown(self):
        dossiers.vider_cache()

    def test_chaque_identifiant_est_un_guid_valide(self):
        for cle, valeur in dossiers.IDS.items():
            self.assertEqual(str(uuid.UUID(valeur)).lower(),
                             valeur.strip("{}").lower(), cle)

    def test_toute_cle_utilisee_est_declaree_partout(self):
        for cle in dossiers.CLES_UTILISEES:
            self.assertIn(cle, dossiers.IDS, f"{cle} utilise sans GUID")
            self.assertTrue(dossiers.NOMS.get(cle), f"{cle} sans nom de repli")

    @unittest.skipUnless(IS_WINDOWS, "SHGetKnownFolderPath est propre a Windows")
    def test_windows_rend_les_dossiers_reels(self):
        for cle in dossiers.CLES_UTILISEES:
            rendu = dossiers.connu(cle)
            self.assertTrue(rendu, f"Windows ne rend pas {cle}")
            self.assertTrue(os.path.isdir(rendu), f"{cle} -> {rendu} n'est pas un dossier")
            self.assertTrue(dossiers.nom(cle), f"{cle} sans nom sur cette machine")

    @unittest.skipUnless(IS_WINDOWS, "SHGetKnownFolderPath est propre a Windows")
    def test_windows_rend_aussi_appdata_onedrive_et_demarrage(self):
        for cle in ("appdata", "localappdata", "onedrive", "startup", "common_startup"):
            self.assertTrue(dossiers.connu(cle), f"{cle} introuvable")


class ApiMuetteTest(_Machine):
    """Sans l'API (plateforme sans shell, appel qui echoue) : repli sur les noms."""

    def test_rien_de_cree_rien_trouve(self):
        self.monte({})
        self.assertIsNone(dossiers.trouver("downloads"))
        self.assertEqual(dossiers.tous(["downloads", "videos"]), [])
        self.assertIsNone(dossiers.nom("downloads"))

    def test_repli_sur_le_nom_francais(self):
        self.monte({})
        local = self.profil / "Téléchargements"
        local.mkdir()
        self.assertEqual(_nc(dossiers.trouver("downloads")), _nc(local))

    def test_repli_sur_le_nom_anglais(self):
        self.monte({})
        (self.profil / "Downloads").mkdir()
        self.assertEqual(_nc(dossiers.trouver("downloads")), _nc(self.profil / "Downloads"))

    def test_reponse_vide_n_est_pas_une_fausse_route(self):
        self.monte({})
        with mock.patch.object(dossiers, "_api", lambda cle: "   "):
            self.assertIsNone(dossiers.trouver("documents"))


class NomsNonGarantisTest(_Machine):
    """Dossier renomme, deplace ou redirige : seul le chemin rendu par Windows compte."""

    def test_dossier_renomme_par_l_utilisateur(self):
        rendu = self.monte({"downloads": "A telecharger"})
        self.assertEqual(_nc(dossiers.trouver("downloads")), _nc(rendu["downloads"]))
        self.assertFalse((self.profil / "Downloads").exists())
        self.assertFalse((self.profil / "Téléchargements").exists())

    def test_un_dossier_absent_n_est_pas_invente(self):
        self.monte({"pictures": None})
        self.assertIsNone(dossiers.trouver("pictures"))

    def test_dossier_deplace_hors_du_profil(self):
        rendu = self.monte({"documents": str(self.tmp / "D" / "Donnees")})
        self.assertEqual(_nc(dossiers.trouver("documents")), _nc(rendu["documents"]))

    def test_redirection_onedrive_reconnue_comme_racine_synchronisee(self):
        nuage = self.tmp / "OneDrive"
        self.monte({"onedrive": str(nuage), "documents": str(nuage / "Documents")})
        racines = [_nc(r) for r in cloud.racines_synchronisees()]
        self.assertIn(_nc(nuage), racines,
                     "le OneDrive rendu par l'API doit compter comme racine synchronisee")
        self.assertEqual(_nc(cloud.racine_synchronisee(str(nuage / "Documents"))), _nc(nuage))

    def test_deux_cles_meme_dossier_une_seule_entree(self):
        nuage = self.tmp / "OneDrive"
        self.monte({"onedrive": str(nuage), "documents": str(nuage)})
        self.assertEqual(len(dossiers.tous(["documents", "onedrive", "documents"])), 1)


class MoteurSuitLaResolutionTest(_Machine):
    """Core/Storage doit suivre le chemin rendu, en aucun cas un nom impose."""

    def setUp(self):
        super().setUp()
        self.rendu = self.monte(
            {"downloads": "Tombés", "pictures": "Photos", "videos": "Films",
             "documents": "Papiers", "desktop": "Brouillon"},
            fichiers={"Films/Captures/clip.mp4": 4096})

    def test_dossiers_par_defaut_sont_ceux_de_ce_pc(self):
        noms = [p.name for p in storage.default_folders()]
        self.assertIn("Tombés", noms)
        self.assertIn("Photos", noms)
        for interdit in NOMS_LOCAUX_INTERDITS:
            self.assertNotIn(interdit, noms, "le moteur retombe sur un nom francais en dur")

    def test_downloads_folder_n_est_pas_limite_a_deux_noms(self):
        self.assertEqual(_nc(storage.downloads_folder()), _nc(self.rendu["downloads"]))

    def test_zone_des_gros_suiv_la_resolution_aussi(self):
        zones = [_nc(z.rstrip("\\/")) for z in storage.largest_zone()]
        self.assertIn(_nc(self.rendu["videos"]), zones)
        self.assertIn(_nc(self.rendu["downloads"]), zones)
        for z in zones:
            self.assertNotIn(z.lower(), ("c:", "d:", "/", "\\"),
                            "jamais un disque entier comme zone par defaut")

    def test_clips_trouves_meme_si_videos_a_un_autre_nom(self):
        clip = self.profil / "Films" / "Captures" / "clip.mp4"
        res = storage.find_clips(min_size=1000, limit=10)
        self.assertEqual([_nc(p) for _s, p, _m, _src in res], [_nc(clip)])
        self.assertEqual(res[0][3], "Xbox Game Bar",
                         "le dossier Captures doit etre attribue a la Game Bar")

    def test_sans_dossier_connu_on_reste_prudent(self):
        self.monte({})
        self.assertEqual(storage.default_folders(), [])
        self.assertIsNone(storage.downloads_folder())
        self.assertEqual(storage.find_clips(min_size=1), [])
        zones = storage.largest_zone()
        self.assertEqual(len(zones), 1, "sans dossier connu : le profil, jamais un disque")
        self.assertNotIn(_nc(zones[0]).rstrip("\\/"), ("c:", "d:", "/"))


def _corps(src, fonction):
    """Corps d'une fonction de premier niveau, jusqu'a la fonction suivante."""
    debut = src.index(f"def {fonction}(")
    suite = re.search(r"\ndef |\Z", src[debut + 1:])
    return src[debut:debut + 1 + suite.start()]


class PasDeNomsEnDurTest(unittest.TestCase):
    """Garde-fou : la resolution ne doit plus reposer sur un nom de dossier."""

    def _src(self, *parties):
        return Path(__file__).resolve().parent.parent.joinpath(*parties).read_text(
            encoding="utf-8")

    def test_storage_ne_devine_plus_un_nom_de_dossier(self):
        src = self._src("Core", "Storage", "storage.py")
        for fonc in ("default_folders", "largest_zone", "downloads_folder", "find_clips"):
            corps = _corps(src, fonc)
            for nom in NOMS_LOCAUX_INTERDITS:
                self.assertNotIn(f'"{nom}"', corps, f"{fonc} compare encore « {nom} » en dur")
                self.assertNotIn(f"'{nom}'", corps, f"{fonc} compare encore « {nom} » en dur")

    def test_les_quatre_entrees_passent_par_le_resolver(self):
        src = self._src("Core", "Storage", "storage.py")
        self.assertIn("from Shared.Utils import dossiers", src)
        for fonc in ("default_folders", "largest_zone", "downloads_folder", "find_clips"):
            self.assertIn("dossiers.", _corps(src, fonc), f"{fonc} ne resout plus rien")


class ResolutionHorsReseauTest(unittest.TestCase):
    def setUp(self):
        self.src = Path(__file__).resolve().parent.parent.joinpath(
            "Shared", "Utils", "dossiers.py").read_text(encoding="utf-8")

    def test_la_resolution_ne_touche_jamais_le_reseau(self):
        self.assertIn("SHGetKnownFolderPath", self.src)
        self.assertIn("CoTaskMemFree", self.src, "la chaine rendue par Windows doit etre liberee")
        for mot in ("urllib", "requests", "http", "socket", "startfile", "urlretrieve"):
            self.assertNotIn(mot, self.src, "trouver un dossier ne doit pas ouvrir le reseau")

    def test_com_est_initialise_dans_le_meme_bloc_que_l_appel(self):
        corps = _corps(self.src, "_api")
        self.assertIn("_com_initialise()", corps,
                      "SHGetKnownFolderPath exige COM initialise dans le thread appelant")
        self.assertLess(corps.index("_com_initialise()"), corps.index("SHGetKnownFolderPath"),
                        "l'initialisation doit preceder l'appel")

    def test_seul_un_repertoire_est_accepte(self):
        self.assertIn("isdir", self.src)


class CodeRetourScExeTest(unittest.TestCase):
    """Le motif d'un refus ne doit plus dependre de la phrase ecrite par sc.exe.

    Sur CE poste, l'echec s'ecrit « [SC] OpenService Échec(s) 1060 » : chercher
    « FAILED » ne rapporte donc jamais rien. sc.exe recopie le numero d'erreur
    Windows dans son code de retour (verifie ici : 1060) — c'est lui qui fait foi,
    le texte ne reste qu'un repli."""

    def test_le_code_du_processus_passe_avant_le_texte(self):
        self.assertEqual(refus.numero(code=1058, sortie="[SC] Échec(s) 1060 :"), 1058)

    def test_sortie_de_sc_exe_saisie_sur_sa_machine(self):
        sortie = ("[SC] OpenService Échec(s) 1060 :\r\n"
                  "Le service spécifié n'existe pas en tant que service installé.\r\n")
        self.assertEqual(refus.numero(sortie=sortie), 1060)

    def test_echec_non_signale_sur_un_succes(self):
        self.assertIsNone(refus.numero(code=0, sortie="[SC] ChangeServiceConfig SUCCESS"),
                          "code 0 = reussite : rien a traduire")

    def test_services_transmet_le_code_du_processus(self):
        sortie = "[SC] OpenService Échec(s) 1060 :\r\nLe service spécifié n'existe pas.\r\n"
        with mock.patch.object(services, "run_cmd", lambda *a, **k: (1060, sortie)):
            ok, code, recu = services._sc("Spooler", "disabled")
        self.assertFalse(ok)
        self.assertEqual(code, 1060, "sans le code, le motif retomberait sur « raison inconnue »")
        self.assertIn("n'existe pas", services._motif("Spooler", "désactiver", code, recu))

    def test_date_de_pilote_en_culture_invariante(self):
        src = Path(__file__).resolve().parent.parent.joinpath(
            "Core", "SystemInfo", "hardware.py").read_text(encoding="utf-8")
        self.assertIn("InvariantCulture", src,
                      "ToString('yyyy-MM-dd') suit la culture du PC : calendrier non grégorien possible")


class PlanAlimentationMemoriseTest(unittest.TestCase):
    """Le GUID du plan retenu est memorise : on ne cherche plus son nom ensuite."""

    def test_le_guid_memorise_suffit(self):
        with tempfile.TemporaryDirectory() as td:
            etat = Path(td) / "power_state.json"
            etat.write_text('{"ultimate": "d2867d74-4c56-4129-8c1e-5d5ec1bfbe4a"}', encoding="utf-8")
            with mock.patch.object(power, "STATE", etat), \
                    mock.patch.object(power, "list_schemes",
                                      lambda: [("d2867d74-4c56-4129-8c1e-5d5ec1bfbe4a",
                                                "Plan renommé par l'utilisateur", True)]):
                self.assertEqual(power.find_ultimate(), "d2867d74-4c56-4129-8c1e-5d5ec1bfbe4a")


class DossierDemarrageTest(_Machine):
    """Le dossier « Demarrage » peut etre detourne : le chemin recolle ne suffit plus."""

    def test_le_chemin_rendu_par_windows_est_suivi(self):
        detourne = self.tmp / "GPO" / "Demarrage"
        self.monte({"startup": str(detourne), "common_startup": str(detourne)})
        cases = {h: chemin for h, chemin, _a, _s in startup.dossiers_demarrage()}
        self.assertEqual(_nc(cases["HKCU"]), _nc(detourne))

    def test_a_defaut_le_chemin_standard_reste(self):
        self.monte({})
        cases = {h: chemin for h, chemin, _a, _s in startup.dossiers_demarrage()}
        self.assertTrue(cases["HKCU"].lower().endswith("startup"))
        self.assertIn("Microsoft\\Windows", cases["HKCU"])

    def test_cle_de_registre_de_letat_inchangee(self):
        # L'etat « desactive » se lit dans StartupApproved : ces cles-la ne dependent
        # pas du chemin du dossier et ne doivent pas bouger avec lui.
        self.monte({})
        approuves = [a.lower() for _h, _c, a, _s in startup.dossiers_demarrage()]
        self.assertTrue(all("startupapproved\\startupfolder" in a for a in approuves), approuves)


if __name__ == "__main__":
    unittest.main()
