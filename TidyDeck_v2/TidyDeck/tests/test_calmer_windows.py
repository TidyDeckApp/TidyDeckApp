"""Wording « Calmer Windows » : les formulations demandees (pubs / suggestions,
« Applique » au lieu de « Actif ») et le lien avec la page Applis preinstallées."""
import json
import os
import shutil
import tempfile
import unittest
from tkinter import ttk

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Shared.Utils import lang

BASE_CFG = {
    "first_run": False, "theme": "clair", "text_size": "normale", "colorblind": False,
    "advanced": True, "quarantine_days": 7, "serenity": False, "close_action": "minimize",
    "durations": {}, "last_calm": "2026-01-01 00:00:00", "sound": False, "reminder": False,
    "stream_mode": False, "installed": "2026-01-01 00:00:00", "last_reminder": None,
    "toasts_prev": None, "game_mode_on": False, "meals_done": [], "express_mode": False,
    "custom_sound": "", "sound_volume": 70, "rdv_volume": 70, "toast_position": "bottom-right",
    "rdv_time": "", "rdv_at": "", "dnd_enabled": False,
    "reminders": {"hydration": {"on": False, "every": 60},
                  "meals": {"on": False, "lunch": "12:30", "dinner": "19:30",
                             "snack_am_on": False, "snack_am": "10:30",
                             "snack_pm_on": False, "snack_pm": "16:00", "extra_slots": []},
                  "eyes": {"on": False, "every": 20}, "stretch": {"on": False, "every": 90},
                  "defer": "wait", "auto_detect": False, "sound": False, "dnd_enabled": False},
}


class _Case(unittest.TestCase):
    def _env(self, **over):
        tmp = tempfile.mkdtemp(prefix="td_cw_")
        saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = tmp
        cfg = json.loads(json.dumps(BASE_CFG))
        cfg.update(over)
        d = os.path.join(tmp, "TidyDeck")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        return tmp, saved

    def _un(self, tmp, saved):
        if saved is not None:
            os.environ["LOCALAPPDATA"] = saved
        else:
            os.environ.pop("LOCALAPPDATA", None)
        shutil.rmtree(tmp, ignore_errors=True)


class NomsDesReglagesTest(unittest.TestCase):
    EXPECT = {
        "start_ads": "Masquer les pubs et suggestions du menu Démarrer",
        "tips": "Masquer les astuces et notifications « découvrez Windows »",
        "lock_ads": "Masquer les pubs de l'écran de verrouillage",
        "settings_ads": "Masquer les suggestions dans Paramètres",
        "silent_apps": "Empêcher l'installation automatique d'applis sponsorisées",
        "explorer_ads": "Masquer les annonces de l'Explorateur",
        "ad_id": "Désactiver l'identifiant publicitaire",
        "file_ext": "Afficher les extensions de fichiers (.pdf, .exe...)",
    }

    def test_noms_attendus(self):
        from Core.Tweaks import tweaks
        for tid, name in self.EXPECT.items():
            self.assertEqual(tweaks.BY_ID[tid].name, name, tid)

    def test_les_ids_nont_pas_bouge(self):
        # Les ids sont la cle du journal et du registre : ils ne doivent JAMAIS changer.
        from Core.Tweaks import tweaks
        self.assertEqual(set(tweaks.BY_ID), set(self.EXPECT))


