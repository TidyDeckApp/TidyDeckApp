# -*- coding: utf-8 -*-
"""Moteur « les plus gros fichiers / dossiers » : c'est du lecture seule sur le
disque de l'utilisateur, donc chaque promesse est testee ici.

Ce qui est verifie : classement, limitation, recursivite sans doublon, fichiers et
dossiers systeme ignores, liens symboliques et jonctions jamais suivis, annulation,
acces refuses avalés sans crash — et le masquage des chemins en mode Discret.
"""
import os
import shutil
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401

from Core.Storage import storage

K = 1024


def _ecrit(p, n):
    with open(p, "wb") as fh:
        fh.write(b"\0" * n)


class ArbreTemporaire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="td_gros_")
        self.racine = os.path.join(self.tmp, "zone")
        os.makedirs(os.path.join(self.racine, "sous1", "niche"))
        os.makedirs(os.path.join(self.racine, "sous2"))
        os.makedirs(os.path.join(self.racine, "vide"))
        _ecrit(os.path.join(self.racine, "petit.bin"), 1 * K)
        _ecrit(os.path.join(self.racine, "moyen.bin"), 3 * K)
        _ecrit(os.path.join(self.racine, "gros.bin"), 5 * K)
        _ecrit(os.path.join(self.racine, "sous1", "niche", "deep.bin"), 2 * K)
        _ecrit(os.path.join(self.racine, "sous1", "a.bin"), 2 * K)
        _ecrit(os.path.join(self.racine, "sous2", "lourd.bin"), 6 * K)
        # fichiers systeme : ne doivent jamais etre comptes
        _ecrit(os.path.join(self.racine, "pagefile.sys"), 9 * K)
        _ecrit(os.path.join(self.racine, "hiberfil.sys"), 9 * K)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------------------------------------------------------- classement
    def test_fichiers_tries_du_plus_gros_au_plus_petit(self):
        r = storage.find_largest(self.racine, limit=10)
        tailles = [s for s, _p, _m in r["files"]]
        self.assertEqual(tailles, sorted(tailles, reverse=True))
        self.assertEqual(tailles[:3], [6 * K, 5 * K, 3 * K])

    def test_fichiers_systeme_jamais_comptes(self):
        r = storage.find_largest(self.racine, limit=50)
        chemins = " ".join(p for _s, p, _m in r["files"]).lower()
        self.assertNotIn("pagefile", chemins)
        self.assertNotIn("hiberfil", chemins)
        self.assertNotIn("swapfile", chemins)
        self.assertTrue(all(s < 9 * K for s, _p, _m in r["files"]),
                        "les 9 Ko systeme ne doivent pas remonter en tete")

    def test_dossiers_un_seulement_le_premier_niveau(self):
        """sinon un dossier et ses sous-dossiers comptent deux fois la meme place"""
        r = storage.find_largest(self.racine, limit=10)
        noms = [n for n, _c, _t in r["folders"]]
        self.assertIn("sous1", noms)
        self.assertIn("sous2", noms)
        self.assertNotIn("niche", noms,
                        "un sous-sous-dossier ne doit pas apparaitre au premier niveau")

    def test_taille_dossier_renvoie_le_contenu_complet(self):
        r = storage.find_largest(self.racine, limit=10)
        par_nom = {n: t for n, _c, t in r["folders"]}
        self.assertEqual(par_nom["sous1"], 4 * K, "2 x 2 Ko recursifs")
        self.assertEqual(par_nom["sous2"], 6 * K)
        self.assertEqual(par_nom["vide"], 0)

    def test_dossiers_les_plus_gros_d_abord(self):
        r = storage.find_largest(self.racine, limit=10)
        taille_premier = r["folders"][0][2]
        self.assertEqual(r["folders"][0][0], "sous2")
        self.assertTrue(all(t <= taille_premier for _n, _c, t in r["folders"]))

    def test_limite_respectee(self):
        r = storage.find_largest(self.racine, limit=2)
        self.assertLessEqual(len(r["files"]), 2)
        self.assertEqual([s for s, _p, _m in r["files"]], [6 * K, 5 * K])

    def test_compte_des_fichiers_parcourus(self):
        r = storage.find_largest(self.racine, limit=50)
        self.assertEqual(r["scanned"], 6, "6 fichiers utilisateur, les 2 systemes exclus")

    def test_plusieurs_racines_a_la_fois(self):
        autre = os.path.join(self.tmp, "autre")
        os.makedirs(autre)
        _ecrit(os.path.join(autre, "geant.bin"), 20 * K)
        r = storage.find_largest([self.racine, autre], limit=10)
        self.assertEqual(r["files"][0][0], 20 * K)
        self.assertIn("sous2", [n for n, _c, _t in r["folders"]])

    def test_racine_inexistante_ne_casse_rien(self):
        r = storage.find_largest(os.path.join(self.tmp, "pas_la"), limit=5)
        self.assertEqual(r["files"], [])
        self.assertEqual(r["folders"], [])
        self.assertFalse(r["cancelled"])

    # ------------------------------------------------- liens et jonctions
    def test_lien_symbolique_reel_n_est_pas_compte(self):
        """Creer un lien demande des droits sous Windows : si impossible, le test se
        declare saute, mais le test force ci-dessous couvre la logique de toute facon."""
        lien = os.path.join(self.racine, "lien_vers_gros.lnk")
        try:
            os.symlink(os.path.join(self.racine, "gros.bin"), lien)
        except OSError:
            self.skipTest("creation de lien symbolique refusee sur ce compte")
        r = storage.find_largest(self.racine, limit=50)
        rendu = [p for _s, p, _m in r["files"]]
        self.assertNotIn(lien, rendu, "le lien est compte comme un fichier de plus")

    def test_dossier_marque_lien_est_ignore(self):
        """Le saut est verifie meme sans droit de creation : on force la reconnais-
        sance du lien. Un dossier-jonction suivi ferait compter deux fois et
        sortir de la zone."""
        avant = storage.find_largest(self.racine, limit=50)
        self.assertIn("sous2", [n for n, _c, _t in avant["folders"]])
        original = storage._is_link
        bloque = os.path.join(self.racine, "sous2")
        try:
            storage._is_link = lambda p: (p == bloque) or original(p)
            apres = storage.find_largest(self.racine, limit=50)
        finally:
            storage._is_link = original
        self.assertNotIn("sous2", [n for n, _c, _t in apres["folders"]],
                        "un dossier reconnu comme lien doit etre ignore, pas scanne")
        self.assertLess(apres["scanned"], avant["scanned"],
                        "les octets du lien ne sont pas comptes une deuxieme fois")

    def test_is_link_reconnait_les_vrais_liens(self):
        self.assertFalse(storage._is_link(self.racine))
        self.assertFalse(storage._is_link(os.path.join(self.racine, "gros.bin")))

    # --------------------------------------------------------- annulation
    def test_annulation_interrompt_sans_crash(self):
        appelee = [0]

        def souvent():
            appelee[0] += 1
            return appelee[0] > 3        # on coupe tres tot

        r = storage.find_largest(self.racine, cancel=souvent, limit=50)
        self.assertTrue(r["cancelled"], "le drapeau d'arret doit etre visible du caller")
        self.assertLess(r["scanned"], 6, "l'arret doit couper avant la fin")

    def test_annule_apres_coupure_tot_reste_coherent(self):
        drapeau = [False]
        vus = [0]

        def cb():
            vus[0] += 1
            if vus[0] > 8:
                drapeau[0] = True
            return drapeau[0]
        r = storage.find_largest(self.racine, cancel=cb, limit=50)
        self.assertTrue(r["cancelled"])
        tailles = [s for s, _p, _m in r["files"]]
        self.assertEqual(tailles, sorted(tailles, reverse=True),
                         "resultat partiel mais toujours trie")

    def test_sans_annulation_rafraichit_tout(self):
        r = storage.find_largest(self.racine, cancel=lambda: False, limit=50)
        self.assertFalse(r["cancelled"])
        self.assertEqual(r["scanned"], 6)

    # ------------------------------------------------- acces refuses
    def test_dossier_inaccessible_ignore_sans_erreur(self):
        bloc = os.path.join(self.racine, "interdit")
        os.makedirs(bloc)
        _ecrit(os.path.join(bloc, "x.bin"), 4 * K)
        original = os.scandir

        def faux(p):
            if str(p) == bloc:
                raise PermissionError("acces refuse")
            return original(p)
        os.scandir = faux
        try:
            r = storage.find_largest(self.racine, limit=50)
        finally:
            os.scandir = original
        noms = [n for n, _c, _t in r["folders"]]
        self.assertNotIn("interdit", noms)
        self.assertIn("sous2", noms, "le reste du scan continue malgré le refus")

    def test_dossier_illisible_est_signale_sans_etre_classe(self):
        """On ne peut pas le mesurer : il ne doit pas etre classe (encore moins a 0)
        mais il doit etre visible du pied de page."""
        bloc = os.path.join(self.racine, "interdit")
        os.makedirs(bloc)
        _ecrit(os.path.join(bloc, "x.bin"), 4 * K)
        original = os.scandir

        def faux(p):
            if str(p) == bloc:
                raise PermissionError("acces refuse")
            return original(p)
        os.scandir = faux
        try:
            r = storage.find_largest(self.racine, limit=50)
        finally:
            os.scandir = original
        self.assertEqual([n for n, _p in r["locked"]], ["interdit"])
        self.assertNotIn("interdit", [n for n, _c, _t in r["folders"]])
        self.assertEqual(r["scanned"], 6, "le refus ne doit pas annuler le reste du compte")

    def test_refus_plus_bas_dans_larbre_ne_bloque_rien(self):
        """Un refus dans un sous-dossier ne rend pas le parent non mesurable :
        on compte ce qui est lisible et on continue."""
        niche = os.path.join(self.racine, "sous1", "niche")
        original = os.scandir

        def faux(p):
            if str(p) == niche:
                raise PermissionError("acces refuse")
            return original(p)
        os.scandir = faux
        try:
            r = storage.find_largest(self.racine, limit=50)
        finally:
            os.scandir = original
        par_nom = {n: t for n, _c, t in r["folders"]}
        self.assertEqual(par_nom["sous1"], 2 * K, "le reste de sous1 est compte")
        self.assertEqual(r["locked"], [], "sous1 reste mesurable")

    # --------------------------------------------------- lecture seule
    def test_le_scan_ne_detruit_rien(self):
        """Aucune suppression, aucun deplacement, aucune reecriture pendant le scan."""
        mefaits = []
        gardes = {}
        for nom in ("remove", "unlink", "renames", "replace", "rmdir"):
            gardes[nom] = getattr(os, nom, None)

        def interdit(*a, **k):
            mefaits.append("os." + nom)
            raise AssertionError("lecture seule : appel interdit")

        for nom in ("remove", "unlink", "renames", "replace", "rmdir"):
            setattr(os, nom, interdit)
        rt = shutil.rmtree

        def rtmp(*a, **k):
            mefaits.append("shutil.rmtree")
            raise AssertionError("lecture seule : rmtree interdit")
        shutil.rmtree = rtmp
        try:
            r = storage.find_largest(self.racine, limit=50)
        finally:
            shutil.rmtree = rt
            for nom, f in gardes.items():
                if f is not None:
                    setattr(os, nom, f)
        self.assertEqual(mefaits, [], "le moteur doit etre strictement en lecture seule")
        self.assertEqual(r["scanned"], 6, "le scan doit ne pas etre vide pour autant")

    def test_les_system_tags_viennent_de_racine_uniquement(self):
        # « windows » dans les Documents du user n'est PAS systeme
        self.assertFalse(storage.is_system_dir("windows", os.path.join(self.racine, "windows")))
        self.assertFalse(storage.is_system_dir("Windows", os.path.join("C:", "Users", "x", "Windows")))
        # mais en racine de disque, oui
        self.assertTrue(storage.is_system_dir("Windows", os.path.join("C:", "Windows")))
        self.assertTrue(storage.is_system_dir("Program Files", "D:\\Program Files"))
        self.assertTrue(storage._at_drive_root("C:\\Users"))
        self.assertFalse(storage._at_drive_root("C:\\Users\\x\\Documents"))

    def test_la_zone_par_defaut_n_est_pas_le_disque_entier(self):
        z = [str(x).rstrip("\\/") for x in storage.largest_zone()]
        self.assertTrue(z, "il faut toujours une zone par defaut")
        for x in z:
            self.assertNotIn(x.lower(), ("c:", "d:", "e:", "f:", "/", "\\"),
                            "la zone par defaut ne doit jamais etre un disque entier")


