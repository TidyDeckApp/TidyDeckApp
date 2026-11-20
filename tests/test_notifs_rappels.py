"""Rappels bien-être : choix « Visuel / Son » propre à chaque rappel.

Migration de l'ancien carillon global, valeurs par défaut, lecture du choix
par le moteur de rappel, et vérification que le mode Jeu bloque toujours
tout, quel que soit le choix.
"""
import json
import os
import shutil
import tempfile
import time
import unittest

from Shared.Utils import config
from Shared.Utils.config import DEFAULTS
from Services.Reminders.scheduler import Scheduler, notif_for
from Services.Reminders.notif_ui_logic import banner_utile, apply_visible

try:
    import tkinter  # noqa: F401
    _TK = True
except Exception:
    _TK = False

BASE_R = {"hydration": {"on": True, "every": 60},
          "meals": {"on": True, "lunch": "12:30", "dinner": "19:30",
                    "snack_am_on": True, "snack_am": "10:30",
                    "snack_pm_on": False, "snack_pm": "16:00",
                    "extra_slots": [{"id": "custom_0", "name": "Café", "time": "15:00", "on": True}]},
          "eyes": {"on": False, "every": 20},
          "stretch": {"on": False, "every": 90},
          "defer": "wait", "auto_detect": False, "dnd_enabled": False}


