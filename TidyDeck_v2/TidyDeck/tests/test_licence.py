"""Licence et mentions legales : GPL-3.0 reellement presente, declarations
identiques en mode normal et en mode Serenite, et licences tierces conservees."""
import io
import os
import shutil
import unittest

from tests import ROOT, HAS_DISPLAY  # noqa: F401
from Shared.Utils import lang


def _lire(*parties):
    return io.open(os.path.join(ROOT, *parties), encoding="utf-8").read()


class FichiersLicenceTest(unittest.TestCase):
    def test_LICENSE_racine_est_la_GPL_v3_officielle(self):
        t = _lire("LICENSE")
        self.assertIn("GNU GENERAL PUBLIC LICENSE", t)
        self.assertIn("Version 3, 29 June 2007", t)
        self.assertIn("END OF TERMS AND CONDITIONS", t)
        self.assertGreater(len(t), 30000, "le texte de la GPL doit etre intégral")

    def test_licence_tierce_qrcode_conservee(self):
        t = _lire("vendor", "qrcode", "LICENSE")
        self.assertIn("Lincoln Loop", t)
        self.assertIn("Redistribution and use in source and binary forms", t)
        self.assertIn("Kazuhiko Arase", t, "l'avis d'origine (pyqrnative) doit rester joint")


class LicenceDansAProposTest(unittest.TestCase):
    def test_les_deux_listes_ont_neuf_lignes(self):
        from UI.Pages.about_page import CONDITIONS_CALM, CONDITIONS_FULL
        self.assertEqual(len(CONDITIONS_FULL), 9)
        self.assertEqual(len(CONDITIONS_CALM), 9,
                        "Serenite doit porter le meme contenu, pas moins")

    def test_licence_gpl_anoncee_dans_les_deux_versions(self):
        from UI.Pages.about_page import CONDITIONS_CALM, CONDITIONS_FULL
        self.assertIn("GPL-3.0", CONDITIONS_FULL[-1])
        self.assertIn("GPL-3.0", CONDITIONS_CALM[-1])
        self.assertIn("LICENSE", CONDITIONS_FULL[-1])
        self.assertIn("LICENSE", CONDITIONS_CALM[-1])

    def test_corrections_jurigiques_dans_le_texte_complet(self):
        from UI.Pages.about_page import CONDITIONS_FULL
        blob = "\n".join(CONDITIONS_FULL)
        self.assertIn("dans les limites permises par la loi", blob)
        self.assertIn("Rien n'est élevé sans ton accord", blob)
        self.assertNotIn("Rien n'est fait sans ta validation", blob)

    def test_ligne_applis_preinstallees(self):
        from UI.Pages.about_page import CONDITIONS_CALM, CONDITIONS_FULL
        self.assertIn("Applications préinstallées", "\n".join(CONDITIONS_FULL))
        self.assertIn("applis préinstallées", "\n".join(CONDITIONS_CALM).lower())

    def test_ligne_vie_privee(self):
        from UI.Pages.about_page import CONDITIONS_CALM, CONDITIONS_FULL
        self.assertIn("Vie privée", "\n".join(CONDITIONS_FULL))
        self.assertIn("Tes données restent chez toi", "\n".join(CONDITIONS_CALM))

    def test_ne_rien_promettre_sur_le_reseau(self):
        from UI.Pages.about_page import CONDITIONS_FULL
        blob = "\n".join(CONDITIONS_FULL)
        self.assertIn("le seul accès réseau est le bouton", blob)


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
class RenduAProposTest(unittest.TestCase):
    def setUp(self):
        import json
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="td_lic_")
        self.saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp
        d = os.path.join(self.tmp, "TidyDeck")
        os.makedirs(d, exist_ok=True)
        from tests.test_round3 import BASE_CFG
        with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as f:
            json.dump(BASE_CFG, f)

    def tearDown(self):
        if self.saved is not None:
            os.environ["LOCALAPPDATA"] = self.saved
        else:
            os.environ.pop("LOCALAPPDATA", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _blob(self, serene):
        from UI.app import App
        app = App()
        lang.set_lang("fr")
        app.ctx.cfg["serenity"] = serene
        app.rebuild()
        app.goto("À propos")
        app.root.update()
        out = []

        def promene(w):
            for c in w.winfo_children():
                promene(c)
            try:
                out.append(str(c.cget("text")))
            except Exception:
                pass
        promene(app.pages["À propos"])
        app.root.destroy()
        return "\n".join(out)

    def test_gpl_visible_en_mode_normal_et_serein(self):
        for serene in (False, True):
            blob = self._blob(serene)
            self.assertIn("GPL-3.0", blob, f"licence absente en serene={serene}")


if __name__ == "__main__":
    unittest.main()
