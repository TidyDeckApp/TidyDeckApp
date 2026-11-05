"""Le logo TidyDeck : le fichier est embarque, et il se voit a l'ecran.

Trois accidents reels evites ici :
  * l'executable livre avec la plume Tk par defaut parce que PyInstaller n'a pas
    recu le .ico (ou que les donnees ne sont pas embarquees a cote) ;
  * l'application qui ne se lance plus du tout parce que assets/tidydeck.ico a
    disparu de l'extraction ;
  * la fenetre secondaire (welcome, toast, boite de dialogue) qui garde l'icone
    Tk parce que l'icone ne s'herite pas.
"""
import os
import re
import shutil
import struct
import unittest

from tests import ROOT, HAS_DISPLAY  # noqa: F401

from Shared.Utils import common

ASSETS = os.path.join(ROOT, "assets")
ICO = os.path.join(ASSETS, "tidydeck.ico")
SVG = os.path.join(ASSETS, "tidydeck-logo.svg")
TAILLES_MINIMUM = (16, 24, 32, 48)


def entrees(chemin):
    """(en-tete, [dictes par image]) d'un fichier .ico, sans dependance externe."""
    with open(chemin, "rb") as fh:
        data = fh.read()
    reserve, type_, nombre = struct.unpack_from("<HHH", data, 0)
    images = []
    for i in range(nombre):
        w, h, _, _, plans, bpp, taille, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * i)
        images.append({"largeur": w or 256, "hauteur": h or 256, "plans": plans,
                       "bpp": bpp, "taille": taille, "offset": offset,
                       "entete": data[offset:offset + 4]})
    return {"reserve": reserve, "type": type_, "data": data, "images": images}


class FichierIcoTest(unittest.TestCase):
    def test_le_fichier_est_la(self):
        self.assertTrue(os.path.isfile(ICO), "assets/tidydeck.ico doit accompagner la source")

    def test_c_est_vraiment_une_icone(self):
        e = entrees(ICO)
        self.assertEqual(e["reserve"], 0)
        self.assertEqual(e["type"], 1, "1 = icone (2 = curseur)")

    def test_tailles_attendues(self):
        trouvees = {i["largeur"] for i in entrees(ICO)["images"]}
        for t in TAILLES_MINIMUM:
            self.assertIn(t, trouvees, f"Windows reclame le ico en {t} px (barre de titre)")

    def test_chaque_image_tient_dans_le_fichier(self):
        e = entrees(ICO)
        for i in e["images"]:
            self.assertLessEqual(i["offset"] + i["taille"], len(e["data"]),
                                 "une entree qui depasse la fin du fichier = icone refusee")
            self.assertIn(i["entete"], (b"\x89PNG", b"BM"),
                          "une entree doit etre un PNG ou un BMP")
            self.assertGreaterEqual(i["bpp"], 32, "il faut un canal alpha, sinon fond noir")

    def test_carre_et_transparent_aux_bords(self):
        for i in entrees(ICO)["images"]:
            self.assertEqual(i["largeur"], i["hauteur"], "une icone etiree se voit tout de suite")


class LogoSourceTest(unittest.TestCase):
    def test_le_svg_est_garde(self):
        self.assertTrue(os.path.isfile(SVG),
                        "le .svg source sert a re-generer l'icone : on le garde")
        texte = open(SVG, encoding="utf-8").read()
        self.assertIn("<svg", texte)

    def test_le_svg_contient_la_palette(self):
        texte = open(SVG, encoding="utf-8").read().upper()
        for couleur in ("#1B2B4B", "#F4F7FC", "#C8610A"):
            self.assertIn(couleur, texte, f"couleur de marque {couleur} attendue dans le logo")


class CheminAssetTest(unittest.TestCase):
    def test_chemin_absolu_et_reel(self):
        p = common.chemin_asset("tidydeck.ico")
        self.assertTrue(os.path.isabs(p))
        self.assertTrue(os.path.isfile(p))
        self.assertEqual(os.path.basename(os.path.dirname(p)), "assets")

    def test_embarque_pyinstaller_pointe_sur_meipass(self):
        ancien = getattr(common.sys, "_MEIPASS", None)
        common.sys._MEIPASS = os.path.join(os.sep, "tmp", "bundle123")
        try:
            self.assertEqual(common.chemin_asset("tidydeck.ico"),
                             os.path.join(os.sep, "tmp", "bundle123", "assets", "tidydeck.ico"))
        finally:
            if ancien is None:
                del common.sys._MEIPASS
            else:
                common.sys._MEIPASS = ancien

    def test_ne_sert_pas_un_chemin_vide(self):
        self.assertTrue(common.chemin_asset(""), os.path.isabs(common.chemin_asset("")))


