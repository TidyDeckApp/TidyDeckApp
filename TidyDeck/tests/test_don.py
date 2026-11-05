"""Le canal de don : un seul lien, un seul endroit, et aucune insistance.

TidyDeck vise un public TDAH : un lien discret sur la page « A propos » reste
compatible avec la promesse du logiciel, une sollicitation repetee la detruit.
Ce fichier verrouille les quatre regles ecrites dans DISTRIBUTION.md section 3.
"""
import os
import re
import unittest
from urllib.parse import urlparse

from tests import ROOT  # noqa: F401

from Shared.Utils import common

# Les mots qui transformeraient un lien discret en harcèlement.
INTERDITS = ("premium", "débloquer la version", "s'il te plaît, donne", "urgence",
             "sans toi le projet meurt")


def sources():
    """(chemin relatif, contenu) de tout le code livré, hors fichiers de chantier.

    Les tests sont exclus : ce fichier cite lui-même le lien et le mot « don » pour
    les interdire. Les scripts de chantier (`_*.py`) aussi : ils ne sont pas livrés."""
    for dossier, dirs, fichiers in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith("_")
                   and d != "tests"]
        fichiers = [f for f in fichiers if not f.startswith("_")]
        for f in fichiers:
            if f.endswith(".py"):
                p = os.path.join(dossier, f)
                yield os.path.relpath(p, ROOT).replace("\\", "/"), open(
                    p, encoding="utf-8").read()


class UrlDuCanalTest(unittest.TestCase):
    def test_l_url_est_ecrite_en_https(self):
        self.assertTrue(common.DONATION_URL.startswith("https://"),
                        "un lien de don en http simple se fait réécrire en route")

    def test_un_seul_prestataire_et_pas_deux(self):
        domaine = urlparse(common.DONATION_URL).netloc.lower()
        prestataires = ("ko-fi.com", "buymeacoffee.com", "paypal.com", "patreon.com")
        presents = [p for p in prestataires if p in domaine]
        self.assertEqual(len(presents), 1,
                         "un seul prestataire de don : plusieurs vitrines = harcèlement")
        self.assertEqual("ko-fi.com", presents[0])

    def test_le_lien_vise_bien_tidydeck(self):
        self.assertEqual("https://ko-fi.com/tidydeck", common.DONATION_URL)

    def test_aucun_identifiant_dans_l_url(self):
        self.assertNotIn("token", common.DONATION_URL.lower())
        self.assertNotIn("key=", common.DONATION_URL.lower())


class EmplacementUniqueTest(unittest.TestCase):
    def test_deux_fichiers_seulement_parlent_du_canal(self):
        autorises = {"Shared/Utils/common.py", "UI/Pages/about_page.py"}
        trous = {c for c, src in sources() if "DONATION_URL" in src}
        self.assertEqual(autorises, trous,
                         "le canal de don déborde de son unique emplacement")

    def test_le_lien_n_est_pas_en_dur_ailleurs(self):
        for chemin, src in sources():
            if chemin == "Shared/Utils/common.py":
                continue
            self.assertNotIn("ko-fi", src.lower(),
                             f"une adresse de don recopiée en dur dans {chemin}")

    def test_aucun_bouton_de_don_hors_a_propos(self):
        # Le dictionnaire de traduction contient la chaîne « Faire un don » côté EN :
        # ce n'est pas un bouton, on l'exclut comme les fichiers de chantier.
        pages = [c for c, src in sources()
                 if "Faire un don" in src and c != "Shared/Utils/translations.py"]
        self.assertEqual(["UI/Pages/about_page.py"], pages)

    def test_les_rappels_ne_parlent_jamais_de_don(self):
        """Les rappels sont le seul endroit où TidyDeck prend la parole de sa propre
        initiative : aucun ne doit évoquer l'argent."""
        from Services.Reminders.scheduler import MESSAGES
        texte = " ".join(" ".join(str(m) for m in msg) for msg in MESSAGES.values())
        mots = re.findall(r"[a-zà-ÿ]+", texte.lower())
        for interdit in ("don", "kofi", "premium", "payer", "prix"):
            self.assertNotIn(interdit, mots,
                             "un rappel qui réclame de l'argent casse la promesse")
        self.assertNotIn("ko-fi", texte.lower())


class PromesseSansInsistanceTest(unittest.TestCase):
    def setUp(self):
        self.about = open(os.path.join(ROOT, "UI", "Pages", "about_page.py"),
                          encoding="utf-8").read()

    def test_le_bouton_est_accompagne_du_rappel_qu_rien_n_est_obligatoire(self):
        self.assertIn("Aucun don n'est requis, aucun n'est rappelé", self.about)

    def test_le_bouton_n_apparait_que_si_le_canal_est_decidé(self):
        self.assertIn("if DONATION_URL:", self.about,
                      "le bloc don doit rester conditionné : vide = rien à l'écran")
        self.assertNotIn("Faire un don</", self.about)
        self.assertEqual(1, self.about.count("Faire un don"))

    def test_aucun_vocabulaire_de_palier_premium(self):
        for mot in INTERDITS:
            self.assertNotIn(mot, self.about, f"vocabulaire de palier payant : {mot}")

    def test_le_titre_du_bloc_reste_discret(self):
        self.assertIn('Soutenir TidyDeck', self.about)
        self.assertIsNone(re.search(r"text=(?:T\()?\"[^\"]*(merci|il te reste|offre)", self.about),
                          "le libellé ne doit rien laisser devoir à l'utilisateur")


if __name__ == "__main__":
    unittest.main()
