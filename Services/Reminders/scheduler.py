"""Rappels bien-être (hydratation, repas, 20-20-20, étirements) avec « Ne pas déranger pendant un jeu ».

Tout est local : un minuteur Tk léger (1 vérification toutes les 15 s, coût négligeable pour les FPS)."""
import time
from datetime import datetime, timedelta
from Shared.Utils import winui
from Shared.Utils.lang import T

INTERVAL_KINDS = ("hydration", "eyes", "stretch")
CHECK_EVERY_MS = 15000

MESSAGES = {
    "hydration": ("💧 Un verre d'eau ?", "Ton corps te dira merci. Prends quelques gorgées.", 0),
    "meal_lunch": ("🍽 C'est l'heure du déjeuner", "Une vraie pause fait du bien à la concentration.", 0),
    "meal_dinner": ("🍽 C'est l'heure du dîner", "Pause repas (ou petit snack) : tu l'as mérité.", 0),
    "meal_snack_am": ("🍎 Pause snack du matin", "Un petit encas pour tenir jusqu'au déjeuner.", 0),
    "meal_snack_pm": ("🍪 Pause snack de l'après-midi", "Recharge-toi avec un snack avant la fin de journée.", 0),
    "eyes": ("👀 Pause visuelle 20-20-20", "Regarde quelque chose à environ 6 mètres, pendant 20 secondes.", 20),
    "stretch": ("🧘 Debout, on bouge !", "Étire-toi, marche un peu, roule des épaules : 1 minute suffit.", 0),
    "rdv_alert": ("⏰ Rendez-vous bientôt !", "Prépare-toi à arrêter : ton rendez-vous approche. Tu peux finir ta partie tranquillement.", 0),
    "rdv_missed": ("⏰ Rendez-vous manqué", "L'heure que tu avais réglée est passée pendant que TidyDeck était fermé. Rien n'a pu t'avertir : vérifie si tu dois encore y aller.", 0),
}

MISSED_WINDOW_S = 12 * 3600


