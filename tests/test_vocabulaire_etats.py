# -*- coding: utf-8 -*-
"""Vocabulaire des etats, selon la NATURE de ce qu'on montre.

« Calmer Windows » = des reglages que TOI tu appliques -> « ✔ Appliqué » / « ✕ Pas appliqué ».
Démarrage et Services = l'etat d'une chose qui tourne ou non. Dire « Appliqué » la-bas
ferait croire qu'on a deja agi sur Spotify, alors que « Actif » veut dire : il se lance
avec Windows. Donc « ✔ Actif » / « ✕ Désactivé » sur ces deux pages.

Un changement pas encore applique ne s'appelle jamais Actif ni Appliqué : il dit
« Sera désactivé » / « Sera réactivé ». Le symbole (✔ / ✕ / ⏻ / ⏼ / 🔒) reste colle
au mot : la couleur ne porte jamais l'info seule."""
import os
import unittest

from tests import ROOT

CALME = os.path.join(ROOT, "UI", "Pages", "tweaks_page.py")
PAGES = {"Démarrage": os.path.join(ROOT, "UI", "Pages", "startup_page.py"),
         "Services": os.path.join(ROOT, "UI", "Pages", "services_page.py")}
ETAT_PAS_APPLIQUE = ("✔ Appliqué", "✕ Pas appliqué")   # reserve a Calmer Windows
ETAT_MATERIEL = ("✔ Actif", "✕ Désactivé")             # Démarrage + Services
SYMBOLES = ("✔", "✕", "⏻", "⏼", "↩", "🔒", "⚠")


def _src(page):
    with open(PAGES[page], encoding="utf-8") as f:
        return f.read()


class VocabulaireSelonLaPageTest(unittest.TestCase):
    def test_calmer_windows_seul_dit_applique(self):
        from UI.Pages.tweaks_page import BASE
        self.assertEqual((BASE["active"][0], BASE["inactive"][0]),
                         ("✔ Appliqué", "✕ Pas appliqué"))
        with open(CALME, encoding="utf-8") as f:
            self.assertIn("✔ Appliqué", f.read())

    def test_demarrage_et_services_ne_disent_plus_applique(self):
        for page in PAGES:
            src = _src(page)
            for mot in ETAT_PAS_APPLIQUE:
                self.assertNotIn(mot, src, f"{page} dit encore « {mot} » : « Appliqué » "
                                          "veut dire « on a agi », pas « ça tourne »")

    def test_demarrage_et_services_disent_actif_desactive(self):
        for page in PAGES:
            src = _src(page)
            for mot in ETAT_MATERIEL:
                self.assertIn(mot, src, f"{page} n'affiche plus « {mot} »")

    def test_le_mot_applique_nulle_part_comme_etat_d_une_ligne(self):
        """« Appliquer » (le bouton) reste autorise : seul le mot d'etat est regle."""
        for page in PAGES:
            for ligne in _src(page).splitlines():
                if "Appliqué" in ligne:
                    self.fail(f"{page} : « Appliqué » revient dans « {ligne.strip()} »")


class DemarrageStatutTest(unittest.TestCase):
    def _e(self, enabled, level="safe", policy=False):
        return {"enabled": enabled, "level": level, "policy": policy}

    def _info(self, e, checked):
        from UI.Pages.startup_page import StartupPage
        return StartupPage._info(None, e, checked)

    def test_lance_au_demarrage_donc_actif(self):
        self.assertEqual(self._info(self._e(True), True), "✔ Actif · Désactivable sans risque")

    def test_pas_lance_donc_desactive(self):
        # désactivé = le conseil n'a plus de sens, on ne l'affiche pas
        self.assertEqual(self._info(self._e(False), False), "✕ Désactivé")

    def test_essentiel_actif(self):
        self.assertTrue(self._info(self._e(True, "keep"), True).startswith("✔ Actif"))

    def test_en_attente_de_desactivation(self):
        self.assertEqual(self._info(self._e(True), False), "⏻ Sera désactivé · Désactivable sans risque")

    def test_en_attente_de_reactivation(self):
        self.assertEqual(self._info(self._e(False), True), "⏼ Sera réactivé · Désactivable sans risque")

    def test_verrou_administrateur(self):
        self.assertEqual(self._info(self._e(True, policy=True), False),
                         "🔒 Géré par ton administrateur")

    def test_un_changement_en_attente_ne_dit_jamais_actif_ni_desactive(self):
        for e, coche in ((self._e(True), False), (self._e(False), True)):
            t = self._info(e, coche)
            self.assertNotIn(t[:8], ("✔ Actif ", "✕ Désact"),
                            f"un choix pas encore applique ne doit pas presenter un etat fige : « {t} »")

    def test_conseil_conserve(self):
        for lev, mot in (("keep", "Essentiel"), ("safe", "sans risque"),
                        ("maybe", "Selon ton usage"), ("unknown", "Inconnu")):
            self.assertIn(mot, self._info(self._e(True, lev), True))


