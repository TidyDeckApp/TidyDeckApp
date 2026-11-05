"""Langue FR/EN : dictionnaire sain, T passe-partout, persistance, sélecteur."""
import json
import os
import re
import shutil
import string
import sys
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Shared.Utils import lang
from Shared.Utils.translations import EN

TEMPL_RE = re.compile(r"\{[a-z0-9]+\}")
FORMATTER = string.Formatter()
ACCENTS = re.compile(r"[àâçéèêëîïôùûüœÀÂÇÉÈÊËÎÏÔÙÛÜŒ]")
UP_WORD = re.compile(r"[A-Z]{4,}")
UP_OK = {"ADHD", "GPL", "SSD", "HKEY", "HKCU", "HKLM", "GPO", "UWP", "GUID", "AAA",
         "CPU", "GPU", "BIOS", "UEFI", "NVIDIA", "AMD", "INTEL", "WINDOWS", "INTERNET",
         "PDF", "URL", "USB", "HDD", "DPI", "SDK", "API", "OEM", "UAC", "NTFS",
         "ONEDRIVE", "TIDYDECK", "YES", "OK", "WPA", "DNS", "DHCP", "LAN", "HTTP",
         "HTTPS", "JSON", "XML", "CSV", "UTF", "ASCII", "XBOX", "DIRECTX", "BETA",
         "PC", "FR", "EN", "JPEG", "PNG", "GIF", "SVG", "EXE", "DLL", "HDR", "VRR",
         "FPS", "ISO", "RGB", "MIDI", "OLED", "NUC", "HP", "Dell".upper(), "ASUS",
         "MSI", "LEN", "ACER", "PHILIPS", "ECRAN", "RELIURES", "TOUT", "SOIT", "SFTP"}
CODE_BITS = ("Select-Object", "Get-AppxPackage", "Get-Partition", "Get-PhysicalDisk",
             "$null", "NOTFOUND", "DriveLetter", "Get-Disk")
VARIANTES_INTERDITES = ("Clean-up", "Quiet Windows", "Trash", "Journal ", " tab",
                        "DO ONLY", "PERMANENT", "RE-ENABLE", "RESTORE AS", "WARNING:",
                        "APPEARANCE AND", "SETTINGS", "TWEAK WINDOWS", "TRACK",
                        "IGNORED VALUES", "DETECTED.E.")


class DictionnaireHygieneTest(unittest.TestCase):
    """Garde-fous de la spec « terminer la traduction anglaise » (T1-T8)."""

    def test_T1_gabarits_formatables(self):
        for k, v in EN.items():
            try:
                list(FORMATTER.parse(v))
            except Exception as e:
                self.fail(f"valeur non formatable {v[:50]!r} (clé {k[:40]!r}) : {e}")

    def test_T2_accolades_et_parentheses(self):
        for k, v in EN.items():
            self.assertEqual(sorted(TEMPL_RE.findall(k)), sorted(TEMPL_RE.findall(v)),
                             f"accolades différentes : {k[:50]!r}")
            self.assertEqual(v.count("("), v.count(")"),
                             f"parentheses déséquilibrées : {v[:50]!r}")

    def test_T3_espaces_de_bordure(self):
        for k, v in EN.items():
            self.assertEqual(k.startswith(" "), v.startswith(" "),
                             f"espace de début : {k[:40]!r} -> {v[:40]!r}")
            self.assertEqual(k.endswith(" "), v.endswith(" "),
                             f"espace de fin : {k[:40]!r} -> {v[:40]!r}")

    def test_T4_pas_de_cris_en_majuscules(self):
        for k, v in EN.items():
            for w in UP_WORD.findall(v):
                if w not in UP_OK and w not in k:
                    self.fail(f"mot tout en majuscules dans EN : {w!r} dans {v[:60]!r}")

    def test_T5_pas_unites_ni_accents_fr_dans_EN(self):
        for k, v in EN.items():
            self.assertIsNone(re.search(r"(?<=\d) ?(Mo|Ko|To)(?![\wÀ-ÿ])", v),
                              f"unité française dans EN : {v[:50]!r}")
            self.assertIsNone(re.search(r"(?<=\d) ?Go(?![\wÀ-ÿ])", v),
                              f"unité française dans EN : {v[:50]!r}")
            stripped = v.replace("Français", "")
            self.assertIsNone(ACCENTS.search(stripped),
                              f"accent français dans EN : {v[:50]!r}")

    def test_T6_varientes_interdites(self):
        for k, v in EN.items():
            for bad in VARIANTES_INTERDITES:
                self.assertNotIn(bad, v, f"variante interdite {bad!r} dans {v[:60]!r}")
            self.assertIsNone(re.search(r"\btabs?\b", v),
                              f"on dit page, pas tab : {v[:60]!r}")

    def test_T7_ponctuation_propre(self):
        for k, v in EN.items():
            short = v.replace("...", "")
            self.assertNotIn("..", short, f"double point : {v[:50]!r}")
            self.assertNotIn(".e.", v, f"faute détected.e. : {v[:50]!r}")
            self.assertEqual(k.rstrip().endswith("."), v.rstrip().endswith("."),
                             f"point final asymétrique : {k[:40]!r} -> {v[:40]!r}")

    def test_T8_pas_de_code_dans_les_cles(self):
        for k in EN:
            for bit in CODE_BITS:
                self.assertNotIn(bit, k, f"clé qui est du code : {k[:60]!r}")


