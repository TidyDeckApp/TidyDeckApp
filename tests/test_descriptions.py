# -*- coding: utf-8 -*-
"""Contrôle complet des descriptions : Démarrage (_hint par mots entiers),
Services et Applications préinstallées — clés EN exactes, aucun mode qui
contredit le niveau, radios ●/○ à indicateur unique, analyse sans coche auto.
"""
import os
import shutil
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Core.Startup.startup import HINTS, UNKNOWN, _hint
from Shared.Utils.translations import EN


def _clean(cmd):
    return cmd


class CasReelsTest(unittest.TestCase):
    """Table de cas réels : (nom de l'entrée, commande, sous-chaîne attendue)."""

    CAS = [
        ("Elgato Stream Deck", r'"C:\Program Files\Elgato\StreamDeck\StreamDeck.exe"', "Elgato Stream Deck"),
        ("Stream Deck", r"C:\AMD\tools\streamdeck.exe", "Elgato Stream Deck"),
        ("Volume Controller SD plugin", r"C:\Plugins\SDVolumeController.exe", UNKNOWN),
        ("Voicemod", r'"C:\Program Files\Voicemod\Voicemod.App.exe"', "Voicemod"),
        ("Mullvad VPN", r'"C:\Program Files\Mullvad VPN\mullvad-vpn.exe"', "Mullvad VPN"),
        ("Windscribe", r'"C:\Program Files\Windscribe\Windscribe.exe"', "Windscribe VPN"),
        ("Riot Client", r'"C:\Riot Games\Riot Client\RiotClientServices.exe"', "Riot Client"),
        ("Riot Vanguard", r'"C:\Riot Games\Riot Vanguard\vgc.exe"', "anti-triche"),
        ("vgtray", r"C:\Riot Games\Vanguard\vgtray.exe", "anti-triche"),
        ("RtkAudUService", r"C:\Windows\System32\RtkAudUService64.exe", "Realtek"),
        ("SecurityHealth", r"C:\Windows\System32\SecurityHealthSystray.exe", "Sécurité Windows"),
        ("OneDrive", r'"C:\Users\x\OneDrive\OneDrive.exe" /background', "cloud Microsoft"),
        ("Discord", r'"C:\Users\x\AppData\Local\Discord\Update.exe" --processStart Discord.exe', "Discord"),
        ("Spotify", r'"C:\Users\x\AppData\Roaming\Spotify\Spotify.exe" -minimized', "Spotify"),
        ("Steam", r'"C:\Program Files (x86)\Steam\steam.exe" -silent', "Steam"),
        ("Radmin VPN", r'"C:\Program Files\Radmin VPN\rvpn.exe"', "Client VPN"),
        ("Motorola Device Manager", r'"C:\Program Files\Motorola\MotoSwitchService.exe"', "Motorola"),
        ("PhpStorm 2025.2", r'"C:\Program Files\JetBrains\phpstorm64.exe"', "PhpStorm"),
    ]

    def test_table_cas_reels(self):
        for nom, cmd, attendu in self.CAS:
            texte, niveau = _hint(nom, cmd)
            self.assertIn(attendu, texte, f"{nom} -> {texte[:60]}")

    def test_chemin_et_arguments_jamais_utilises(self):
        # « amd » n'est qu'un dossier du chemin : aucune règle ne doit partir de là.
        texte, niveau = _hint("Zorgbillon", r"C:\games\amd\launcher.exe --runinbk --tor")
        self.assertEqual(texte, UNKNOWN)
        self.assertEqual(niveau, "unknown")

    def test_dans_le_doute_non_reconnu(self):
        texte, niveau = _hint("TrucMuche", r"C:\Users\x\AppData\Local\Truc\trucmuch.exe")
        self.assertEqual(texte, UNKNOWN)
        self.assertEqual(niveau, "unknown")


class ProprieteMotsEntiersTest(unittest.TestCase):
    """Propriété générale : une clé collée au milieu d'un autre mot (streamdeck
    pour « amd », motorola pour « tor ») ne déclenche JAMAIS la règle."""

    def test_cle_encastree_ne_declenche_pas(self):
        for cle, texte, niveau in HINTS:
            if len(cle.split()) != 1:
                continue
            leurre = "zq" + cle + "qz"
            trouve, _ = _hint(leurre, leurre + ".exe")
            self.assertNotEqual(trouve, texte,
                                f"la clé « {cle} » matche à l'intérieur de « {leurre} »")

    def test_cle_courte_jamais_en_sous_chaine(self):
        for cle, texte, niveau in HINTS:
            if len(cle) > 3 or len(cle.split()) != 1:
                continue
            leurre = "x" + cle + "x"
            trouve, _ = _hint(leurre, "")
            self.assertNotEqual(trouve, texte, f"clé courte « {cle} » en sous-chaîne")

    def test_doublons_de_cles_supprimes(self):
        vus = {}
        for cle, texte, niveau in HINTS:
            self.assertNotIn(cle.lower(), vus, f"clé en double : {cle}")
            vus[cle.lower()] = texte

    def test_riot_vanguard_separe_de_riot_client(self):
        t1, n1 = _hint("Riot Vanguard", r"C:\Riot Games\Riot Vanguard\vgc.exe")
        t2, n2 = _hint("RiotClientServices", r"C:\Riot Games\Riot Client\RiotClientServices.exe")
        self.assertIn("anti-triche", t1)
        self.assertEqual(n1, "keep")
        self.assertIn("lanceur", t2)
        self.assertEqual(n2, "safe")
        self.assertNotEqual(t1, t2)