class _Ctx:
    """Contexte minimal, meme forme que App.mask : le masque passe toujours par
    privacy.mask(texte, stream_mode)."""
    theme = {"bg": "#ffffff", "card": "#fafafa", "line": "#dddddd", "fg": "#000000",
             "muted": "#666666", "accent": "#3366cc"}
    status_colors = {"info": "#3366cc"}
    scale = 1.0

    def __init__(self, stream):
        self.cfg = {"serenity": False, "advanced": True, "colorblind": False,
                   "stream_mode": stream}
        self.root = None

    def mask(self, t):
        from Shared.Utils import privacy
        return privacy.mask(str(t), self.cfg["stream_mode"])


class MasquementDiscretTest(unittest.TestCase):
    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_les_chemins_sont_masques_en_mode_discret(self):
        self._check(stream=True)

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_les_chemins_sont_visibles_hors_mode_discret(self):
        self._check(stream=False)

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_le_pied_de_page_signale_les_dossiers_illlisibles(self):
        import tkinter as tk
        from UI.Pages import largest_view

        ctx = _Ctx(False)
        root = tk.Tk()
        root.withdraw()
        ctx.root = root
        try:
            vue = largest_view.LargestView(root, ctx)
            vue.pack(fill="both", expand=True)
            vue.data = {"files": [], "folders": [], "system": [], "scanned": 3,
                       "locked": [("interdit", os.path.expanduser("~") + r"\interdit")],
                       "cancelled": False}
            vue._render()
            for _ in range(20):
                root.update()
                root.update_idletasks()
            texte = str(vue.foot.cget("text"))
            self.assertIn("inaccessible", texte.lower())
            self.assertIn("interdit", texte, "le nom du dossier bloque doit rester visible")
        finally:
            root.destroy()

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def _check(self, stream):
        import tkinter as tk
        from UI.Pages import largest_view

        classe_vraie = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        nom_fichier = "monteur_de_donners.bin"

        root = tk.Tk()
        root.withdraw()
        ctx = _Ctx(stream)
        ctx.root = root
        try:
            vue = largest_view.LargestView(root, ctx)
            vue.pack(fill="both", expand=True)
            vue.data = {"files": [(5 << 20, os.path.join(os.path.expanduser("~"),
                                                        "Documents", nom_fichier), 0.0)],
                       "folders": [("dossier", os.path.join(os.path.expanduser("~"), "Documents"),
                                    9 << 20)],
                       "system": [], "scanned": 1, "cancelled": False}
            vue.shown = 10
            vue._render()
            for _ in range(30):
                root.update()
                root.update_idletasks()

            texts = []

            def ramasse(w):
                for c in w.winfo_children():
                    try:
                        texts.append(str(c.cget("text")))
                    except Exception:
                        pass
                    ramasse(c)
            ramasse(vue)
            tout = " | ".join(texts)

            if stream:
                self.assertIn(nom_fichier, tout,
                            "les noms de fichiers restent lisibles (c'est voulu et dit)")
                if classe_vraie:
                    self.assertNotIn(classe_vraie, tout,
                                    "le vrai nom d'utilisateur doit disparaitre en mode Discret")
                self.assertNotIn(os.path.expanduser("~"), tout.replace("~", ""),
                                "le chemin personnel ne doit pas etre rendu en clair")
            else:
                self.assertIn(nom_fichier, tout)
        finally:
            root.destroy()


