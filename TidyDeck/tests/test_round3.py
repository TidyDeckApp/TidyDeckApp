"""Regresions du round 3 : volume daltonien, zone de clic des cases, emplacements
verifiables, compactage Configuration/Rappels, ton Serenite de « A propos »,
repliement PLUS en mode Serenite."""
import json
import os
import shutil
import tempfile
import unittest

import tkinter as tk

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Shared.Utils import lang


def lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(h):
    h = h.lstrip("#")
    return (0.2126 * lin(int(h[0:2], 16)) + 0.7152 * lin(int(h[2:4], 16))
            + 0.0722 * lin(int(h[4:6], 16)))


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Verts utilises hors mode daltonien : aucun ne doit survivre au mode daltonien.
GREENS = {"#2E7D32", "#7BD88F", "#5FBF6B", "#35883B", "#5E8452"}

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


class _AppCase(unittest.TestCase):
    def _make_app(self, **over):
        self.tmp = tempfile.mkdtemp(prefix="td_r3_")
        self._saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp
        cfg = json.loads(json.dumps(BASE_CFG))
        cfg.update(over)
        d = os.path.join(self.tmp, "TidyDeck")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        from UI.app import App
        self.app = App()
        lang.set_lang("fr")
        self.app.root.geometry("1200x750+0+0")
        self.app.root.update()
        self.app.root.update_idletasks()
        return self.app

    def tearDown(self):
        if getattr(self, "app", None) is not None:
            try:
                self.app.root.destroy()
            except Exception:
                pass
            self.app = None
        if getattr(self, "_saved", None) is not None:
            os.environ["LOCALAPPDATA"] = self._saved
        elif hasattr(self, "tmp"):
            os.environ.pop("LOCALAPPDATA", None)
        if getattr(self, "tmp", None):
            shutil.rmtree(self.tmp, ignore_errors=True)
            self.tmp = None


class VolumeDaltonienTest(unittest.TestCase):
    """Fix B : la barre de volume ne doit jamais etre verte en mode daltonien,
    ni en Configuration ni dans Rappels bien-etre (elles lisent la meme jeton)."""

    def setUp(self):
        if not HAS_DISPLAY:
            self.skipTest("pas d'affichage")
        import tkinter as tk
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def _vol(self, theme, cb, serene):
        from UI.theme import apply
        p, status, _ = apply(self.root, {"theme": theme, "colorblind": cb,
                                        "serenity": serene, "text_size": "normale"})
        return p, status

    def test_volume_jamais_vert_en_daltonien(self):
        for theme in ("clair", "sombre", "tdah"):
            for serene in (False, True):
                p, _ = self._vol(theme, True, serene)
                self.assertNotIn(p["volume"].upper(), GREENS,
                               f"volume encore vert ({p['volume']}) theme={theme} serene={serene}")

    def test_volume_contraste_sur_carte(self):
        for theme in ("clair", "sombre", "tdah"):
            for cb in (False, True):
                for serene in (False, True):
                    p, _ = self._vol(theme, cb, serene)
                    r = ratio(p["volume"], p["card"])
                    self.assertGreaterEqual(r, 3.0,
                                          f"volume peu visible theme={theme} cb={cb} serene={serene} : {r:.2f}")

    def test_style_volume_aligne_sur_le_jeton(self):
        from tkinter import ttk
        for theme in ("clair", "sombre", "tdah"):
            p, _ = self._vol(theme, True, False)
            s = ttk.Style(self.root)
            self.assertEqual(s.lookup("Volume.Horizontal.TScale", "background").upper(),
                             p["volume"].upper())

    def test_hors_daltonien_le_vert_est_conserve(self):
        # Non regression : sans daltonisme, les themes gardent leurs teintes habituelles.
        p, _ = self._vol("clair", False, False)
        self.assertEqual(p["volume"], "#2E7D32")