class ServicesStatutTest(unittest.TestCase):
    def _page(self, mode):
        from Core.Health import services
        from UI.Pages.services_page import ServicesPage
        sid = services.SERVICES[0]["id"]
        faux = ServicesPage.__new__(ServicesPage)
        faux.states = {sid: {"mode": mode}}
        return faux, sid

    def test_service_qui_tourne_est_actif(self):
        p, sid = self._page("manual")
        self.assertTrue(p._base(sid).startswith("✔ Actif"), p._base(sid))

    def test_service_arrete_est_desactive(self):
        p, sid = self._page("disabled")
        self.assertTrue(p._base(sid).startswith("✕ Désactivé"), p._base(sid))

    def test_conseil_seulement_si_actif(self):
        from Core.Health import services
        from UI.Pages.services_page import LV
        p, sid = self._page("disabled")
        self.assertNotIn(LV[services.BY_ID[sid]["level"]], p._base(sid))
        p2, sid2 = self._page("manual")
        self.assertIn(LV[services.BY_ID[sid2]["level"]], p2._base(sid2))


class DoubleCanalTest(unittest.TestCase):
    """Mode daltonien / niveaux de gris : chaque etat porte un symbole, pas que la couleur."""

    def test_chaque_statut_commence_par_un_symbole(self):
        from UI.Pages.startup_page import StartupPage
        textes = [StartupPage._info(None, {"enabled": en, "level": lev, "policy": pol}, coche)
                 for en in (True, False) for lev in ("keep", "safe", "maybe", "unknown")
                 for coche, pol in ((True, False), (False, False), (False, True))]
        for t in textes:
            self.assertIn(t[0], SYMBOLES, f"pas de symbole pour « {t} »")

    def test_les_deux_etats_ne_se_ressemblent_pas(self):
        from UI.Pages.startup_page import StartupPage
        a = StartupPage._info(None, {"enabled": True, "level": "safe", "policy": False}, True)
        b = StartupPage._info(None, {"enabled": False, "level": "safe", "policy": False}, False)
        self.assertNotEqual(a[0], b[0])
        self.assertNotEqual(a, b)


class StylesDeStatutInchangesTest(unittest.TestCase):
    """Les jetons de couleur (ok/info/warn/off) ne changent pas : Sérénité et palette
    daltonien les retracent deja au niveau du theme."""

    def test_demarrage_jetons_connus(self):
        from UI.Pages.startup_page import LEVEL
        for lev, (_i, _t, st) in LEVEL.items():
            self.assertIn(st, ("ok", "info", "warn", "danger", "off"), lev)

    def test_serenite_ne_garde_ni_rouge_ni_orange(self):
        from UI.theme import STATUS
        for cle in (("clair", False), ("sombre", False), ("tdah", False),
                    ("clair", True), ("sombre", True), ("tdah", True)):
            for nom in STATUS[cle]:
                self.assertIsInstance(STATUS[cle][nom], str)


class SereniteDemarrageTest(unittest.TestCase):
    """En Sérénité, la phrase d'accompagnement doit suivre la largeur reelle du
    bloc (auto_wrap + fill="x") : sinon elle est rogneee a droite de la fenetre."""

    def test_la_phrase_serenite_ne_rogne_plus(self):
        import re
        src = _src("Démarrage")
        self.assertRegex(src, re.compile(r'auto_wrap\(ttk\.Label\(self\.serene_box.*?fill="x"', re.S),
                        "la phrase Sérénité de Démarrage n'est plus contrainte en largeur")


if __name__ == "__main__":
    unittest.main()