class BarreDeChargementTest(unittest.TestCase):
    """Le texte « Analyse en cours… » est redondant avec le sous-titre de la page :
    le scan doit être annoncé par une barre de chargement, pas du texte en double.
    Et la ligne « Zone : … » + sélecteur de zone sont superflus : chaque ligne du
    résultat affiche déjà son chemin."""

    def _src(self, *parties):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), *parties)
        return open(p, encoding="utf-8").read()

    def test_plus_gros_barre_en_attente(self):
        src = self._src("UI", "Pages", "largest_view.py")
        for interdit in ("Analyse en cours", "rien n'est supprimé, rien n'est écrit"):
            self.assertNotIn(interdit, src, f"texte de scan encore présent : {interdit}")
        self.assertIn("ttk.Progressbar", src)
        self.assertIn("indeterminate", src)
        self.assertIn("start(", src)
        self.assertIn("stop(", src)

    def test_plus_gros_plus_de_ligne_zone(self):
        src = self._src("UI", "Pages", "largest_view.py")
        for interdit in ('"Zone :', "Zone analysée", "Mes dossiers", "Disque entier"):
            self.assertNotIn(interdit, src, f"sélecteur/nom de zone encore présent : {interdit}")

    def test_residus_barre_en_attente(self):
        src = self._src("UI", "Pages", "residus_view.py")
        self.assertNotIn("Recherche en cours", src)
        self.assertIn("ttk.Progressbar", src)
        self.assertIn("indeterminate", src)

    def test_zone_lbl_supprime(self):
        src = self._src("UI", "Pages", "largest_view.py")
        self.assertNotIn("zone_lbl", src)


