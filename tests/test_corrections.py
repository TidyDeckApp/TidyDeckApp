# -*- coding: utf-8 -*-
"""Corrections demandées après relecture (lot « encore à corriger »).

Couvre : séparation données/phrase du journal, inversion FR/EN à l'écriture,
barème Sérénité « mots à la place des chiffres », radios ◉/○, symboles,
panneau de détail,Steam en vraie casse, résidus « peut contenir des sauvegardes ».
"""
import io
import os
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Shared.Utils import lang
from Shared.Utils.common import mots_espace, human_size, formater_espace
from UI.Pages.journal_page import detail_journal
from Core.Storage.residus import (contient_donnees_utilisateur, sur_zone_interdite,
                                  JOURS_QUARANTAINE_RESIDUS)

MB = 1024 * 1024


def _src(rel):
    return io.open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()


class LangueCourante(unittest.TestCase):
    def tearDown(self):
        lang.set_lang("fr")


class DetailNettoyageTest(LangueCourante):
    DETAIL_LEGACY = ("Mis en quarantaine : 3 éléments. Ignorés (utilisés) : 23. "
                     "Corbeille vidée (définitif) : 0 o. Éléments : Fichiers temporaires (utilisateur)")

    def test_donnees_structures_en(self):
        lang.set_lang("en")
        e = {"meta": {"clean": {"q": 3, "skip": 23, "recyc": 0,
                                "items": ["Fichiers temporaires (utilisateur)"]}},
             "details": ""}
        out = detail_journal(e)
        self.assertTrue(out.startswith("Cleanup: 3 set aside"), out)
        self.assertIn("skipped (in use)", out)
        self.assertIn("0 B", out)
        self.assertNotIn("Mis en quarantaine", out)

    def test_legacy_fr_traduit_en(self):
        lang.set_lang("en")
        out = detail_journal({"details": self.DETAIL_LEGACY})
        self.assertTrue(out.startswith("Cleanup: 3 set aside"), out)
        self.assertIn("0 B", out)

    def test_legacy_fr_reste_fr(self):
        out = detail_journal({"details": self.DETAIL_LEGACY})
        self.assertEqual(out, self.DETAIL_LEGACY)

    def test_legacy_deplacements(self):
        lang.set_lang("en")
        self.assertEqual(detail_journal({"details": "4 fichiers déplacés."}), "4 files moved.")
        self.assertEqual(detail_journal({"details": "1 fichier mis en quarantaine."}), "1 file quarantined.")


class CanonLangueTest(unittest.TestCase):
    def test_titres_journal_stockes_en_fr(self):
        # Les écritures dans le journal ne passent plus par T() : la langue de
        # l'affichage décide, pas la langue du moment de l'action.
        self.assertNotIn('journal.add("tweaks", (T(', _src("Core/Tweaks/tweaks.py"))
        self.assertNotIn('journal.add("tweaks_off", (T(', _src("Core/Tweaks/tweaks.py"))
        self.assertNotIn('T("{v0} service Windows désactivé")', _src("Core/Health/services.py"))
        self.assertNotIn('T("{v0} service Windows remis comme avant")', _src("Core/Health/services.py"))
        self.assertNotIn('T("{v0} fichier déplacé.")', _src("Core/Storage/storage.py"))

    def test_cleaner_stocke_des_donnees(self):
        src = _src("Core/Health/cleaner.py")
        self.assertIn('"clean": {"q": len(pairs)', src)
        self.assertIn("journal.add(\"pairs\", \"Nettoyage\", \"\"", src)

    def test_colonne_action(self):
        self.assertIn('T("Action")', _src("UI/Pages/journal_page.py"))


class BaremeEspaceTest(unittest.TestCase):
    def test_seuils(self):
        self.assertEqual(mots_espace(0), "un peu de place")
        self.assertEqual(mots_espace(49 * MB), "un peu de place")
        self.assertEqual(mots_espace(50 * MB), "de la place")
        self.assertEqual(mots_espace(1024 * MB - 1), "de la place")
        self.assertEqual(mots_espace(1024 * MB), "une bonne place")
        self.assertEqual(mots_espace(10 * 1024 * MB), "beaucoup de place")
        self.assertEqual(mots_espace(500 * 1024 * MB), "beaucoup de place")

    def test_formater_espace(self):
        self.assertEqual(formater_espace(1234), human_size(1234))
        self.assertEqual(formater_espace(1234, serene=True), "un peu de place")


class SauvegardesResidusTest(unittest.TestCase):
    def test_detection(self):
        tmp = tempfile.mkdtemp(prefix="td_saves_")
        def dossier(*parts):
            p = os.path.join(tmp, *parts)
            os.makedirs(p, exist_ok=True)
            return p
        g1 = dossier("GameX")
        os.makedirs(os.path.join(g1, "Saved", "SaveGames"))
        g2 = dossier("GameY")
        os.makedirs(os.path.join(g2, "Saves"))
        g3 = dossier("GameZ")
        open(os.path.join(g3, "slot.save"), "w").close()
        g4 = dossier("CacheNetto")
        g5 = dossier("Vide")
        g6 = dossier("Stock")
        open(os.path.join(g6, "local.sqlite"), "w").close()
        self.assertTrue(contient_donnees_utilisateur(g1))
        self.assertTrue(contient_donnees_utilisateur(g2))
        self.assertTrue(contient_donnees_utilisateur(g3))
        self.assertFalse(contient_donnees_utilisateur(g4))
        self.assertFalse(contient_donnees_utilisateur(g5))
        self.assertTrue(contient_donnees_utilisateur(g6))

    def test_zones_interdites(self):
        self.assertTrue(sur_zone_interdite(r"C:\Users\p\Documents\ResteAncien"))
        self.assertTrue(sur_zone_interdite(r"C:\Users\p\Saved Games\Jeu"))
        self.assertTrue(sur_zone_interdite(r"C:\Users\p\OneDrive\Reste"))
        self.assertTrue(sur_zone_interdite(r"C:\Steam\steamapps\commun\Jeu"))
        self.assertTrue(sur_zone_interdite(r"C:\Users\p\AppData\Roaming\Epic Games\Reste"))
        self.assertFalse(sur_zone_interdite(r"C:\Users\p\AppData\Roaming\VieuxLogiciel"))

    def test_quarantaine_residus_30_jours(self):
        self.assertEqual(JOURS_QUARANTAINE_RESIDUS, 30)


