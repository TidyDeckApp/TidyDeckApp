"""Tests de la détection des résidus (Phase 0, lecture seule).

Règle corrigée (cahier résidus v1, section 2) : un dossier n'est proposé que
si AUCUN logiciel installé ne lui correspond ET qu'il est inactif depuis
longtemps. Toute correspondance avec un logiciel installé = jamais proposé.

Tout se fait sur une fausse arborescence fabriquée une seule fois dans un
dossier temporaire : aucune lecture du vrai registre, aucune écriture ailleurs.
"""
import os
import shutil
import tempfile
import time
import unittest

from Core.Storage import residus

JOUR = 86400.0
MO = 1024 * 1024

INSTALLS = [
    {"nom": "Slack", "cle": "slack", "source": "Windows",
     "editeur": "Slack Technologies", "installation": "", "jeu": ""},
    {"nom": "Google Chrome", "cle": "googlechrome", "source": "Windows",
     "editeur": "Google LLC", "installation": "", "jeu": ""},
    {"nom": "Adobe Acrobat", "cle": "adobeacrobat", "source": "Windows",
     "editeur": "Adobe Inc.", "installation": "", "jeu": ""},
    {"nom": "SuperJeuX", "cle": "superjeux", "source": "Windows",
     "editeur": "Steam", "installation": "", "jeu": "Steam"},
    {"nom": "TrucApp Client", "cle": "trucappclient", "source": "Windows",
     "editeur": "Truc", "installation": "", "jeu": ""},
]


def _dossier(base, nom, taille, age_jours):
    p = os.path.join(base, nom)
    os.makedirs(p, exist_ok=True)
    f = os.path.join(p, "data.bin")
    with open(f, "wb") as fh:
        fh.truncate(taille)
    t = time.time() - age_jours * JOUR
    os.utime(f, (t, t))
    os.utime(p, (t, t))
    return p


def _etat(base):
    etat = {}
    for dossier, _, fichiers in os.walk(base):
        for f in fichiers:
            p = os.path.join(dossier, f)
            st = os.stat(p)
            etat[p] = (st.st_size, st.st_mtime)
    return etat


