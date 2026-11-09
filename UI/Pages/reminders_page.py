import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk, filedialog
from Shared.Utils import sound
from UI.components import ScrollFrame, VolumeBar, info_note
from UI.Pages.base import Page
from Shared.Utils.lang import T


def _valid_time(s):
    try:
        hh, mm = s.split(":")
        return 0 <= int(hh) < 24 and 0 <= int(mm) < 60
    except ValueError:
        return False


class RemindersPage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Rappels bien-être",
                         "Des petits coups de pouce doux, jamais insistants. Tout est désactivé tant que tu ne l'actives pas.")
        self._save_job = None
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f, r = sf.inner, ctx.cfg["reminders"]
        info_note(f, ctx.theme, ctx.status_colors["info"],
                  "⚠️ TidyDeck doit rester ouvert pour te rappeler : réduis-le dans la barre des tâches "
                  "ou la zone de notification, mais ne le ferme pas.", wraplength=640).pack(anchor="w", pady=(0, 6))
        self.v = {}
        meals = r["meals"]

        def row(pady=2):
            fr = ttk.Frame(f)
            fr.pack(fill="x", pady=pady)
            return fr

        def tester(parent, key):
            ttk.Button(parent, text=T("Tester"), command=lambda k=key: self.test(k)).pack(side="left", padx=(14, 0))

        def every(parent, key, field, values):
            var = tk.StringVar(value=str(r[key][field]))
            self.v[f"{key}.{field}"] = var
            ttk.Label(parent, text=T("toutes les")).pack(side="left", padx=(12, 4))
            ttk.Combobox(parent, textvariable=var, values=[str(x) for x in values], width=4, state="readonly").pack(side="left")
            ttk.Label(parent, text=T("min"), style="Muted.TLabel").pack(side="left", padx=(4, 0))

        fr = row()
        self.v["hydration.on"] = tk.BooleanVar(value=r["hydration"]["on"])
        ttk.Checkbutton(fr, text=T("💧 Hydratation"), variable=self.v["hydration.on"]).pack(side="left")
        every(fr, "hydration", "every", [45, 60])
        tester(fr, "hydration")

        fr = row()
        self.v["meals.on"] = tk.BooleanVar(value=meals.get("on", False))
        ttk.Checkbutton(fr, text=T("🍽 Repas principaux"), variable=self.v["meals.on"]).pack(side="left")
        ttk.Label(fr, text=T("Midi")).pack(side="left", padx=(14, 4))
        self.v["meals.lunch"] = tk.StringVar(value=meals["lunch"])
        ttk.Entry(fr, textvariable=self.v["meals.lunch"], width=6).pack(side="left")
        ttk.Label(fr, text=T("Soir")).pack(side="left", padx=(12, 4))
        self.v["meals.dinner"] = tk.StringVar(value=meals["dinner"])
        ttk.Entry(fr, textvariable=self.v["meals.dinner"], width=6).pack(side="left")
        tester(fr, "meals")

        fr = row()
        self.v["meals.snack_am_on"] = tk.BooleanVar(value=meals.get("snack_am_on", False))
        ttk.Checkbutton(fr, text=T("🍎 Snack matin"), variable=self.v["meals.snack_am_on"]).pack(side="left")
        self.v["meals.snack_am"] = tk.StringVar(value=meals["snack_am"])
        ttk.Entry(fr, textvariable=self.v["meals.snack_am"], width=6).pack(side="left", padx=(6, 0))
        self.v["meals.snack_pm_on"] = tk.BooleanVar(value=meals.get("snack_pm_on", False))
        ttk.Checkbutton(fr, text=T("🍪 Snack après-midi"), variable=self.v["meals.snack_pm_on"]).pack(side="left", padx=(20, 0))
        self.v["meals.snack_pm"] = tk.StringVar(value=meals["snack_pm"])
        ttk.Entry(fr, textvariable=self.v["meals.snack_pm"], width=6).pack(side="left", padx=(6, 0))

        ttk.Button(f, text=T("+ Ajouter un créneau personnalisé"), command=self._add_extra_slot).pack(anchor="w", pady=(2, 0))
        self._slots_frame = ttk.Frame(f)
        self._slots_frame.pack(anchor="w")
        self._extra_frames = []
        for i, extra in enumerate(meals.get("extra_slots", [])):
            self._build_extra_slot(self._slots_frame, i, extra)

        fr = row()
        self.v["eyes.on"] = tk.BooleanVar(value=r["eyes"]["on"])
        ttk.Checkbutton(fr, text=T("👀 Pause visuelle 20-20-20"), variable=self.v["eyes.on"]).pack(side="left")
        every(fr, "eyes", "every", [20])
        tester(fr, "eyes")
        ttk.Label(f, text=T("(regarder au loin 20 s)"), style="Muted.TLabel").pack(anchor="w")

        fr = row()
        self.v["stretch.on"] = tk.BooleanVar(value=r["stretch"]["on"])
        ttk.Checkbutton(fr, text=T("🧘 S'étirer / bouger"), variable=self.v["stretch.on"]).pack(side="left")
        every(fr, "stretch", "every", [60, 90, 120])
        tester(fr, "stretch")

        fr = row()
        self.v["sound"] = tk.BooleanVar(value=r["sound"])
        ttk.Checkbutton(fr, text=T("🔔 Petit carillon doux avec chaque rappel"), variable=self.v["sound"]).pack(side="left")

        ttk.Label(f, text=T("Où apparaissent les rappels :"), style="Sub.TLabel").pack(anchor="w", pady=(6, 2))
        self.toast_pos = tk.StringVar(value=ctx.cfg.get("toast_position", "bottom-right"))
        # Les 4 positions sur une seule ligne : la taille « très grande » (seule à
        # déborder) a été retirée du programme, la ligne tient désormais toujours.
        line = ttk.Frame(f)
        line.pack(anchor="w", pady=1)
        from UI.components import RadiOpt
        for text, val in ((T("Bas droite"), "bottom-right"), (T("Bas gauche"), "bottom-left"),
                          (T("Haut droite"), "top-right"), (T("Haut gauche"), "top-left")):
            RadiOpt(line, text=text, value=val, variable=self.toast_pos).pack(
                side="left", padx=(0, 16))

        fr = row(pady=(6, 0))
        ttk.Label(fr, text=T("⏰ Minuteur de rendez-vous"), style="Sub.TLabel").pack(side="left")
        ttk.Label(f, text=T("Je préviens avant pour que tu finisses ta partie sans stress."),
                  style="Muted.TLabel").pack(anchor="w")
        # Les contrôles du RDV sont répartis sur deux lignes : à taille de texte
        # « grande » ou « très grande », une seule ligne dépasserait la largeur utile
        # et les éléments seraient rognés / se chevaucheraient.
        fr = row(pady=2)
        self.rdv_time = tk.StringVar(value=ctx.cfg.get("rdv_time", ""))
        self.rdv_warn = tk.StringVar(value=str(ctx.cfg.get("rdv_warn_min", 15)))
        ttk.Label(fr, text=T("Heure du RDV")).pack(side="left")
        ttk.Entry(fr, textvariable=self.rdv_time, width=6).pack(side="left", padx=(6, 0))
        ttk.Label(fr, text=T("(HH:MM)"), style="Muted.TLabel").pack(side="left", padx=(4, 0))
        ttk.Label(fr, text=T("Prévenir")).pack(side="left", padx=(16, 0))
        ttk.Entry(fr, textvariable=self.rdv_warn, width=6).pack(side="left", padx=(6, 0))
        ttk.Label(fr, text=T("min avant")).pack(side="left", padx=(4, 0))
        fr = row(pady=2)
        ttk.Button(fr, text=T("⏰ Démarrer le minuteur"), command=self._set_rdv).pack(side="left")
        ttk.Button(fr, text=T("⏹ Arrêter"), command=self._cancel_rdv).pack(side="left", padx=(8, 0))
        self.rdv_status = ttk.Label(f, text=T(""), style="Muted.TLabel")
        self.rdv_status.pack(anchor="w")
        fr = row(pady=2)
        ttk.Label(fr, text=T("Notification RDV :")).pack(side="left", padx=(0, 8))
        cur = ctx.cfg.get("rdv_notif", "none")
        self.rdv_visual = tk.BooleanVar(value=cur in ("visual", "both"))
        self.rdv_sound = tk.BooleanVar(value=cur in ("sound", "both"))
        ttk.Checkbutton(fr, text=T("Visuel"), variable=self.rdv_visual).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(fr, text=T("Son"), variable=self.rdv_sound).pack(side="left", padx=(0, 12))
        ttk.Label(f, style="Muted.TLabel",
                  text=T("Rien n'est coché par défaut : coche ce que tu veux, décoche quand tu veux.")).pack(anchor="w")
        fr = row(pady=2)
        ttk.Button(fr, text=T("🔊 Tester le son RDV"), command=self._test_rdv_sound).pack(side="left")
        ttk.Button(fr, text=T("🎵 Changer le son…"), command=self._pick_sound).pack(side="left", padx=(8, 0))
        self.rdv_snd_lbl = ttk.Label(f, style="Muted.TLabel")
        self.rdv_snd_lbl.pack(anchor="w")
        self._refresh_sound_lbl()
        fr = row(pady=2)
        ttk.Label(fr, text=T("Volume du son RDV :")).pack(side="left")
        self.rdv_vol_var = tk.IntVar(value=int(ctx.cfg.get("rdv_volume", 70)))
        VolumeBar(fr, ctx.theme, self.rdv_vol_var, ctx.theme["volume"],
                  on_release=self._rdv_vol_saved).pack(side="left", padx=(10, 0))
        self._arm_autosave()

    def _arm_autosave(self):
        # Comme Apparence/Configuration : pas de bouton « Appliquer »,
        # chaque changement est enregistre tout seul (debounce 400 ms).
        for var in list(self.v.values()) + [self.toast_pos, self.rdv_visual, self.rdv_sound]:
            var.trace_add("write", self._autosave)

    def _autosave(self, *_):
        if self._save_job:
            try:
                self.after_cancel(self._save_job)
            except Exception:
                from Shared.Utils import depannage
                depannage.noter("UI/Pages/reminders_page.py:163")
        self._save_job = self.after(400, self._save_now)

    def _save_now(self):
        self._save_job = None
        self.save(silent=True)

    def _rdv_vol_saved(self, _e=None):
        v = int(round(float(self.rdv_vol_var.get())))
        self.ctx.cfg["rdv_volume"] = v
        self.ctx.save()
        sound.play(self.ctx.cfg.get("custom_sound") or None, v / 100.0)

    def _refresh_sound_lbl(self):
        c = self.ctx.cfg.get("custom_sound") or ""
        self.rdv_snd_lbl.configure(text=(T("Son personnalisé : {v0}").format(v0=c)) if c else T("Son actuel : carillon doux par défaut."))

    def _test_rdv_sound(self):
        sound.play(self.ctx.cfg.get("custom_sound") or None, self.rdv_vol_var.get() / 100.0)

    def _pick_sound(self):
        path = filedialog.askopenfilename(title="Choisis un son (fichier WAV)",
                                        filetypes=[("Son WAV", "*.wav"), ("Tous les fichiers", "*.*")])
        if path:
            self.ctx.cfg["custom_sound"] = path
            self.ctx.save()
            self._refresh_sound_lbl()
            sound.play(path, self.rdv_vol_var.get() / 100.0)

    def _build_extra_slot(self, parent, idx, extra):
        box = ttk.Frame(parent)
        box.pack(anchor="w", padx=28, pady=2)
        var_on = tk.BooleanVar(value=extra.get("on", False))
        var_time = tk.StringVar(value=extra.get("time", "15:00"))
        var_name = tk.StringVar(value=extra.get("name", T("Créneau {v0}").format(v0=idx + 1)))
        self.v[f"extra_{idx}_on"] = var_on
        self.v[f"extra_{idx}_time"] = var_time
        self.v[f"extra_{idx}_name"] = var_name
        ttk.Checkbutton(box, textvariable=var_name, variable=var_on).pack(side="left")
        ttk.Entry(box, textvariable=var_time, width=6).pack(side="left", padx=6)
        ttk.Label(box, text=T("(HH:MM)"), style="Muted.TLabel").pack(side="left")
        ttk.Button(box, text=T("✕"), width=3, command=lambda b=box, i=idx: self._remove_extra_slot(b, i)).pack(side="left", padx=4)
        self._extra_frames.append((idx, box))

    def _add_extra_slot(self):
        idx = len(self._extra_frames)
        new_extra = {"id": f"custom_{idx}", "name": T("Créneau {v0}").format(v0=idx + 1), "time": "15:00", "on": True}
        self._build_extra_slot(self._slots_frame, idx, new_extra)

    def _remove_extra_slot(self, box, idx):
        box.destroy()
        self._extra_frames = [(i, b) for i, b in self._extra_frames if i != idx]

    def _set_rdv(self):
        t = self.rdv_time.get().strip()
        if not _valid_time(t):
            messagebox.showwarning("TidyDeck", T("Heure invalide. Format : HH:MM (ex: 14:30)"))
            return
        try:
            warn = int(self.rdv_warn.get())
        except ValueError:
            warn = 15
        notif = ("both" if (self.rdv_visual.get() and self.rdv_sound.get())
                 else "visual" if self.rdv_visual.get()
                 else "sound" if self.rdv_sound.get() else "none")
        hh, mm = (int(x) for x in t.split(":"))
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        when = "aujourd'hui"
        if target <= now:
            target += timedelta(days=1)
            when = "demain"
        self.ctx.cfg["rdv_time"] = t
        self.ctx.cfg["rdv_at"] = target.strftime(T("%Y-%m-%d %H:%M:%S"))
        self.ctx.cfg["rdv_warn_min"] = warn
        self.ctx.cfg["rdv_notif"] = notif
        self.ctx.save()
        label = {"both": "visuel + son", "visual": "visuel", "sound": "son",
                "none": "aucune (coche Visuel ou Son)"}[notif]
        self.rdv_status.configure(
            text=T("⏰ RDV {v0} à {v1} — alerte {v2} min avant. Notification : {v3}. "
                 "TidyDeck doit rester ouvert pour te rappeler.").format(v0=when, v1=t, v2=warn, v3=label))
        self.ctx.app.scheduler.set_rdv(target, warn, notif)

    def _cancel_rdv(self):
        self.ctx.cfg["rdv_time"] = ""
        self.ctx.cfg["rdv_at"] = ""
        self.ctx.save()
        self.rdv_status.configure(text=T("⏹ Minuteur arrêté. Plus aucun rappel de rendez-vous ne partira."))
        self.ctx.app.scheduler.cancel_rdv()

    def test(self, key):
        kind = {"meals": "meal_lunch"}.get(key, key)
        self.ctx.app.show_reminder(kind, test=True)

    def save(self, silent=False):
        r, v = self.ctx.cfg["reminders"], self.v
        bad = []
        for key in ("hydration", "meals", "eyes", "stretch"):
            r[key]["on"] = v[key + ".on"].get()
        for key, field in (("hydration", "every"), ("eyes", "every"), ("stretch", "every")):
            try:
                r[key][field] = int(v[f"{key}.{field}"].get())
            except (TypeError, ValueError):
                pass
        for slot in ("lunch", "dinner", "snack_am", "snack_pm"):
            t = v[f"meals.{slot}"].get().strip()
            if not _valid_time(t):
                bad.append(T("« {v0} »").format(v0=t))
                continue
            r["meals"][slot] = t
        r["meals"]["snack_am_on"] = v["meals.snack_am_on"].get()
        r["meals"]["snack_pm_on"] = v["meals.snack_pm_on"].get()
        extras = []
        for i, (orig_idx, _) in enumerate(self._extra_frames):
            t = v.get(f"extra_{orig_idx}_time", tk.StringVar(value="15:00")).get().strip()
            if not _valid_time(t):
                bad.append(T("créneau personnalisé"))
                continue
            extras.append({"id": f"custom_{orig_idx}", "name": v.get(f"extra_{orig_idx}_name", tk.StringVar(value=T("Créneau {v0}").format(v0=orig_idx + 1))).get(),
                          "time": t, "on": v.get(f"extra_{orig_idx}_on", tk.BooleanVar(value=False)).get()})
        r["meals"]["extra_slots"] = extras
        r["sound"] = v["sound"].get()
        self.ctx.cfg["toast_position"] = self.toast_pos.get()
        self.ctx.cfg["rdv_notif"] = ("both" if (self.rdv_visual.get() and self.rdv_sound.get())
                                     else "visual" if self.rdv_visual.get()
                                     else "sound" if self.rdv_sound.get() else "none")
        self.ctx.save()
        self.ctx.app.scheduler.reschedule()
        if bad:
            msg = T("⚠ Heure pas encore valide : {v0}. Écris-la comme 12:30 — le reste est bien enregistré.").format(v0=", ".join(bad))
            if silent:
                self.say(msg)
            else:
                messagebox.showwarning("TidyDeck", msg)
            return
        self.say(T("✔ Enregistré automatiquement, rien à appliquer."))