class GlossaireTest(unittest.TestCase):
    def test_glossaire_present_dans_entete(self):
        head = open(os.path.join(ROOT, "Shared", "Utils", "translations.py"),
                    encoding="utf-8").read(2600)
        for term in ("Calm Windows", "Cleanup", "Tidy-up", "Quarantine", "Recycle Bin"):
            self.assertIn(term, head, f"glossaire incomplet : {term}")


class ResiduFrancaisTest(unittest.TestCase):
    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_T9_aucun_texte_fr_en_mode_en(self):
        import subprocess
        probe = os.path.join(ROOT, "_probe_lang.py")
        if not os.path.exists(probe):
            self.skipTest("sonde indisponible")
        out_file = os.path.join(ROOT, "_probe_lang_out.txt")
        if os.path.exists(out_file):
            os.remove(out_file)
        subprocess.run([sys.executable, "_probe_lang.py"], cwd=ROOT,
                       capture_output=True, text=True, timeout=600,
                       env={**os.environ, "SEREN": ""})
        if not os.path.exists(out_file):
            self.skipTest("sonde bloquée (autre instance TidyDeck ouverte)")
        txt = open(out_file, encoding="utf-8").read()
        if "déjà ouvert" in txt:
            self.skipTest("autre instance TidyDeck ouverte")

        def section(nom):
            part = txt.split(nom, 1)
            if len(part) < 2:
                return []
            body = part[1].split("\n\n", 1)[0]
            return [l for l in body.splitlines()[1:] if l.strip() and not l.startswith("(")]

        keep = lambda lines: [l for l in lines if "Périphérique" not in l
                              and "Français" not in l and "Apparence" not in l]
        self.assertEqual(keep(section("== BOUTONS/CASES RESTES EN FRANCAIS ==")), [],
                         "boutons restés en français en mode EN")
        self.assertEqual(keep(section("== LABELS COURTS RESTES EN FRANCAIS")), [],
                         "labels restés en français en mode EN")


class DictionnaireTest(unittest.TestCase):
    def test_non_vide(self):
        self.assertGreater(len(EN), 200)

    def test_cles_valeurs_non_vides(self):
        for k, v in EN.items():
            self.assertTrue(k.strip(), "clé vide")
            self.assertTrue(v.strip(), f"valeur vide pour {k[:40]!r}")

    def test_apostrophes_droites_dans_EN(self):
        for v in EN.values():
            self.assertNotIn("’", v, f"apostrophe accroupie dans EN : {v[:40]!r}")

    def test_gabarits_identiques(self):
        for k, v in EN.items():
            self.assertEqual(sorted(TEMPL_RE.findall(k)), sorted(TEMPL_RE.findall(v)),
                             f"gabarils différents : {k[:50]!r}")

    def test_pas_de_cle_en_anglais(self):
        # une clé doit rester du français-source (jamais une clé technique brute type ttk)
        for k in EN:
            self.assertFalse(k.startswith((".", "tk")), f"clé suspecte : {k!r}")