class ZoneClicCaseTest(_AppCase):
    """Fix A : cocher uniquement en cliquant sur le petit carre, jamais sur le texte."""

    @staticmethod
    def _calls(src, needle):
        """Extrait chaque appel multi-ligne commencant par `needle`."""
        out, i = [], 0
        while True:
            j = src.find(needle, i)
            if j < 0:
                return out
            depth, k = 0, j
            while k < len(src):
                if src[k] == "(":
                    depth += 1
                elif src[k] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            out.append(" ".join(src[j:k + 1].split()))
            i = k + 1

    def test_toutes_les_listes_cochees_sont_box_only(self):
        pages = ["startup_page.py", "storage_page.py", "debloat_page.py",
                 "services_page.py", "tweaks_page.py"]
        base = os.path.join(ROOT, "UI", "Pages")
        for pg in pages:
            with open(os.path.join(base, pg), encoding="utf-8") as fh:
                src = fh.read()
            for call in self._calls(src, "Checklist("):
                self.assertIn("box_only=True", call,
                              f"{pg} : Checklist checkable sans box_only=True -> {call[:110]}")

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_clic_sur_texte_ne_coche_pas_demarrage(self):
        from UI.components import Checklist

        class Ctx:
            status_colors = {"ok": "#000000"}
            theme = {"card": "#fff", "line": "#ddd", "fg": "#000", "bg": "#fff"}
            cfg = {"serenity": False}

            @staticmethod
            def mask(t):
                return t
        app = self._make_app(advanced=True)
        lst = Checklist(app.root, Ctx(), ("A", "B"), checkable=True, box_only=True)
        lst.pack()
        lst.set_rows([dict(id="x", name="Un programme", info="état", status="ok",
                          checked=False, detail="d")])
        tree = lst.tree
        tree.identify_row = lambda yy: "x"
        tree.identify_region = lambda x, y: "cell"
        tree.identify_column = lambda x: "#2" if x >= 100 else "#1"
        lst._click(type("E", (), {"x": 500, "y": 4})())
        self.assertFalse(lst.rows["x"]["checked"], "un clic sur le texte a coche la ligne")
        lst._click(type("E", (), {"x": 10, "y": 4})())
        self.assertTrue(lst.rows["x"]["checked"], "un clic sur le carre n'a pas coche la ligne")