class DescriptionSurediteTest(unittest.TestCase):
    """Chaque description a SA clé exacte en EN ; le niveau colle au texte."""

    def test_hints_tous_ont_cle_en(self):
        manques = [t[:60] for c, t, l in HINTS if t not in EN]
        self.assertEqual(manques, [])
        self.assertIn(UNKNOWN, EN)

    def test_services_tous_ont_cle_en(self):
        from Core.Health.services import SERVICES
        manques = [(s["id"], c) for s in SERVICES for c in ("name", "what", "risk") if s[c] not in EN]
        self.assertEqual(manques, [])

    def test_debloat_labels_ont_cle_en(self):
        from Core.Debloat.debloat import KNOWN
        manques = [lab for lab, pk in KNOWN if lab not in EN]
        self.assertEqual(manques, [])

    def test_niveau_coherent_avec_le_texte(self):
        for cle, texte, niveau in HINTS:
            if "À GARDER" in texte or "À garder" in texte:
                self.assertIn(niveau, ("keep", "maybe"),
                              f"« {cle} » dit « à garder » mais niveau {niveau}")
            if "Vital" in texte or "critique" in texte:
                self.assertEqual(niveau, "keep", f"« {cle} »")

    def test_debloat_labels_packed_prefixes_coherents(self):
        from Core.Debloat.debloat import KNOWN
        for lab, pkgs in KNOWN:
            for p in pkgs:
                self.assertTrue(p.lower().startswith(("microsoft.", "clipchamp.")),
                                f"{lab} -> {p}")


class RadioIndicateurUniqueTest(unittest.TestCase):
    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_un_seul_rond_et_gras_daltonien(self):
        import tkinter as tk
        from tkinter import ttk
        from UI import theme
        from UI.components import RadiOpt
        root = tk.Tk()
        root.withdraw()
        try:
            cfg = {"theme": "clair", "colorblind": False, "serenity": False,
                   "text_size": "normale", "stream_mode": False, "advanced": False}
            theme.apply(root, cfg)
            layout_txt = str(ttk.Style(root).layout("Opt.TRadiobutton"))
            self.assertNotIn("Radiobutton.indicator", layout_txt)
            var = tk.StringVar(value="b")
            rb1 = RadiOpt(root, text="Alpha", variable=var, value="a")
            rb2 = RadiOpt(root, text="Beta", variable=var, value="b")
            self.assertEqual(rb1.cget("text"), "○ Alpha")
            self.assertEqual(rb2.cget("text"), "● Beta")
            self.assertNotIn("◉", rb1.cget("text") + rb2.cget("text"))
            var.set("a")
            self.assertEqual(rb1.cget("text"), "● Alpha")
            self.assertEqual(str(rb1.cget("style")), "Opt.TRadiobutton")
            # mode daltonien : rebuild -> l'option choisie passe en gras (style dédié)
            cfg["colorblind"] = True
            theme.apply(root, cfg)
            st = ttk.Style(root)
            self.assertIn("bold", str(st.lookup("OptB.TRadiobutton", "font")))
            rb3 = RadiOpt(root, text="Gamma", variable=var, value="a")
            rb4 = RadiOpt(root, text="Delta", variable=var, value="b")
            self.assertEqual(str(rb3.cget("style")), "OptB.TRadiobutton")
            self.assertEqual(str(rb4.cget("style")), "Opt.TRadiobutton")
        finally:
            root.destroy()


class AnalyseSansCocheTest(unittest.TestCase):
    """Après « Analyser mon PC » : rien n'est coché tout seul, le bouton reste
    désactivé, et la phrase guide vers la coche manuelle ou « Tout cocher »."""

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_selection_vide_apres_analyse(self):
        import tkinter as tk
        self._saved = os.environ.get("LOCALAPPDATA")
        self.tmp = tempfile.mkdtemp(prefix="td_ana_")
        os.environ["LOCALAPPDATA"] = self.tmp
        try:
            from Shared.Utils import config
            from Shared.Utils import lang
            from UI.app import App
            lang.set_lang("fr")
            app = App()
            app.root.update()
            page = app.pages["Nettoyage"]
            self.assertTrue(page.items, "catalogue simple vide ?")

            class FauxR:
                def __init__(self, item):
                    self.item = item
                    self.size = 500_000
                    self.count = 3
                    self.blocked = ""

            res = {i.id: FauxR(i) for i in page.items}
            page._analysed(res, None)
            self.assertEqual(page.checked_ids(), [],
                             "l'analyse a coché des catégories toute seule")
            self.assertFalse(page.clean_btn.instate(["!disabled"]),
                             "« Nettoyer la sélection » doit rester désactivé")
            self.assertIn("Coche ce que tu veux ranger", page.status.cget("text"))
            self.assertIn("Tout cocher (Recommandé)", page.status.cget("text"))
            # « Tout cocher » (bouton, lui) coche bien ensuite, et débloque le bouton
            page._apply_preset("safe")
            self.assertTrue(page.checked_ids())
            self.assertTrue(page.clean_btn.instate(["!disabled"]))
            app.root.destroy()
        finally:
            if self._saved is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = self._saved
            shutil.rmtree(self.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