class SourcesCorrectifsTest(unittest.TestCase):
    def test_titre_fenetre_reconstruit(self):
        src = _src("UI/app.py")
        self.assertGreaterEqual(src.count('self.title = T("{v0} — Le ménage de ton PC'), 2)

    def test_accueil_phrases_t(self):
        src = _src("UI/Home/home.py")
        self.assertIn('T("• Ce que je ne fais jamais ici', src)
        self.assertIn('Collapsible(f, T("Ce que fait exactement ce bouton")', src)

    def test_services_bouton_rayons(self):
        src = _src("UI/Pages/services_page.py")
        self.assertIn('T("✔ Appliquer mes choix…")', src)
        self.assertIn("RadiOpt(", src)

    def test_radios_opt_et_theme(self):
        comp = _src("UI/components.py")
        self.assertIn("class RadiOpt", comp)
        self.assertIn('T("C\'est fait, doucement.")', comp)
        self.assertIn('T("Remettre comme avant")', comp)
        theme = _src("UI/theme.py")
        self.assertIn("Opt.TRadiobutton", theme)
        self.assertIn(".TScrollbar", theme)

    def test_settings_texte_tray(self):
        self.assertIn("La croix cache la fenêtre.", _src("UI/Pages/settings_page.py"))

    def test_steam_vraie_casse(self):
        self.assertIn("[_joli_chemin(p) for p in dict.fromkeys(libs)]", _src("Core/Games/games.py"))

    def test_serenite_deux_versions(self):
        src = _src("UI/routine.py")
        self.assertIn("mots_espace(", src)
        self.assertIn('T("Il n\'y avait rien à ranger pour l\'instant.")', src)

    def test_residus_garde_sauvegardes(self):
        src = _src("Core/Storage/residus.py")
        self.assertIn("if sur_zone_interdite(e.path) or contient_donnees_utilisateur(e.path):", src)
        self.assertIn("MARQUEURS_DONNEES", src)
        self.assertIn("EXTENSIONS_DONNEES", src)
        self.assertIn('"JOURS_QUARANTAINE_RESIDUS"'.replace('"', "")[:24], src)

    def test_residus_annonce_30_jours(self):
        src = _src("UI/Pages/residus_view.py")
        self.assertIn("quarantaine", src)
        self.assertIn("30 jours", src)

    def test_dictionnaire_nouvelles_cles(self):
        from Shared.Utils.translations import EN
        for k in ("Tu as libéré {espace}. Rien n'est perdu : tu peux tout remettre pendant {j} jours.",
                  "C'est fait, doucement.", "Remettre comme avant",
                  "Il n'y avait rien à ranger pour l'instant.",
                  "un peu de place", "de la place", "une bonne place", "beaucoup de place",
                  "Action",
                  "Si un jour un dossier est mis de côté, la quarantaine proposée sera de "
                  "30 jours (au lieu de 7), annulable depuis Journaux.",
                  "La croix cache la fenêtre. Double-clique sur l'icône près de "
                  "l'horloge (ou clic droit > Ouvrir) pour la faire revenir."):
            self.assertIn(k, EN, k)
        self.assertNotIn("Temp + Caches", EN["Avec le mode express, l'étape 2 saute : je range directement "
                        "les fichiers sûrs (Temp + Caches), sans aperçu ni confirmation, d'un seul trait.\n"
                        "Toujours annulable pendant {j} jours depuis la page Journaux."])
        for k, v in EN.items():
            if "volontairement pas dans cette liste" in k:
                self.assertNotIn("NOT", v)
                self.assertIn("intentionally not in this list", v)


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
class RadiOptTest(unittest.TestCase):
    def test_symbole_suivant_variable(self):
        import tkinter as tk
        from UI.components import RadiOpt
        root = tk.Tk()
        root.withdraw()
        try:
            var = tk.StringVar(value="b")
            rb = RadiOpt(root, text="Alpha", variable=var, value="a")
            self.assertEqual(rb.cget("text"), "○ Alpha")
            var.set("a")
            self.assertEqual(rb.cget("text"), "● Alpha")
            var.set("c")
            self.assertEqual(rb.cget("text"), "○ Alpha")
        finally:
            root.destroy()


class NuageRangementTest(unittest.TestCase):
    def test_storage_page_importe_nuage(self):
        """Ruff a trouvé un NameError (cloud undefined) : l'import doit exister."""
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(racine, "UI", "Pages", "storage_page.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("from Shared.Utils import cloud", src)
        self.assertIn("cloud.avertissement(paths)", src)


if __name__ == "__main__":
    unittest.main()