class PropreteVuesTest(unittest.TestCase):
    """Phrases en double retirées, bouton « Remonter » masqué tant qu'on n'a
    pas foré un dossier, infobulle sur « Copier »."""

    def _src(self, *parties):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), *parties)
        return open(p, encoding="utf-8").read()

    def test_residus_intro_sans_duplication(self):
        src = self._src("UI", "Pages", "residus_view.py")
        self.assertNotIn("ne fait que te les montrer", src)

    def test_page_ne_redit_pas_consultation_seule(self):
        src = self._src("UI", "Pages", "storage_page.py")
        self.assertNotIn('self.say("Consultation seule', src)

    def test_remonter_masque_par_defaut(self):
        src = self._src("UI", "Pages", "largest_view.py")
        build = src[src.index("def _build"):src.index("_build_options")]
        self.assertNotIn("up_btn.pack", build,
                         "« Remonter » ne doit pas être visible au premier affichage")
        self.assertIn("up_btn", src, "remonter doit rester dispo une fois foré")

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_bouton_remonter_pas_visible_du_premier_coup(self):
        import tkinter as tk
        from UI.Pages import largest_view
        root = tk.Tk()
        root.withdraw()
        ctx = _Ctx(False)
        ctx.root = root
        try:
            vue = largest_view.LargestView(root, ctx)
            vue.pack(fill="both", expand=True)
            root.update()
            self.assertEqual(vue.up_btn.winfo_ismapped(), 0,
                             "« Remonter » ne doit apparaître qu'après un double-clic")
        finally:
            root.destroy()

    def test_infobulle_copier(self):
        src = self._src("UI", "Pages", "largest_view.py")
        self.assertIn("Copier le chemin d'accès", src)

    def test_plus_de_bouton_retour(self):
        """On navigue d'onglet en onglet : le « ← Retour » des vues est superflu."""
        for page in ("largest_view.py", "residus_view.py"):
            src = self._src("UI", "Pages", page)
            self.assertNotIn("← Retour", src, f"bouton Retour encore présent dans {page}")

    def test_aucune_duplication_lecture_seule(self):
        """La page dit déjà « Rien n'est supprimé » dans son sous-titre : ni le
        message de statut ni l'intro ne doivent le répéter."""
        page = self._src("UI", "Pages", "storage_page.py")
        self.assertNotIn('self.say("Lecture seule', page)
        lv = self._src("UI", "Pages", "largest_view.py")
        self.assertFalse(any("aucun bouton de suppression" in l
                             for l in lv.splitlines() if "configure(text" in l))


if __name__ == "__main__":
    unittest.main()
