import math
import time
from tkinter import ttk
from Shared.Utils import config, sound
from UI.components import FlowFrame, run_bg, auto_wrap
from Shared.Utils.common import IS_WINDOWS, is_admin
from Shared.Utils.lang import T


class Page(ttk.Frame):
    def __init__(self, master, ctx, title, subtitle=""):
        super().__init__(master, padding=14)
        self.ctx = ctx
        self._busy = None
        ttk.Label(self, text=T(title), style="Title.TLabel").pack(anchor="w")
        if subtitle:
            self.subtitle_lbl = auto_wrap(ttk.Label(self, text=T(subtitle), style="Muted.TLabel",
                                                  justify="left"))
            self.subtitle_lbl.pack(anchor="w", fill="x", pady=(2, 8))
        self.bar = FlowFrame(self)
        self.bar.pack(fill="x", pady=(0, 8))
        self.status = auto_wrap(ttk.Label(self, text="", style="Muted.TLabel", justify="left"))
        self.status.pack(side="bottom", anchor="w", fill="x", pady=(6, 0))
        self.progress = ttk.Progressbar(self, mode="indeterminate")

    def button(self, text, cmd, accent=False):
        b = ttk.Button(self.bar, text=T(text), command=cmd, style="Accent.TButton" if accent else "TButton")
        self.bar.add(b)
        return b

    def admin_button(self):
        if IS_WINDOWS and not is_admin():
            self.button("🛡 Relancer en administrateur", self.ctx.ask_admin)

    def say(self, text):
        self.status.configure(text=self.ctx.mask(T(text)))

    # --- preservation de la position de defilement a travers un rebuild ---
    def _find_sf(self, w=None):
        from UI.components import ScrollFrame
        for c in (w if w is not None else self).winfo_children():
            if isinstance(c, ScrollFrame):
                return c
            r = self._find_sf(c)
            if r is not None:
                return r
        return None

    def get_scroll(self):
        sf = self._find_sf()
        return sf.get_view() if sf else 0.0

    def set_scroll(self, frac):
        sf = self._find_sf()
        if sf is not None:
            self.after(120, lambda: sf.set_view(frac))

    # --- attente rassurante : barre + temps estimé (appris des scans précédents) ---
    def busy(self, text, key="default"):
        est = self.ctx.cfg["durations"].get(key, 5)
        self._busy = (time.time(), est, key, text)
        self.progress.pack(side="bottom", fill="x", pady=(6, 0))
        self.progress.start(14)
        self._tick()

    def _tick(self):
        if not self._busy:
            return
        t0, est, _, text = self._busy
        elapsed = time.time() - t0
        left = est - elapsed
        if elapsed > est + 3:
            msg = f"{text}… un peu plus long que d'habitude, tout va bien"
        elif left > 20:
            msg = f"{text}… compte environ une minute. Tu peux faire autre chose, je te préviens à la fin"
        elif left > 10:
            msg = f"{text}… moins d'une minute"
        elif left > 5:
            msg = f"{text}… moins de 10 secondes, tu y es presque"
        elif left > 1:
            msg = f"{text}… encore {math.ceil(left)} secondes"
        else:
            msg = f"{text}… presque fini"
        self.status.configure(text=msg)
        self.after(500, self._tick)

    def idle(self, key=None):
        if self._busy:
            elapsed = time.time() - self._busy[0]
            self.ctx.cfg["durations"][self._busy[2]] = round(max(1.0, elapsed), 1)
            config.save(self.ctx.cfg)
            if elapsed >= 3 and self.ctx.cfg.get("sound", True):
                sound.chime()          # carillon doux : tu peux quitter l'écran des yeux
        self._busy = None
        self.progress.stop()
        self.progress.pack_forget()

    def load(self, key, fn, apply, ttl=60, force=False):
        """Affiche tout de suite la dernière valeur connue, puis rafraîchit EN ARRIÈRE-PLAN si elle est trop vieille.
        (Avant : les commandes lentes bloquaient l'interface à chaque changement d'onglet.)"""
        ctx = self.ctx
        c = ctx.cache.get(key)
        if c:
            apply(c[1])
            if not force and time.time() - c[0] < ttl:
                return
        if key in ctx.loading:
            return
        ctx.loading.add(key)

        def done(r, e):
            ctx.loading.discard(key)
            if e is None:
                ctx.cache[key] = (time.time(), r)
                apply(r)
        run_bg(ctx.root, fn, done)

    def on_show(self):
        pass