class WordingCalmerWindowsTest(_Case):
    def test_colletat_applique_et_pas_actif(self):
        from UI.Pages.tweaks_page import BASE
        self.assertEqual(BASE["active"][0], "✔ Appliqué")
        self.assertEqual(BASE["inactive"][0], "✕ Pas appliqué")
        self.assertEqual(BASE["drift"][0], "⚠ Défait (mise à jour ?)")
        self.assertEqual(BASE["active"][1], "ok")

    def test_sous_titre_allege(self):
        path = os.path.join(ROOT, "UI", "Pages", "tweaks_page.py")
        src = open(path, encoding="utf-8").read()
        self.assertIn("Coche un réglage pour l'appliquer, décoche-le pour revenir comme avant.", src)
        for old in ("Coche = réglage", "contrairement à l'apparence",
                   "Windows est rempli de notifications",
                   "notifications, sons et distractions",
                   "Coupe les pubs et notifications inutiles"):
            self.assertNotIn(old, src, f"ancienne formulation encore presente : {old}")

    def test_bloc_a_quoi_ca_sert(self):
        src = open(os.path.join(ROOT, "UI", "Pages", "tweaks_page.py"), encoding="utf-8").read()
        for frag in ("Windows affiche des pubs, des suggestions et des applis sponsorisées",
                    "Cette page les coupe, une par une :",
                    "Moins de pubs dans le menu Démarrer, l'écran de verrouillage et Paramètres.",
                    "Plus d'applis sponsorisées installées toutes seules"):
            self.assertIn(frag, src)

    def test_message_rien_a_changer(self):
        src = open(os.path.join(ROOT, "UI", "Pages", "tweaks_page.py"), encoding="utf-8").read()
        self.assertIn("Coche un réglage « Pas appliqué » pour l'appliquer, ou décoche un réglage « Appliqué »", src)
        self.assertNotIn("pour l'activer, ou décoche un réglage « Actif »", src)

    def test_phrase_serenite(self):
        src = open(os.path.join(ROOT, "UI", "Pages", "tweaks_page.py"), encoding="utf-8").read()
        self.assertIn("Coupe les pubs et les suggestions de Windows en une seule fois.", src)
        self.assertIn("Une seule confirmation, un point de restauration, et tout reste annulable.", src)

    def test_sous_titre_serenite(self):
        src = open(os.path.join(ROOT, "UI", "Pages", "tweaks_page.py"), encoding="utf-8").read()
        self.assertIn("Le calme en un clic. Rien ne change sans ton accord.", src)
        self.assertNotIn("Rien ne change sans ton accord, et tout est annulable", src)

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_le_texte_sous_le_bouton_reste_dans_le_bloc(self):
        # Sans wraplength ce libelle rendait une ligne de 1164 px pour ~854
        # disponibles en « Grande » : un tiers de la phrase etait invisible.
        tmp, saved = self._env(serenity=True)
        try:
            from UI.app import App
            for ts in ("normale", "grande"):
                app = App()
                lang.set_lang("fr")
                try:
                    app.root.geometry("1200x750+0+0")
                    app.goto("Calmer Windows")
                    app.root.update()
                    app.root.update_idletasks()
                    page = app.pages["Calmer Windows"]
                    lbl = [c for c in page.serene_box.winfo_children()
                          if isinstance(c, ttk.Label) and "Coupe" in str(c.cget("text"))]
                    self.assertTrue(lbl, "libelle sous le bouton introuvable")
                    lbl = lbl[0]
                    avail = app.content.winfo_width() - 32
                    self.assertLessEqual(lbl.winfo_reqwidth(), avail,
                                       f"texte rogne en {ts} : {lbl.winfo_reqwidth()} > {avail}")
                    self.assertGreater(int(str(lbl.cget("wraplength")) or 0), 0,
                                     "pas de wraplength : le texte ne peut pas passer a la ligne")
                    self.assertLessEqual(page.winfo_reqheight(), 750,
                                       f"page trop grande en {ts} : {page.winfo_reqheight()}")
                finally:
                    try:
                        app.root.destroy()
                    except Exception:
                        pass
        finally:
            self._un(tmp, saved)


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
class LienDebloatCalmerWindowsTest(_Case):
    def _note(self, page):
        return str(page.silent_lbl.cget("text"))

    def test_note_presente_et_coherente(self):
        tmp, saved = self._env(advanced=True)
        try:
            from UI.app import App
            from Core.Tweaks import tweaks
            app = App()
            lang.set_lang("fr")
            try:
                app.goto("Applications préinstallées")
                app.root.update()
                page = app.pages["Applications préinstallées"]
                page._refresh_silent_note()
                note = self._note(page)
                done = tweaks.is_active(tweaks.BY_ID["silent_apps"])
                if done:
                    self.assertIn("Déjà fait : Windows n'installera plus automatiquement ces applications partenaires", note)
                else:
                    self.assertIn("Avant de retirer des applis, active", note)
                    self.assertIn("« Empêcher l'installation automatique d'applis sponsorisées »", note)
                    self.assertIn("dans Calmer Windows", note)
                self.assertTrue(note.strip(), "la note est vide")
            finally:
                try:
                    app.root.destroy()
                except Exception:
                    pass
        finally:
            self._un(tmp, saved)

    def test_la_note_se_met_a_jour_apres_un_changement_de_reglage(self):
        tmp, saved = self._env(advanced=True)
        try:
            from UI.app import App
            app = App()
            lang.set_lang("fr")
            try:
                app.goto("Applications préinstallées")
                app.root.update()
                page = app.pages["Applications préinstallées"]
                page._refresh_silent_note()
                before = self._note(page)
                page._refresh_silent_note()
                self.assertEqual(before, self._note(page))
            finally:
                try:
                    app.root.destroy()
                except Exception:
                    pass
        finally:
            self._un(tmp, saved)


if __name__ == "__main__":
    unittest.main()
