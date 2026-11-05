"""Réarmement du minuteur de rendez-vous au démarrage + « Rendez-vous manqué »."""
import unittest

from tests import ROOT  # noqa: F401
from Services.Reminders import scheduler as S


class FakeRoot:
    def __init__(self):
        self.jobs = []

    def after(self, ms, fn):
        self.jobs.append((ms, fn))
        return len(self.jobs)

    def after_cancel(self, j):
        pass


def make(rdv_time="", rdv_at="", warn=15, notif="visual"):
    cfg = {"reminders": {"hydration": {"on": False, "every": 60},
                        "eyes": {"on": False, "every": 20},
                        "stretch": {"on": False, "every": 90},
                        "meals": {"on": False, "lunch": "12:30", "dinner": "19:30",
                                   "snack_am_on": False, "snack_am": "10:30",
                                   "snack_pm_on": False, "snack_pm": "16:00",
                                   "extra_slots": []},
                        "sound": False, "defer": "wait", "auto_detect": False,
                        "dnd_enabled": False},
           "rdv_time": rdv_time, "rdv_at": rdv_at, "rdv_warn_min": warn,
           "rdv_notif": notif, "rdv_volume": 0, "game_mode_on": False}
    seen = []
    ctx = type("C", (), {})()
    ctx.root = FakeRoot()
    ctx.cfg = cfg
    ctx.save = lambda: None
    return S.Scheduler(ctx, lambda k: seen.append(k), lambda k: None), cfg, seen


class RearmTest(unittest.TestCase):
    def test_no_rdv_does_nothing(self):
        sch, cfg, seen = make()
        sch.rearm_rdv()
        self.assertEqual(seen, [])
        self.assertFalse(sch._rdv_active)

    def test_future_rdv_arms(self):
        from datetime import datetime, timedelta
        at = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        sch, cfg, seen = make("03:00", at)
        sch.rearm_rdv()
        self.assertTrue(sch._rdv_active)
        self.assertEqual(cfg["rdv_at"], at)
        self.assertEqual(seen, [])

    def test_past_rdv_within_window_notifies_missed(self):
        from datetime import datetime, timedelta
        past = datetime.now() - timedelta(minutes=40)
        sch, cfg, seen = make(past.strftime("%H:%M"), past.strftime("%Y-%m-%d %H:%M:%S"))
        sch.rearm_rdv()
        self.assertEqual(cfg["rdv_time"], "", "le RDV doit etre efface")
        self.assertEqual(cfg["rdv_at"], "")
        # la notification est differee (after) : on la declenche a la main
        deferred = [fn for ms, fn in sch.ctx.root.jobs if ms >= 1000]
        self.assertTrue(deferred, "la notif doit etre mise en attente, pas envoyee brutalement")
        for fn in deferred:
            fn()
        self.assertEqual(seen, ["rdv_missed"])

    def test_past_rdv_outside_window_is_silent(self):
        from datetime import datetime, timedelta
        far = datetime.now() - timedelta(hours=13)
        sch, cfg, seen = make(far.strftime("%H:%M"), far.strftime("%Y-%m-%d %H:%M:%S"))
        sch.rearm_rdv()
        self.assertEqual(cfg["rdv_time"], "")
        deferred = [fn for ms, fn in sch.ctx.root.jobs if ms >= 1000]
        for fn in deferred:
            fn()
        self.assertEqual(seen, [], "au-dela de la fenetre, pas de notif")

    def test_midnight_crossing_is_not_missed(self):
        """Un RDV a 01:30 pris a 22:45 doit armer pour demain, pas passer pour manque."""
        from datetime import datetime, timedelta
        cross = datetime.now() + timedelta(hours=3)
        sch, cfg, seen = make(cross.strftime("%H:%M"), "")
        sch.rearm_rdv()
        self.assertEqual(cfg["rdv_time"], cross.strftime("%H:%M"))
        self.assertTrue(sch._rdv_active, "ne doit PAS etre considere comme manque")
        self.assertEqual(seen, [])
        self.assertEqual(cfg["rdv_at"],
                         cross.replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S"))

    def test_invalid_time_is_cleared(self):
        for bad in ("25:99", "abc", "12", "", "99:99", "-1:00"):
            sch, cfg, seen = make(bad)
            sch.rearm_rdv()
            self.assertEqual(cfg["rdv_time"], "", f"{bad!r} aurait du etre nettoye")
            self.assertFalse(sch._rdv_active)

    def test_start_calls_rearm(self):
        from datetime import datetime, timedelta
        past = datetime.now() - timedelta(minutes=10)
        sch, cfg, seen = make(past.strftime("%H:%M"), past.strftime("%Y-%m-%d %H:%M:%S"))
        sch._loop = lambda: None  # pas de boucle infinie dans le test
        sch.start()
        self.assertEqual(cfg["rdv_time"], "")
        for ms, fn in sch.ctx.root.jobs:
            if ms >= 1000:
                fn()
        self.assertEqual(seen, ["rdv_missed"])

    def test_alert_window_fires_immediately(self):
        from datetime import datetime, timedelta
        soon = datetime.now() + timedelta(minutes=5)
        sch, cfg, seen = make(soon.strftime("%H:%M"), soon.strftime("%Y-%m-%d %H:%M:%S"), warn=15)
        sch.rearm_rdv()
        self.assertEqual(seen, ["rdv_alert"])
        self.assertEqual(cfg["rdv_time"], "", "RDV consomme apres alerte")

    def test_missed_message_exists_and_is_clear(self):
        title, body, _ = S.MESSAGES["rdv_missed"]
        self.assertIn("manqué", title.lower())
        self.assertGreater(len(body), 20)

    def test_missed_window_is_twelve_hours(self):
        self.assertEqual(S.MISSED_WINDOW_S, 12 * 3600)


if __name__ == "__main__":
    unittest.main()