class AppliquerIconeTest(unittest.TestCase):
    def setUp(self):
        if not HAS_DISPLAY:
            self.skipTest("pas d'ecran pour creer une fenetre Tk")

    def test_icone_collee_sur_la_fenetre(self):
        import tkinter as tk
        r = tk.Tk()
        try:
            self.assertTrue(common.appliquer_icone(r),
                            "l'icone doit se coller sans exception sur une vraie fenetre")
        finally:
            r.destroy()

    def test_le_toplevel_herite_de_l_icone(self):
        """welcome, toast et boites de dialogue sont des Toplevel : sans "-default"
        ils gardent la plume Tk, ce qui se voit immediatement a l'ecran.
        Tk pose l'icone sur la classe de fenetre : c'est la qu'on va la chercher."""
        if os.name != "nt":
            self.skipTest("heritage de l'icone verifie sous Windows")
        import ctypes
        import tkinter as tk
        user32 = ctypes.windll.user32
        user32.GetClassLongPtrW.restype = ctypes.c_void_p

        def icone(win):
            return int(user32.GetClassLongPtrW(win.winfo_id(), -34) or 0)  # GCLP_HICONSM

        def mesure(avec):
            r = tk.Tk()
            if avec:
                common.appliquer_icone(r)
            r.update()
            racine = icone(r)
            top = tk.Toplevel(r)
            top.update()
            second = icone(top)
            top.destroy()
            r.destroy()
            return racine, second

        sans_root, sans_top = mesure(False)
        avec_root, avec_top = mesure(True)
        self.assertNotEqual(avec_root, sans_root, "l'icone de la fenetre n'a pas change")
        self.assertNotEqual(avec_top, sans_top,
                            "le Toplevel doit porter l'icone de l'application")
        self.assertEqual(avec_top, avec_root)

    def test_icone_absente_ne_casse_jamais_la_fenetre(self):
        import tkinter as tk
        ancien = common.chemin_asset
        common.chemin_asset = lambda nom: os.path.join(ROOT, "assets_absent", nom)
        r = tk.Tk()
        try:
            self.assertFalse(common.appliquer_icone(r),
                             "icone introuvable = False, surtout pas une exception")
            self.assertTrue(r.winfo_exists(), "la fenetre doit rester vivante")
        finally:
            common.chemin_asset = ancien
            r.destroy()


class BranchePartoutTest(unittest.TestCase):
    def test_l_application_colle_l_icone_apres_la_fenetre(self):
        src = open(os.path.join(ROOT, "UI", "app.py"), encoding="utf-8").read()
        self.assertIn("appliquer_icone", src)
        self.assertLess(src.index("tk.Tk()"), src.index("appliquer_icone(self.root)"),
                        "iconbitmap avant tk.Tk() ne peut pas marcher")

    def test_pas_d_autre_appel_a_iconbitmap(self):
        """Une iconbitmap en dur ailleurs court-circuiterait l'herittance et
        casserait l'embarquement PyInstaller."""
        interets = []
        for dossier, _, fichiers in os.walk(ROOT):
            if any(p in dossier for p in ("__pycache__", os.sep + "tests")):
                continue
            for f in fichiers:
                if not f.endswith(".py") or f.startswith("_"):
                    continue
                p = os.path.join(dossier, f)
                if "iconbitmap" in open(p, encoding="utf-8").read():
                    interets.append(os.path.relpath(p, ROOT))
        self.assertEqual([os.path.join("Shared", "Utils", "common.py")], interets,
                         "seul common.py doit manipuler l'icone")