class Scheduler:
    def __init__(self, ctx, notify, flash):
        self.ctx, self.notify, self.flash = ctx, notify, flash
        self.next, self.pending = {}, []
        self._job = None
        self._rdv_job = None
        self._rdv_active = False

    def set_rdv(self, target, warn_min, notif_type):
        """target : datetime du rendez-vous (pas juste HH:MM, sinon un RDV apres minuit
        serait pris pour un RDV deja passe)."""
        self.cancel_rdv()
        self._rdv_active = True
        self._rdv_notif = notif_type
        self._check_rdv(target, warn_min)

    def cancel_rdv(self):
        self._rdv_active = False
        if self._rdv_job:
            self.ctx.root.after_cancel(self._rdv_job)
            self._rdv_job = None

    def _check_rdv(self, target, warn_min):
        if not self._rdv_active:
            return
        try:
            now = datetime.now()
            diff_min = (target - now).total_seconds() / 60
            if 0 < diff_min <= warn_min:
                self._fire_rdv(target.strftime("%H:%M"), int(diff_min))
                return
            elif diff_min > warn_min:
                delay = int((diff_min - warn_min) * 60 * 1000)
                self._rdv_job = self.ctx.root.after(delay, lambda: self._check_rdv(target, warn_min))
            else:
                self._missed_rdv(target.strftime("%H:%M"))
        except Exception:
            from Shared.Utils import depannage
            depannage.noter("Services/Reminders/scheduler.py:63")

    def _fire_rdv(self, rdv_time, mins_left):
        if not self._rdv_active:
            return
        msg = T("⏰ Attention : rendez-vous dans {v0} min ({v1}) !").format(v0=mins_left, v1=rdv_time)
        notif = getattr(self, '_rdv_notif', 'both')
        if notif in ('visual', 'both'):
            self.notify("rdv_alert")
        if notif in ('sound', 'both'):
            from Shared.Utils import sound
            try:
                v = float(self.ctx.cfg.get("rdv_volume", 70)) / 100.0
            except (TypeError, ValueError):
                v = 0.7
            sound.chime(v)
        self.ctx.cfg["rdv_time"] = ""
        self.ctx.cfg["rdv_at"] = ""
        self.ctx.save()
        self._rdv_active = False

    def _missed_rdv(self, rdv_time):
        if not self._rdv_active:
            return
        self._rdv_active = False
        self.ctx.cfg["rdv_time"] = ""
        self.ctx.save()
        notif = getattr(self, "_rdv_notif", "both")
        if notif in ("visual", "both"):
            self.notify("rdv_missed")
        if notif in ("sound", "both"):
            from Shared.Utils import sound
            try:
                v = float(self.ctx.cfg.get("rdv_volume", 70)) / 100.0
            except (TypeError, ValueError):
                v = 0.7
            sound.chime(v)

    @property
    def cfg(self):
        return self.ctx.cfg["reminders"]

    @property
    def meals_done(self):
        return set(tuple(x) for x in self.ctx.cfg.get("meals_done", []))

    @meals_done.setter
    def meals_done(self, val):
        self.ctx.cfg["meals_done"] = [list(x) for x in val]

    def start(self):
        self.reschedule()
        self.rearm_rdv()
        self._loop()

    def rearm_rdv(self):
        """Au démarrage, le minuteur RDV n'existe plus : on le rearme depuis la config.
        Si l'heure est deja passee, on le dit une seule fois puis on efface."""
        now = datetime.now()
        at = (self.ctx.cfg.get("rdv_at") or "").strip()
        t = (self.ctx.cfg.get("rdv_time") or "").strip()
        target = None
        if at:
            try:
                target = datetime.strptime(at, T("%Y-%m-%d %H:%M:%S"))
            except ValueError:
                target = None
        if target is None:
            if not t:
                return
            try:
                hh, mm = (int(x) for x in t.split(":"))
                if not (0 <= hh < 24 and 0 <= mm < 60):
                    raise ValueError("heure hors bornes")
            except (ValueError, TypeError):
                self.ctx.cfg["rdv_time"] = ""
                self.ctx.cfg["rdv_at"] = ""
                return
            cand = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            target = cand if cand > now else cand + timedelta(days=1)
            self.ctx.cfg["rdv_at"] = target.strftime(T("%Y-%m-%d %H:%M:%S"))
        if target <= now:
            self.ctx.cfg["rdv_time"] = ""
            self.ctx.cfg["rdv_at"] = ""
            self.ctx.save()
            if now - target <= timedelta(seconds=MISSED_WINDOW_S):
                self.ctx.root.after(1500, lambda: self.notify("rdv_missed"))
            return
        try:
            warn = int(self.ctx.cfg.get("rdv_warn_min", 15))
        except (TypeError, ValueError):
            warn = 15
        self.set_rdv(target, warn, self.ctx.cfg.get("rdv_notif", "none"))

    def _loop(self):
        try:
            self.tick()
        finally:
            self._job = self.ctx.root.after(CHECK_EVERY_MS, self._loop)

    def reschedule(self):
        now = time.time()
        self.next = {k: now + self.cfg[k]["every"] * 60 for k in INTERVAL_KINDS if self.cfg[k]["on"]}
        self.pending.clear()

    def blocked(self):
        if self.ctx.cfg.get("game_mode_on"):
            return True
        # Rien n'est active par defaut : la detection automatique de jeu / plein ecran
        # ne s'applique que si l'utilisateur a active la section.
        if not self.cfg.get("dnd_enabled", False):
            return False
        return bool(self.cfg.get("auto_detect", False) and winui.fullscreen_busy())

    def _queue(self, kind):
        if kind not in self.pending:
            self.pending.append(kind)

    def _meal_slots(self):
        m = self.cfg["meals"]
        slots = []
        if m.get("on"):
            slots.append(("lunch", m.get("lunch", "12:30"), "meal_lunch"))
            slots.append(("dinner", m.get("dinner", "19:30"), "meal_dinner"))
        if m.get("snack_am_on", False):
            slots.append(("snack_am", m.get("snack_am", "10:30"), "meal_snack_am"))
        if m.get("snack_pm_on", False):
            slots.append(("snack_pm", m.get("snack_pm", "16:00"), "meal_snack_pm"))
        for extra in m.get("extra_slots", []):
            if extra.get("on", False):
                slots.append((extra["id"], extra.get("time", "15:00"), f"meal_{extra['id']}"))
        return slots

    def tick(self, now=None):
        now = now or time.time()
        for kind in INTERVAL_KINDS:
            c = self.cfg[kind]
            if not c["on"]:
                self.next.pop(kind, None)
                continue
            self.next.setdefault(kind, now + c["every"] * 60)
            if now >= self.next[kind]:
                self.next[kind] = now + c["every"] * 60
                self._queue(kind)
        done = self.meals_done
        today = time.strftime("%Y-%m-%d", time.localtime(now))
        for slot_id, time_str, msg_key in self._meal_slots():
            try:
                hh, mm = (int(x) for x in time_str.split(":"))
                t = datetime.fromtimestamp(now).replace(hour=hh, minute=mm, second=0, microsecond=0).timestamp()
            except (ValueError, KeyError):
                continue
            if (today, slot_id) in done:
                continue
            if now >= t and now - t <= 90 * 60:      # dans la fenêtre : l'heure système du créneau vient de passer
                done.add((today, slot_id))
                self.meals_done = done
                self._queue(msg_key)
            elif now - t > 90 * 60:
                done.add((today, slot_id))            # créneau trop passé : on ne te bombe pas de rappels en retard
                self.meals_done = done
        if not self.pending:
            return
        if self.blocked():
            if self.cfg.get("defer") == "flash":
                for k in list(self.pending):
                    self.flash(k)
                self.pending.clear()
            return
        self.notify(self.pending.pop(0))

    def snooze(self, kind, minutes=10):
        self.ctx.root.after(minutes * 60000, lambda: self._queue(kind))