class TestResidus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.mkdtemp(prefix="tidydeck_residus_")
        cls.roam = os.path.join(cls.base, "Roaming")
        cls.local = os.path.join(cls.base, "Local")
        cls.progdata = os.path.join(cls.base, "ProgramData")
        for z in (cls.roam, cls.local, cls.progdata):
            os.makedirs(z)
        cls.racines = [cls.roam, cls.local, cls.progdata]
        # Ne doivent JAMAIS être proposés : logiciels installés (même anciens).
        _dossier(cls.roam, "Slack", 5 * MO, 210)
        _dossier(cls.roam, "Google", 60 * MO, 220)
        _dossier(cls.roam, "Adobe Acrobat", 25 * MO, 45)
        _dossier(cls.roam, "Adobe Acrobad", 8 * MO, 120)
        _dossier(cls.roam, "SuperJeuX", 40 * MO, 300)
        _dossier(cls.roam, "TrucApp", 10 * MO, 400)
        # Ne doivent pas être proposés : trop récent, trop petit, données perso.
        _dossier(cls.roam, "Recent", 20 * MO, 10)
        _dossier(cls.roam, "PetitReste", 100 * 1024, 400)
        _dossier(cls.roam, "MesSaves", 30 * MO, 400)
        # Seuls candidats valides.
        _dossier(cls.roam, "VieuxLogiciel", 30 * MO, 400)
        _dossier(cls.roam, "ResteMoyen", 12 * MO, 120)
        # Orphelin utilisé par le test des processus.
        _dossier(cls.roam, "ProcApp", 20 * MO, 400)
        # Exclusions et interdits.
        _dossier(cls.roam, "Temp", 5 * MO, 400)
        _dossier(cls.roam, "Windows", 1 * MO, 400)
        _dossier(cls.roam, "Package Cache", 10 * MO, 400)
        _dossier(cls.roam, "Teams", 30 * MO, 400)
        _dossier(cls.roam, "slack.part", 40 * MO, 400)
        _dossier(cls.local, "Packages", 9 * MO, 400)
        _dossier(cls.local, "OneDrive", 70 * MO, 400)
        _dossier(cls.local, "ZVide", 0, 400)
        # Racine nuage (marqueur .dropbox) isolée du reste de Local.
        cls.nuage = os.path.join(cls.local, "DepotNuage")
        os.makedirs(os.path.join(cls.nuage, "AppSynchronisee"))
        open(os.path.join(cls.nuage, ".dropbox"), "wb").close()
        cls.avant = _etat(cls.base)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    def setUp(self):
        # Lecture seule : rien ne doit bouger pendant une analyse.
        self.assertEqual(_etat(self.base), self.avant)

    def _analyse(self, **kw):
        kw.setdefault("installs", INSTALLS)
        res = residus.analyse(racines=self.racines, **kw)
        self.assertEqual(_etat(self.base), self.avant)
        return res

    def noms(self, res):
        return {r["nom"] for r in res["lignes"]}

    # ------------------------------------------- la règle corrigée, en entier
    def test_exemples_reggle_corrigee(self):
        lignes = {r["nom"]: r for r in self._analyse()["lignes"]}
        self.assertEqual(set(lignes), {"VieuxLogiciel", "ResteMoyen", "ProcApp"})
        vieux = lignes["VieuxLogiciel"]
        self.assertEqual(vieux["motif"],
                         "Aucun logiciel installé de ce nom · inactif depuis 13 mois")
        self.assertEqual(vieux["confiance"], "Élevée")
        moyen = lignes["ResteMoyen"]
        self.assertEqual(moyen["motif"],
                         "Aucun logiciel installé de ce nom · inactif depuis 4 mois")
        self.assertEqual(moyen["confiance"], "Moyenne")
        for r in lignes.values():
            self.assertIs(r["preuve_install"], False)
            self.assertTrue(r["motif"].startswith("Aucun logiciel installé"))

    def test_logiciels_installes_jamais_proposes(self):
        n = self.noms(self._analyse())
        for interdit in ("Slack", "Google", "Adobe Acrobat", "Adobe Acrobad",
                         "SuperJeuX", "TrucApp"):
            self.assertNotIn(interdit, n,
                             "un dossier qui correspond à un logiciel installé ne doit jamais sortir")

    def test_trop_recent_petit_ou_donnees_perso(self):
        n = self.noms(self._analyse())
        for interdit in ("Recent", "PetitReste", "MesSaves"):
            self.assertNotIn(interdit, n)

    # ------------------------------------------------------------------ T1
    def test_t1_exclusions_absolues(self):
        n = self.noms(self._analyse())
        for interdit in ("Temp", "Windows", "Package Cache", "Packages"):
            self.assertNotIn(interdit, n)

    # ------------------------------------------------------------------ T2
    def test_t2_dossiers_interdits(self):
        self.assertNotIn("Teams", self.noms(self._analyse()))

    def test_motifs_exclusion(self):
        self.assertTrue(residus.motif_exclusion("Temp"))
        self.assertTrue(residus.motif_exclusion("teams"))
        # La correction : la comparaison est normalisée des deux côtés.
        self.assertTrue(residus.motif_exclusion("Microsoft Edge"))
        self.assertTrue(residus.motif_exclusion("windows defender"))
        self.assertIsNone(residus.motif_exclusion("VieuxLogiciel"))

    def test_exclusions_nouvailles(self):
        for nom in ("google", "discord", "Spotify", "Mozilla", "NVIDIA", "obs-studio"):
            self.assertTrue(residus.motif_exclusion(nom), nom)

    # ------------------------------------------------------------------ T3
    def test_appartenance_logiciel_installe(self):
        for nom in ("Slack", "Google", "Adobe Acrobad", "TrucApp", "SuperJeuX"):
            self.assertTrue(residus.appartient_a_un_logiciel(nom, INSTALLS), nom)
        for nom in ("VieuxLogiciel", "ResteMoyen", "ProcApp"):
            self.assertFalse(residus.appartient_a_un_logiciel(nom, INSTALLS), nom)

    def test_t3_correspondance_partielle_protège(self):
        # « Adobe Acrobad » (faute de frappe) appartient à Adobe Acrobat : plus proposé.
        self.assertNotIn("Adobe Acrobad", self.noms(self._analyse()))

    def test_t3_distance_de_levenshtein(self):
        self.assertEqual(residus.levenshtein("kitten", "sitting"), 3)
        self.assertEqual(residus.levenshtein("slack", "slack"), 0)

    def test_nom_contenant_un_logiciel_est_protégé(self):
        # Un dossier qui CONTIENT le nom d'un logiciel installé (ou l'inverse).
        self.assertTrue(residus.appartient_a_un_logiciel("Google Chrome Beta", INSTALLS))
        self.assertTrue(residus.appartient_a_un_logiciel("Chrome", INSTALLS))

    def test_installlocation_chaque_composante_protège(self):
        # InstallLocation : basename ET chaque composante du chemin protègent.
        inst = INSTALLS + [{
            "nom": "Kaléidoscope", "cle": "kaleidoscope", "source": "Windows",
            "editeur": "Pixel", "installation": r"C:\Program Files\Outil Zeta\ZetaViewer",
            "jeu": ""}]
        for nom in ("ZetaViewer", "Outil Zeta"):
            self.assertTrue(residus.appartient_a_un_logiciel(nom, inst), nom)

    # ------------------------------------------------------------------ T4
    def test_t4_telechargements_inacheves(self):
        self.assertEqual(residus.motif_telechargement("film.mkv.part"),
                         "Téléchargement inachevé")
        self.assertEqual(residus.motif_telechargement("film.crdownload"),
                         "Téléchargement inachevé")
        self.assertNotIn("slack.part", self.noms(self._analyse()))

    # ------------------------------------------------------------------ T5
    def test_t5_processus_en_cours(self):
        self.assertEqual(residus.MOTIF_PROCESSUS, "Programme en cours d'utilisation")
        # ProcApp est un orphelin valide : proposé sans le processus…
        self.assertIn("ProcApp", self.noms(self._analyse()))
        # …jamais tant qu'il tourne.
        self.assertNotIn("ProcApp", self.noms(self._analyse(processus=["ProcApp"])))

    # ------------------------------------------------------------------ T6
    def test_t6_nuage_jamais_propose(self):
        self.assertTrue(residus.est_nuage(os.path.join(self.nuage, "AppSynchronisee")))
        self.assertTrue(residus.est_nuage(os.path.join(self.local, "OneDrive")))
        self.assertFalse(residus.est_nuage(os.path.join(self.roam, "VieuxLogiciel")))
        chimins = " || ".join(os.path.relpath(r["chemin"], self.base)
                              for r in self._analyse()["lignes"])
        for mot in ("OneDrive", "DepotNuage"):
            self.assertNotIn(mot, chimins)

    # ------------------------------------------------------------------ T7
    def test_t7_scan_partiel(self):
        # 18 dossiers triés dans Roaming : la limite coupe avant la fin,
        # VieuxLogiciel (#16) reste dans la liste.
        res = self._analyse(limite_dossiers=16)
        self.assertTrue(res["scan_partiel"])
        self.assertTrue(res["lignes"])

    def test_t7_budget_depose_scan_partiel(self):
        res = self._analyse(budget_s=0.000001)
        self.assertTrue(res["scan_partiel"])

    def test_t7_annulation(self):
        res = self._analyse(cancel=lambda: True)
        self.assertTrue(res["scan_partiel"])
        self.assertEqual(res["lignes"], [])

    # ------------------------------------------------------------------ T8
    def test_t8_aucun_chemin_interdit_ne_sort(self):
        chimins = [os.path.relpath(r["chemin"], self.base) for r in self._analyse()["lignes"]]
        chimins = " || ".join(os.sep + c for c in chimins)
        for mot in ("OneDrive", "Packages", os.sep + "Temp", "DepotNuage"):
            self.assertNotIn(mot, chimins)

    # ------------------------------------------------------------------ T9
    def test_t9_jamais_de_faible(self):
        res = self._analyse()
        self.assertTrue(res["lignes"])
        self.assertNotIn("Faible", {r["confiance"] for r in res["lignes"]})

    # ------------------------------------------------------- garde-fou 3.3
    def test_installs_vide_ne_propose_rien(self):
        res = residus.analyse(racines=self.racines, installs=[])
        self.assertEqual(res["lignes"], [])
        self.assertTrue(res.get("installs_illisibles"))
        self.assertEqual(_etat(self.base), self.avant)

    def test_sans_registre_rien_n_est_propose(self):
        # Registre illisible : il reste Démarrer + Store, la liste est donc
        # incomplète. Tous les orphelins doivent être tus, pas proposés.
        partiel = [{"nom": "TrucApp", "cle": "trucapp", "source": "Démarrer",
                    "editeur": "", "installation": "", "jeu": ""},
                   {"nom": "SuperJeuX", "cle": "superjeux", "source": "Store",
                    "editeur": "", "installation": "", "jeu": "Steam"}]
        res = residus.analyse(racines=self.racines, installs=partiel)
        self.assertEqual(res["lignes"], [])
        self.assertTrue(res.get("installs_illisibles"))
        self.assertEqual(_etat(self.base), self.avant)

    # ------------------------------------------------------- seuil de jours
    def test_seuil_jours_change_la_liste(self):
        self.assertIn("ResteMoyen", self.noms(self._analyse(jours=30)))
        self.assertIn("ResteMoyen", self.noms(self._analyse(jours=90)))
        self.assertNotIn("ResteMoyen", self.noms(self._analyse(jours=180)))
        self.assertIn("VieuxLogiciel", self.noms(self._analyse(jours=180)))

    # ------------------------------------------------------------- divers
    def test_normalisation(self):
        self.assertEqual(residus.normalise("Microsoft Edge Core 1.42"), "microsoftedgecore")
        self.assertEqual(residus.normalise("Google Chrome"), "googlechrome")
        self.assertEqual(residus.normalise("Slack"), "slack")

    def test_tri_par_taille_puis_age(self):
        t = [r["taille"] for r in self._analyse()["lignes"]]
        self.assertEqual(t, sorted(t, reverse=True))

    def test_lignes_selectionnables(self):
        lignes = self._analyse()["lignes"]
        self.assertTrue(lignes)
        for r in lignes:
            self.assertTrue(r["selectable"])
            self.assertFalse(r["selecte"])
            self.assertIs(r["preuve_install"], False)
            self.assertTrue(r["motif"].startswith("Aucun logiciel installé"))

    def test_zones_par_defaut_aucune_ecriture(self):
        residus.zones_par_defaut()
        self.assertEqual(_etat(self.base), self.avant)

    def test_vide_jamais_zero_octet(self):
        res = self._analyse()
        self.assertNotIn("ZVide", self.noms(res))
        for r in res["lignes"]:
            self.assertTrue(r["taille"] >= residus.TAILLE_MIN_OCTETS)