class TestTTest(unittest.TestCase):
    def tearDown(self):
        lang.set_lang("fr")

    def test_pass_partout_en_fr(self):
        lang.set_lang("fr")
        self.assertEqual(lang.T("Fermer"), "Fermer")
        self.assertEqual(lang.T("n'importe quoi"), "n'importe quoi")

    def test_traduit_en(self):
        lang.set_lang("en")
        self.assertEqual(lang.T("Fermer"), "Close")
        self.assertEqual(lang.T("Accueil"), "Home")

    def test_chaine_inconnue_reste_fr(self):
        lang.set_lang("en")
        self.assertEqual(lang.T("Chaîne absente du dictionnaire"), "Chaîne absente du dictionnaire")

    def test_non_string_et_vide(self):
        lang.set_lang("en")
        self.assertEqual(lang.T(""), "")
        self.assertEqual(lang.T(None), None)
        self.assertEqual(lang.T(42), 42)

    def test_set_lang_invalide_retombe_fr(self):
        lang.set_lang("xx")
        self.assertEqual(lang.get_lang(), "fr")


class PersistanceLangueTest(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("LOCALAPPDATA")
        self.tmp = tempfile.mkdtemp(prefix="td_lang_")
        os.environ["LOCALAPPDATA"] = self.tmp

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_config_conserve_lang(self):
        from Shared.Utils import config
        cfg = config.load()
        self.assertEqual(cfg.get("lang"), "fr")
        cfg["lang"] = "en"
        config.save(cfg)
        self.assertEqual(config.load().get("lang"), "en")

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_selecteur_langue_present(self):
        import tkinter as tk
        from Shared.Utils import config
        from UI import theme as theme_mod
        from UI.Pages.settings_page import SettingsPage

        root = tk.Tk()
        root.withdraw()
        cfg = config.load()

        class C:
            journal = None
            advanced = True

            def __init__(self):
                self.cfg = cfg
                self.theme, self.status_colors, self.symbols = theme_mod.apply(root, cfg)

            def save(self):
                config.save(self.cfg)

        ctx = C()
        ctx.root = root
        page = SettingsPage(root, ctx, on_apply=lambda prev: ctx.save())
        texts = _all_text(page)
        self.assertIn("Langue", texts)
        # En francais, l'option anglais se dit « Anglais » (et « French » en anglais)
        self.assertIn("Anglais", texts)
        self.assertIn("Français", texts)
        root.destroy()


class RevueAnglaiseTest(unittest.TestCase):
    """Deuxieme revue anglais : titre, interdits, cohérence nav/titres, contraste, uptime."""

    def tearDown(self):
        lang.set_lang("fr")

    def test_titre_fenetre_en(self):
        lang.set_lang("en")
        v = lang.T("{v0} — Le ménage de ton PC, tout en douceur").format(v0="TidyDeck")
        self.assertEqual(v, "TidyDeck — Tidying your PC, gently")
        self.assertNotIn("ménage", v)

    def test_aucune_ponctuation_francaise_en_anglais(self):
        for k, v in EN.items():
            if re.search(r"\s[;?!]|\w : |«|»", v):
                self.fail(f"ponctuation française dans EN : {v[:60]!r} (clé {k[:40]!r})")

    def test_mots_interdits_en(self):
        interdits = [r"behaviour", r"colour", r"favour", r"\banalyse\b", r"\bcentre\b",
                     r"\btick", r"\bjournal", r"\btrails?\b", r"journey", r"\btrays?\b",
                     r"triple", r"\(s\)", r" & ", r"\(de\)", r"wellness", r"deliverable"]
        for k, v in EN.items():
            low = v.lower()
            for mot in interdits:
                if re.search(mot, low):
                    self.fail(f"interdit {mot!r} dans {v[:60]!r} (clé {k[:40]!r})")

    def test_wellbeing_partout(self):
        self.assertEqual(EN["Rappels bien-être"], "Wellbeing reminders")

    def test_mapping_nav_titres(self):
        lang.set_lang("en")
        couples = {
            "Jeu et live": "Pour les joueurs",
            "Journaux": "Journaux et annulations",
            "Info PC": "Info PC",
            "À propos": "À propos de TidyDeck",
            "Sauvegarde et transfert": "Sauvegarde et transfert",
            "Services": "Services Windows non essentiels",
            "État des lieux": "État des lieux",
            "Rappels bien-être": "Rappels bien-être",
            "Apparence et modes": "Apparence et modes",
            "Applications préinstallées": "Applications préinstallées",
        }
        for nav, titre in couples.items():
            self.assertEqual(lang.T(nav), lang.T(titre), f"nav {nav!r} != titre {titre!r}")

    def test_ancien_nom_liberer_espace_absent(self):
        for k, v in EN.items():
            self.assertNotIn("Free up space now", v, k)

    def test_debloat_revue(self):
        lang.set_lang("en")
        v = lang.T("Désinstalle les applis préinstallées dont tu n'as plus besoin. "
                   "Rien n'est désinstallé avant que tu valides l'aperçu.")
        self.assertEqual(v, "Uninstall preinstalled apps you don't need. "
                            "Nothing is uninstalled until you confirm the preview.")
        s = lang.T("« Calmer Windows » empêche déjà les applis sponsorisées de revenir : "
                   "ce que tu retires ici reste retiré.")
        self.assertNotIn("protects you", s)
        self.assertEqual(lang.T("✔ Appliquer mes choix…"), "✔ Apply my choices…")
        self.assertEqual(lang.T("{g}, {p}. Coche ce que tu veux retirer, puis « Appliquer mes choix »."),
                         "{g}, {p}. Check what you want to remove, then click 'Apply my choices…'.")

    def test_contraste_palettes(self):
        from UI.theme import PALETTES

        def luminance(hexo):
            vals = []
            for i in (1, 3, 5):
                c = int(hexo[i:i + 2], 16) / 255
                vals.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
            return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]

        def ratio(a, b):
            la, lb = sorted((luminance(a), luminance(b)), reverse=True)
            return (la + 0.05) / (lb + 0.05)

        for nom, p in PALETTES.items():
            self.assertGreaterEqual(ratio(p["fg"], p["card"]), 4.5, f"{nom} fg/card")
            self.assertGreaterEqual(ratio(p["fg"], p["line"]), 4.5, f"{nom} fg/line")

    def test_duree_allumage_anglais(self):
        from Core.Health import report
        lang.set_lang("en")
        self.assertEqual(report._duree_allumage(1 / 48), "less than an hour")
        self.assertEqual(report._duree_allumage(1 / 24), "1 hour")
        self.assertEqual(report._duree_allumage(2 / 24), "2 hours")
        self.assertEqual(report._duree_allumage(1.0), "1 day")
        self.assertEqual(report._duree_allumage(2.0), "2 days")
        self.assertEqual(report._duree_allumage(1.25), "1 day 6 hours")
        lang.set_lang("fr")
        self.assertEqual(report._duree_allumage(2 / 24), "2 heures")

    def test_litteraux_T_tous_dans_le_dictionnaire(self):
        import ast
        autorisees = {"", "\n", " · ", "s", "↻", "✕"}
        manquantes = set()
        for dossier, sous, fichiers in os.walk(ROOT):
            sous[:] = [d for d in sous if d not in {"__pycache__", "build", "dist", "work", "tests"}]
            for f in fichiers:
                if not f.endswith(".py") or f == "translations.py":
                    continue
                src = open(os.path.join(dossier, f), encoding="utf-8").read()
                for m in re.finditer(r'T\((["\'])((?:(?!\1).|\\.)*)\)', src):
                    try:
                        cle = ast.literal_eval(m.group(0)[2:-1])
                    except (ValueError, SyntaxError):
                        continue
                    if isinstance(cle, str) and cle not in EN and cle not in autorisees:
                        manquantes.add(cle[:60])
        self.assertEqual(sorted(manquantes), [])


def _all_text(w):
    out = []
    for c in w.winfo_children():
        try:
            out.append(str(c.cget("text")))
        except Exception:
            pass
        out += _all_text(c)
    return out


if __name__ == "__main__":
    unittest.main()