class ConfigSandbox(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("LOCALAPPDATA")
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "TidyDeck"))
        os.environ["LOCALAPPDATA"] = self.tmp

    def tearDown(self):
        if self._old is not None:
            os.environ["LOCALAPPDATA"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, cfg):
        with open(os.path.join(self.tmp, "TidyDeck", "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)


class DefautsTest(ConfigSandbox):
    def test_cles_notif_par_defaut(self):
        for k in ("hydration", "eyes", "stretch"):
            self.assertEqual(DEFAULTS["reminders"][k]["notif"], "visual")
        m = DEFAULTS["reminders"]["meals"]
        for k in ("notif", "snack_am_notif", "snack_pm_notif"):
            self.assertEqual(m[k], "visual")

    def test_config_neuve_notif_visual_partout(self):
        self.write({})
        cfg = config.load()
        self.assertEqual(cfg["reminders"]["hydration"]["notif"], "visual")
        self.assertEqual(cfg["reminders"]["meals"]["notif"], "visual")
        self.assertEqual(cfg["reminders"]["stretch"]["notif"], "visual")


class MigrationTest(ConfigSandbox):
    def test_ancien_carillon_global_devient_visuel_et_son(self):
        r = json.loads(json.dumps(BASE_R))
        r["sound"] = True
        self.write({"reminders": r})
        rr = config.load()["reminders"]
        for k in ("hydration", "meals", "eyes", "stretch"):
            self.assertEqual(rr[k]["notif"], "both", k)
        self.assertEqual(rr["meals"]["snack_am_notif"], "both")
        self.assertEqual(rr["meals"]["snack_pm_notif"], "both")
        self.assertEqual(rr["meals"]["extra_slots"][0]["notif"], "both")

    def test_sans_carillon_global_reste_visual(self):
        r = json.loads(json.dumps(BASE_R))
        r["sound"] = False
        self.write({"reminders": r})
        rr = config.load()["reminders"]
        self.assertEqual(rr["hydration"]["notif"], "visual")
        self.assertEqual(rr["meals"]["notif"], "visual")

    def test_notif_deja_reglee_ne_change_pas(self):
        r = json.loads(json.dumps(BASE_R))
        r["sound"] = True
        r["hydration"]["notif"] = "sound"
        self.write({"reminders": r})
        rr = config.load()["reminders"]
        self.assertEqual(rr["hydration"]["notif"], "sound")
        self.assertEqual(rr["eyes"]["notif"], "both")


class NotifForTest(unittest.TestCase):
    def setUp(self):
        r = json.loads(json.dumps(BASE_R))
        r["hydration"]["notif"] = "sound"
        r["meals"]["notif"] = "both"
        r["meals"]["snack_am_notif"] = "none"
        self.c = {"reminders": r}

    def test_chaque_type_de_rappel_a_son_choix(self):
        self.assertEqual(notif_for(self.c, "hydration"), "sound")
        self.assertEqual(notif_for(self.c, "meal_lunch"), "both")
        self.assertEqual(notif_for(self.c, "meal_dinner"), "both")
        self.assertEqual(notif_for(self.c, "meal_snack_am"), "none")
        self.assertEqual(notif_for(self.c, "meal_snack_pm"), "visual")
        self.assertEqual(notif_for(self.c, "meal_custom_0"), "visual")
        self.assertEqual(notif_for(self.c, "rdv_alert"), "visual")


class ModeJeuBloqueTest(unittest.TestCase):
    """Quel que soit le choix Visuel/Son, mode Jeu = rien ne passe."""

    def test_game_mode_ne_notifie_rien(self):
        calls = []
        ctx = type("Ctx", (), {"cfg": {"game_mode_on": True, "reminders": BASE_R, "meals_done": []}})()
        sch = Scheduler(ctx, calls.append, lambda k: None)
        sch._queue("hydration")
        sch.tick(now=time.time() + 10)
        self.assertEqual(calls, [], "le mode Jeu doit bloquer toute notification")
        self.assertIn("hydration", sch.pending, "le rappel attend la fin de partie")


class _Var:
    """Faux tk.BooleanVar pour tester la logique de save sans fenêtre Tk."""

    def __init__(self, val):
        self._v = val

    def get(self):
        return self._v

    def set(self, v):
        self._v = v


def _page_serene(serene, notif_hydr):
    """Page Rappels de fortune (sans Tk) : seul le chemin save() est exercé."""
    from unittest import mock
    from UI.Pages import reminders_page as rp
    cur = notif_hydr
    vis = _Var(cur in ("visual", "both"))
    snd = _Var(cur in ("sound", "both"))
    r = {"hydration": {"on": True, "every": 60, "notif": cur},
         "meals": {"on": False, "lunch": "12:30", "dinner": "19:30",
                   "snack_am_on": False, "snack_am": "10:30",
                   "snack_pm_on": False, "snack_pm": "16:00", "extra_slots": []},
         "eyes": {"on": False, "every": 20}, "stretch": {"on": False, "every": 90}}
    p = rp.RemindersPage.__new__(rp.RemindersPage)
    p.ctx = mock.Mock()
    p.ctx.cfg = {"reminders": r, "serenity": serene}
    p._extra_frames = []
    p._notif_targets = [(vis, snd, r["hydration"], "notif")]
    p.v = {"hydration.on": _Var(True), "meals.on": _Var(False),
           "eyes.on": _Var(False), "stretch.on": _Var(False),
           "hydration.every": _Var("60"), "eyes.every": _Var("20"),
           "stretch.every": _Var("90"), "meals.lunch": _Var("12:30"),
           "meals.dinner": _Var("19:30"), "meals.snack_am": _Var("10:30"),
           "meals.snack_pm": _Var("16:00"), "meals.snack_am_on": _Var(False),
           "meals.snack_pm_on": _Var(False)}
    p.toast_pos = _Var("bottom-right")
    p.rdv_visual = _Var(False)
    p.rdv_sound = _Var(False)
    p.say = lambda msg: None
    return p, r, vis, snd


@unittest.skipUnless(_TK, "tkinter requis")
class SereniteJamaisEcraseTest(unittest.TestCase):
    """Sérénité ne modifie jamais un choix enregistré ; seul un muet complet
    (ni visuel ni son) retombe sur « visual »."""

    def test_sound_enregistre_reste_sound_apres_save_en_serenite(self):
        p, r, vis, snd = _page_serene(serene=True, notif_hydr="sound")
        p.save(silent=True)
        self.assertEqual(r["hydration"]["notif"], "sound")

    def test_son_decoche_en_serenite_retombe_sur_visual(self):
        p, r, vis, snd = _page_serene(serene=True, notif_hydr="sound")
        snd.set(False)
        p.save(silent=True)
        self.assertEqual(r["hydration"]["notif"], "visual")

    def test_normal_muet_complet_reste_none(self):
        p, r, vis, snd = _page_serene(serene=False, notif_hydr="sound")
        snd.set(False)
        p.save(silent=True)
        self.assertEqual(r["hydration"]["notif"], "none")


class BandeauUtileTest(unittest.TestCase):
    def test_snack_seul_affiche_le_bandeau(self):
        self.assertTrue(banner_utile({"meals": {"snack_am_on": True}}))
        self.assertTrue(banner_utile({"meals": {"snack_pm_on": True}}))

    def test_rien_dactive_pas_de_bandeau(self):
        self.assertFalse(banner_utile({"meals": {"extra_slots": [{"on": False}]}}))
        self.assertFalse(banner_utile({}))

    def test_rdv_actif_affiche_le_bandeau(self):
        self.assertTrue(banner_utile({}, rdv_actif=True))

    def test_creneau_perso_seul_affiche_le_bandeau(self):
        self.assertTrue(banner_utile({"meals": {"extra_slots": [{"on": True}]}}))


class LienAppliquerTest(unittest.TestCase):
    def test_visible_seuil_deux_actifs(self):
        self.assertTrue(apply_visible([True, True]))
        self.assertTrue(apply_visible([False, True, True]))
        self.assertFalse(apply_visible([True, False]))
        self.assertFalse(apply_visible([]))


def _apply_page(serene=False):
    from unittest import mock
    from UI.Pages import reminders_page as rp
    p = rp.RemindersPage.__new__(rp.RemindersPage)
    p.ctx = mock.Mock()
    p.ctx.cfg = {"serenity": serene}
    p.say = lambda msg: None
    said = []
    p.say = said.append
    p._pairs = [{"vis": _Var(True), "snd": _Var(False), "on": _Var(False)},   # hydratation, désactivée
                {"vis": _Var(True), "snd": _Var(True), "on": _Var(True)},     # repas activé = source
                {"vis": _Var(False), "snd": _Var(False), "on": _Var(True)}]   # créneau personnalisé activé
    return p, p._pairs, said


@unittest.skipUnless(_TK, "tkinter requis")
class AppliquerTousTest(unittest.TestCase):
    def test_copie_depuis_le_premier_active_inclus_les_creneaux(self):
        p, pairs, said = _apply_page()
        p._apply_all_notif()
        for i in (0, 2):
            self.assertTrue(pairs[i]["snd"].get(), i)
            self.assertTrue(pairs[i]["vis"].get(), i)
        self.assertTrue(any("Appliqué à tous les rappels" in s for s in said))

    def test_sans_rappel_active_ne_copie_rien(self):
        p, pairs, said = _apply_page()
        for q in pairs:
            q["on"].set(False)
        p._apply_all_notif()
        self.assertFalse(pairs[2]["snd"].get())
        self.assertEqual(said, [])

    def test_serenite_copie_seulement_le_son(self):
        p, pairs, said = _apply_page(serene=True)
        p._apply_all_notif()
        self.assertTrue(pairs[2]["snd"].get())
        self.assertFalse(pairs[2]["vis"].get(), "en Sérénité, Visuel reste tel quel")


def _sch_avec_page():
    """Scheduler de fortune dont ctx.app.pages contient une fausse page ouverte."""
    from unittest import mock
    page = mock.Mock()
    ctx = mock.Mock()
    ctx.cfg = {"rdv_time": "10:00", "rdv_at": "2026-11-16 10:00:00"}
    ctx.app.pages = {"Rappels bien-être": page}
    sch = Scheduler(ctx, mock.Mock(), mock.Mock())
    sch._rdv_active = True
    return sch, ctx, page


class BandeauRdvEteintTest(unittest.TestCase):
    """Quand le minuteur RDV s'éteint (manuellement, à l'alerte, ou RDV passé),
    la page Rappels ouverte doit rafraîchir son bandeau ; fermée, rien ne casse."""

    def test_alerte_rdv_rafrachit_la_page_ouverte(self):
        sch, ctx, page = _sch_avec_page()
        sch._rdv_notif = "none"  # même sans notification, le minuteur s'est éteint
        sch._fire_rdv("10:00", 5)
        page._refresh_banner.assert_called_once()
        self.assertEqual(ctx.cfg["rdv_time"], "")

    def test_rdv_manque_rafrachit_la_page_ouverte(self):
        sch, ctx, page = _sch_avec_page()
        sch._rdv_notif = "none"
        sch._missed_rdv("10:00")
        page._refresh_banner.assert_called_once()

    def test_page_non_ouverte_ne_casse_rien(self):
        sch, ctx, page = _sch_avec_page()
        ctx.app.pages = {}  # la page n'a jamais été construite
        sch._rdv_notif = "none"
        sch._missed_rdv("10:00")  # ne doit lever aucune exception

    @unittest.skipUnless(_TK, "tkinter requis")
    def test_cancel_rdv_cote_page_rafrachit_le_bandeau(self):
        from unittest import mock
        from UI.Pages import reminders_page as rp
        p = rp.RemindersPage.__new__(rp.RemindersPage)
        p.ctx = mock.Mock()
        p.ctx.cfg = {"rdv_time": "10:00", "rdv_at": "2026-11-16 10:00:00"}
        p.rdv_status = mock.Mock()
        p._refresh_banner = mock.Mock()
        p._cancel_rdv()
        p.ctx.app.scheduler.cancel_rdv.assert_called_once()
        p._refresh_banner.assert_called_once()