class _Ctx:
    """Contexte minimal pour rendre la vue sans lancer toute l'application."""
    theme = {"bg": "#ffffff", "card": "#fafafa", "line": "#dddddd", "fg": "#000000",
             "muted": "#666666", "accent": "#0000aa", "accent_fg": "#ffffff"}
    status_colors = {"info": "#7A869A"}

    def __init__(self, stream=False):
        self.cfg = {"stream_mode": stream, "serenity": False, "advanced": True}
        self.root = None

    def mask(self, t):
        from Shared.Utils import privacy
        return privacy.mask(str(t), self.cfg["stream_mode"])


FAUX_RESULTAT = {
    "version": residus.RESIDUS_VERSION,
    "lignes": [
        {"nom": "VieuxLogiciel", "chemin": os.path.join(os.sep, "faux", "Roaming", "VieuxLogiciel"),
         "zone": os.path.join(os.sep, "faux", "Roaming"), "taille": 30 * MO,
         "age_jours": 400, "motif": "Aucun logiciel installé de ce nom · inactif depuis 13 mois",
         "confiance": "Élevée", "preuve_install": False, "selectable": True,
         "selecte": False, "enfant": False},
        {"nom": "ResteMoyen", "chemin": os.path.join(os.sep, "faux", "Roaming", "ResteMoyen"),
         "zone": os.path.join(os.sep, "faux", "Roaming"), "taille": 12 * MO,
         "age_jours": 120, "motif": "Aucun logiciel installé de ce nom · inactif depuis 4 mois",
         "confiance": "Moyenne", "preuve_install": False, "selectable": True,
         "selecte": False, "enfant": False},
    ],
    "scan_partiel": False, "non_lus": [], "dossiers_vus": 12, "budget_s": 1, "jours": 90,
}