class LivrableTest(unittest.TestCase):
    def test_la_spec_livree_porte_l_icone_et_les_assets(self):
        spec = os.path.join(ROOT, "packaging", "TidyDeck.spec")
        self.assertTrue(os.path.isfile(spec),
                        "la spec officielle doit etre livree avec la source")
        src = open(spec, encoding="utf-8").read()
        self.assertIn("tidydeck.ico", src, "--icon : sans lui l'exe garde l'icone Windows")
        self.assertIn("assets", src, "--add-data assets : sans lui la fenetre n'a pas d'icone")

    def test_la_spec_ne_compresse_pas_avec_upx(self):
        """UPX est un emballeur : un .exe recollé avec UPX est signalé par beaucoup
        d'antivirus sans autre examen, l'inverse du résultat voulu sur VirusTotal."""
        src = open(os.path.join(ROOT, "packaging", "TidyDeck.spec"), encoding="utf-8").read()
        self.assertNotIn("upx=True", src, "UPX doit rester désactivé")
        self.assertEqual(2, len(re.findall(r"(?m)^\s*upx=False\s*,?\s*$", src)),
                         "upx=False doit être écrit dans EXE et dans COLLECT")

    def test_le_script_installeur_porte_l_icone(self):
        iss = os.path.join(ROOT, "packaging", "tidydeck.iss")
        if not os.path.isfile(iss):
            self.skipTest("installeur Inno non fourni")
        src = open(iss, encoding="utf-8").read()
        self.assertIn("SetupIconFile", src)
        self.assertIn('MyAppPublisher "Florius"', src,
                      "l'editeur affiche dans « Applications installees » doit etre "
                      "le signataire de la licence, pas le nom du logiciel")
        self.assertIn("UninstallDisplayIcon", src,
                      "sans ca, « Ajouter/supprimer » affiche une icone vide")

    def test_distribution_documente_la_bonne_commande(self):
        doc = open(os.path.join(ROOT, "DISTRIBUTION.md"), encoding="utf-8").read()
        self.assertIn("packaging", doc, "DISTRIBUTION.md doit pointer sur la spec livree")
        self.assertIn("tidydeck.spec", doc.lower())

    def test_le_zip_emporte_les_assets_et_pas_de_bytecode(self):
        """_zip.py ecarte les fichiers de chantier : le logo doit survivre au tri,
        les .pyc et _*.py non."""
        try:
            import _zip
        except ImportError:
            self.skipTest("_zip.py n'est pas livre, le tri ne peut pas etre verifie ici")
        import tempfile
        import zipfile
        ouv = tempfile.mkdtemp(prefix="td_tri_")
        dossier = os.path.join(ouv, "projet")
        for sous in ("assets", "Core", "Core\\__pycache__"):
            os.makedirs(os.path.join(dossier, sous))
        open(os.path.join(dossier, "assets", "tidydeck.ico"), "wb").close()
        open(os.path.join(dossier, "Core", "core.py"), "w").close()
        open(os.path.join(dossier, "Core", "__pycache__", "core.pyc"), "wb").close()
        open(os.path.join(dossier, "_chantier.py"), "w").close()
        chemin = os.path.join(ouv, "t.zip")
        with zipfile.ZipFile(chemin, "w") as z:
            _zip._ajoute(z, dossier, "TidyDeck")
        noms = [n.split("/", 1)[1] for n in zipfile.ZipFile(chemin).namelist()]
        shutil.rmtree(ouv, ignore_errors=True)
        self.assertIn("assets/tidydeck.ico", noms)
        self.assertIn("Core/core.py", noms)
        self.assertNotIn("_chantier.py", noms, "un fichier de chantier s'est glisse dans le zip")
        self.assertFalse([n for n in noms if n.endswith(".pyc") or "__pycache__" in n],
                         "du bytecode Python part dans le livrable")


class IdentiteTacheTest(unittest.TestCase):
    """La barre des tâches doit afficher l'icone TidyDeck, pas celle du
    porteur (python.exe quand on lance depuis les sources)."""

    def test_l_identite_donnee_au_processus_est_explicite(self):
        import io
        src = io.open(os.path.join(ROOT, "Shared", "Utils", "common.py"), encoding="utf-8").read()
        self.assertIn("SetCurrentProcessExplicitAppUserModelID", src)
        self.assertIn('"TidyDeck.TidyDeck"', src)

    def test_appelle_avant_la_fenetre(self):
        import io
        src = io.open(os.path.join(ROOT, "UI", "app.py"), encoding="utf-8").read()
        i_id = src.index("identifier_processus_tache()")
        i_tk = src.index("self.root = self.ctx.root = tk.Tk()")
        self.assertLess(i_id, i_tk, "l'identité doit être posée avant la fenêtre")

    @unittest.skipUnless(common.IS_WINDOWS, "Windows uniquement")
    def test_l_appel_reel_ne_crash_pas(self):
        common.identifier_processus_tache()


if __name__ == "__main__":
    unittest.main()