class EmplacementVerifiableTest(_AppCase):
    """Fix C : « Ouvrir l'emplacement (pour verifier) » doit etre actif la ou il
    existe un chemin, une page Windows ou un chemin namespace."""

    def test_check_accepte_les_champs_emplacement(self):
        from Shared.Models.models import Check
        c = Check("n", "ok", "d", "a", path="C:/x", settings="gaming",
                  shell="::{645FF040-5081-101B-9F08-00AA002F9451}",
                  reg=("HKCU", "Software"), location="le dossier")
        self.assertEqual(c.path, "C:/x")
        self.assertEqual(c.settings, "gaming")
        self.assertTrue(c.shell)
        self.assertEqual(c.reg, ("HKCU", "Software"))

    def test_check_champs_par_defaut_vides(self):
        from Shared.Models.models import Check
        c = Check("n", "ok", "d")
        self.assertEqual(c.path, "")
        self.assertEqual(c.settings, "")
        self.assertEqual(c.shell, "")
        self.assertEqual(c.reg, ())

    def test_check_rows_transmet_les_champs(self):
        from Shared.Models.models import Check
        from UI.Pages.check_page import check_rows

        class Ctx:
            symbols = {"ok": "●", "warn": "▲", "info": "■", "danger": "⬢", "off": "✕"}
            cfg = {"serenity": False}

            @staticmethod
            def mask(t):
                return t
        rows = check_rows(Ctx(), [Check("a", "ok", "d", "", path="C:/Windows",
                                        settings="gaming", location="Jeux")])
        self.assertEqual(rows[0]["folders"], ["C:/Windows"])
        self.assertEqual(rows[0]["settings"], "gaming")
        self.assertEqual(rows[0]["location"], "Jeux")

    def test_les_controles_jeu_ont_un_emplacement(self):
        from Core.Games import games
        checks = games.run_checks(False)
        with_loc = [c for c in checks if c.path or c.settings or c.shell or c.reg]
        self.assertGreaterEqual(len(with_loc), 5,
                               "les controles « Jeu et live » n'exposent pas d'emplacement verifiable")

    def test_pas_de_controle_applications_arriere_plan(self):
        """Le réglage n'existe plus sous Windows 11 : la ligne doit avoir disparu."""
        from Core.Games import games
        src = open(games.__file__, encoding="utf-8").read()
        self.assertNotIn("Applications en arrière-plan", src)
        self.assertNotIn("GlobalUserDisabled", src)

    def test_gpu_absente_ne_crie_pas_non_pris_en_charge(self):
        """HwSchMode absent du registre = valeur par défaut du pilote, pas
        « non prise en charge » : le message doit rester honnête."""
        from Core.Games import games
        src = open(games.__file__, encoding="utf-8").read()
        self.assertNotIn("Désactivée ou non prise en charge", src)
        self.assertIn("HwSchMode", src)

    def test_rapport_sante_a_un_emplacement_pour_la_corbeille(self):
        from Core.Health import report
        checks = report.run_checks(False)
        corbeille = [c for c in checks if "Corbeille" in c.name]
        self.assertTrue(corbeille)
        self.assertTrue(corbeille[0].shell, "la Corbeille n'a pas de chemin namespace")

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_bouton_actif_quand_emplacement_fourni(self):
        app = self._make_app(advanced=True)
        lst = app.pages["État des lieux"].list
        lst.set_rows([dict(id="a", name="x", info="", status="ok", detail="d",
                          settings="startup")])
        lst.tree.selection_set("a")
        lst._select()
        self.assertTrue(lst.open_btn.instate(["!disabled"]),
                        f"bouton reste grise avec un emplacement : state={lst.open_btn.state()}")

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_bouton_grise_sans_emplacement(self):
        app = self._make_app(advanced=True)
        lst = app.pages["État des lieux"].list
        lst.set_rows([dict(id="a", name="x", info="", status="ok", detail="d")])
        lst.tree.selection_set("a")
        lst._select()
        self.assertFalse(lst.open_btn.instate(["!disabled"]))
        self.assertTrue(lst.open_btn.instate(["disabled"]))

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_libelle_du_boutit_suivre_le_location(self):
        app = self._make_app(advanced=True)
        lst = app.pages["État des lieux"].list
        lst.set_rows([dict(id="a", name="x", info="", status="ok", detail="d",
                          settings="startup", location="Paramètres > Démarrage")])
        lst.tree.selection_set("a")
        lst._select()
        self.assertIn("Paramètres > Démarrage", lst.open_btn.cget("text"))


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
class CompactageTest(_AppCase):
    def _sf(self, page):
        from UI.components import ScrollFrame
        for c in page.winfo_children():
            if isinstance(c, ScrollFrame):
                return c
        self.fail("pas de ScrollFrame")

    def test_configuration_sans_scroll_en_normale_meme_dnd_on(self):
        app = self._make_app(advanced=True, text_size="normale")
        app.goto("Configuration")
        app.root.update()
        sf = self._sf(app.pages["Configuration"])
        app.pages["Configuration"].dnd_var.set(True)
        app.root.update()
        app.root.update_idletasks()
        self.assertLessEqual(sf.inner.winfo_reqheight(), sf.canvas.winfo_height() + 1,
                            "Configuration fait défiler la page quand « Ne pas déranger » est activé")

    def test_repli_dnd_ne_laisse_aucun_trou(self):
        app = self._make_app(advanced=True, text_size="normale")
        app.goto("Configuration")
        app.root.update()
        sf = self._sf(app.pages["Configuration"])
        page = app.pages["Configuration"]
        page.dnd_var.set(True)
        app.root.update()
        app.root.update_idletasks()
        h_on = sf.inner.winfo_reqheight()
        page.dnd_var.set(False)
        app.root.update()
        app.root.update_idletasks()
        h_off = sf.inner.winfo_reqheight()
        self.assertLess(h_off, h_on - 40, "replier « Ne pas déranger » ne rend pas la hauteur")
        self.assertFalse(page._dnd_box.winfo_manager())

    def test_rappels_aucune_ligne_trop_large(self):
        for size in ("normale", "grande"):
            app = self._make_app(advanced=True, text_size=size)
            app.goto("Rappels bien-être")
            app.root.update()
            sf = self._sf(app.pages["Rappels bien-être"])
            avail = sf.canvas.winfo_width()
            for row in sf.inner.winfo_children():
                app.root.update_idletasks()
                self.assertLessEqual(row.winfo_reqwidth(), avail,
                                    f"ligne Rappels trop large en {size} : "
                                    f"{row.winfo_reqwidth()} > {avail}")
            app.root.destroy()
            del self.app


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
class TonSereniteAboutTest(_AppCase):
    def _texts(self, widget, out):
        try:
            if widget.winfo_manager() or isinstance(widget, tk.Frame):
                pass
        except Exception:
            pass
        for c in widget.winfo_children():
            self._texts(c, out)
        try:
            out.append(str(widget.cget("text")))
        except Exception:
            pass

    def test_serenite_conditions_adoucies_et_complet_accessibles(self):
        from UI.Pages.about_page import CONDITIONS_CALM, CONDITIONS_FULL
        app = self._make_app(serenity=True)
        app.goto("À propos")
        app.root.update()
        texts = []
        self._texts(app.pages["À propos"], texts)
        blob = "\n".join(texts)
        self.assertTrue(any(c in blob for c in CONDITIONS_CALM),
                        "le ton adouci n'apparait pas dans « A propos » en mode Serenite")
        self.assertTrue(any(c in blob for c in CONDITIONS_FULL),
                        "le texte juridique complet n'est plus accessible en mode Serenite")

    def test_serenite_aucun_mot_alerte_dans_conditions_calmees(self):
        from UI.Pages.about_page import CONDITIONS_CALM
        harsh = ["Absence de garantie", "définitif. TidyDeck te le signale explicitement",
                 "tu restes responsable", "Ne compte pas dessus"]
        blob = "\n".join(CONDITIONS_CALM)
        for h in harsh:
            self.assertNotIn(h, blob, f"formulation seche encore presente : {h}")

    def test_pas_de_bloc_explicatif_mode_serenite(self):
        # Le bloc « Mode Serenite » a ete retire sur demande : la page « A propos »
        # doit garder le meme contenu dans tous les modes, seule la formulation des
        # conditions change en mode Serenite.
        app = self._make_app(serenity=False)
        app.goto("À propos")
        app.root.update()
        texts = []
        self._texts(app.pages["À propos"], texts)
        blob = "\n".join(texts)
        self.assertNotIn("Mode Sérénité 🌿", blob)
        self.assertNotIn("En mode Sérénité, TidyDeck remplace", blob)

    def test_hors_serenite_conditions_dorigine(self):
        from UI.Pages.about_page import CONDITIONS_FULL
        app = self._make_app(serenity=False)
        app.goto("À propos")
        app.root.update()
        texts = []
        self._texts(app.pages["À propos"], texts)
        blob = "\n".join(texts)
        self.assertTrue(any(c in blob for c in CONDITIONS_FULL))


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
class RepliPLUSSereniteTest(_AppCase):
    def test_repli_plus_garde_focus_et_surbrillance(self):
        app = self._make_app(serenity=True, advanced=True)
        sb = app.sidebar
        plus = sb._sections["PLUS"]
        kids = [n for n in sb._all if sb._parent.get(n) == "PLUS"]
        hdr = plus["header"][0]
        child = sb.nav_items[kids[1]][0]
        app.goto(kids[1])
        app.root.update()
        while not plus["expanded"]:
            sb._toggle_section("PLUS")
        app.root.update()
        child.focus_force()
        app.root.update()
        sb._toggle_section("PLUS")
        app.root.update()
        self.assertIs(app.root.focus_displayof(), hdr,
                     "le focus n'a pas ete rendu a l'en-tete PLUS apres repli")
        self.assertEqual(sb.active, kids[1])
        sb._toggle_section("PLUS")
        app.root.update()
        row, border, lbl, fs = sb.nav_items[kids[1]]
        self.assertEqual(border.cget("bg"), sb.colors["sidebar_accent"])
        self.assertIn("bold", str(lbl.cget("font")))

    def test_repli_plus_ne_deborde_pas(self):
        for size in ("normale", "grande"):
            app = self._make_app(serenity=True, advanced=True, text_size=size)
            sb = app.sidebar
            plus = sb._sections["PLUS"]
            for want in (False, True):
                while plus["expanded"] != want:
                    sb._toggle_section("PLUS")
                app.root.update()
                tot = sum(c.winfo_height() for c in sb.winfo_children() if c.winfo_manager())
                self.assertLessEqual(tot, sb.winfo_height(),
                                    f"sidebar deborde en {size} expanded={want} : {tot}")
            app.root.destroy()
            del self.app


if __name__ == "__main__":
    unittest.main()