class TestResidusVue(unittest.TestCase):
    """T10 à T12 : ce que la vue affiche (et surtout ce qu'elle ne fait pas)."""

    def _vue(self, stream=False, loader=None):
        import tkinter as tk
        from UI.Pages.residus_view import ResidusView
        root = tk.Tk()
        root.withdraw()
        ctx = _Ctx(stream)
        ctx.root = root
        vue = ResidusView(root, ctx, loader=loader or (lambda jours, cancel: FAUX_RESULTAT))
        vue.pack()
        t0 = time.time()
        while time.time() - t0 < 5:
            root.update()
            root.update_idletasks()
            texts = self._textes(vue)
            if any("Pourquoi" in t or "proposé(s" in t or "Aucun résidu" in t
                   or "pas pu lire" in t for t in texts):
                break
            time.sleep(0.02)
        return root, vue

    def _textes(self, w, acc=None):
        import tkinter as tk
        from tkinter import ttk as _ttk
        acc = [] if acc is None else acc
        for c in w.winfo_children():
            try:
                t = c.cget("text")
                if isinstance(t, str) and t:
                    acc.append(t)
            except tk_error():
                pass
            if isinstance(c, _ttk.Treeview):
                for iid in c.get_children():
                    acc.extend(str(v) for v in c.item(iid, "values") if v)
            elif isinstance(c, tk.Text):
                try:
                    acc.append(c.get("1.0", "end"))
                except tk_error():
                    pass
            self._textes(c, acc)
        return acc

    def test_vue_affiche_pourquoi_confiance_et_actions(self):
        root, vue = self._vue()
        try:
            tout = " § ".join(self._textes(vue))
            self.assertIn("Pourquoi :", tout)
            self.assertIn("Dernière activité", tout)
            self.assertIn("Élevée", tout)
            self.assertIn("Moyenne", tout)
            self.assertIn("Aucun logiciel installé de ce nom", tout)
            self.assertIn("Ouvrir l'emplacement", tout)
            self.assertIn("VieuxLogiciel", tout)
            self.assertIn("relance", tout.lower())
            self.assertIn("vérifie avant", tout.lower())
        finally:
            root.destroy()

    def test_vue_liste_illisible_le_dis_honnetement(self):
        res = {"version": residus.RESIDUS_VERSION, "lignes": [], "scan_partiel": False,
               "non_lus": [], "installs_illisibles": True}
        root, vue = self._vue(loader=lambda jours, cancel: res)
        try:
            tout = " § ".join(self._textes(vue))
            self.assertIn("pas pu lire la liste des logiciels installés", tout)
            self.assertNotIn("tout est propre", tout.lower())
        finally:
            root.destroy()

    def test_vue_masque_en_mode_discret(self):
        user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        res = dict(FAUX_RESULTAT)
        zone = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        lignes = [dict(r, zone=zone, chemin=os.path.join(zone, r["nom"]))
                  for r in FAUX_RESULTAT["lignes"]]
        root, vue = self._vue(stream=True, loader=lambda jours, cancel: dict(res, lignes=lignes))
        try:
            tout = " § ".join(self._textes(vue))
            if user:
                self.assertNotIn(user, tout)
        finally:
            root.destroy()

    def test_vue_ne_touche_jamais_la_quarantaine(self):
        for f in (residus.__file__,
                  os.path.join(os.path.dirname(residus.__file__), "..", "..",
                               "UI", "Pages", "residus_view.py")):
            src = open(f, encoding="utf-8").read().lower()
            for mot in ("quarantine", "rmtree", "shutil", "winreg.delete", "os.remove"):
                self.assertNotIn(mot, src, f)

    def test_bouton_reserve_au_mode_avance(self):
        src = open(os.path.join(os.path.dirname(residus.__file__), "..", "..",
                                "UI", "Pages", "storage_page.py"), encoding="utf-8").read()
        self.assertIn('if ctx.advanced and not ctx.cfg.get("serenity")', src)
        self.assertIn("show_residus", src)

    def test_bascule_instantanee_entre_boutons(self):
        """Un bouton du dessus doit fermer la vue ouverte : pas de « Retour »."""
        src = open(os.path.join(os.path.dirname(residus.__file__), "..", "..",
                                "UI", "Pages", "storage_page.py"), encoding="utf-8").read()
        for action in ("plan_downloads", "find_old", "find_clips", "apply"):
            self.assertIn(f"self._depuis(self.{action})", src)
        self.assertIn("def _fermer_vues", src)
        self.assertIn("def _depuis", src)


def tk_error():
    import tkinter as tk
    return tk.TclError


if __name__ == "__main__":
    unittest.main()
