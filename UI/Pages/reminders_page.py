import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk, filedialog
from Shared.Utils import sound
from Services.Reminders.notif_ui_logic import apply_visible, banner_utile
from UI.components import ScrollFrame, VolumeBar, info_note, auto_wrap, FlowFrame
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
        self._ready = False
        self._pairs = []
        self._notif_targets = []
        self._extra_frames = []
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f, r = sf.inner, ctx.cfg["reminders"]
        # Bandeau « doit rester ouvert » : la place est réservée en permanence
        # (hauteur fixe), donc l'apparition/disparition ne fait pas bouger la page.
        self._warn_holder = tk.Frame(f, bg=ctx.theme["bg"], height=int(24 * ctx.scale))
        self._warn_holder.pack(fill="x", pady=(0, 6))
        self._warn_holder.pack_propagate(False)
        self._warn_note = info_note(self._warn_holder, ctx.theme, ctx.status_colors["info"],
                                    "TidyDeck doit rester ouvert, même réduit, pour te rappeler.",
                                    wraplength=640)
        self.v = {}
        meals = r["meals"]

        def row(pady=2):
            fr = ttk.Frame(f)
            fr.pack(fill="x", pady=pady)
            return fr

        def frow(pady=2):
            # FlowFrame (lot D) : à 900 px, « Tester » et le bloc Son/Visuel
            # passent à la ligne au lieu d'être coupés au bord droit.
            fr = FlowFrame(f)
            fr.pack(fill="x", pady=pady)
            return fr

        def put(fr, w, right=False):
            fr.add(w, right=right)
            return w

        def tester(parent, key):
            put(parent, ttk.Button(parent, text=T("Tester"),
                                   command=lambda k=key: self.test(k)))

        def every(parent, key, field, values):
            var = tk.StringVar(value=str(r[key][field]))
            self.v[f"{key}.{field}"] = var
            put(parent, ttk.Label(parent, text=T("toutes les")))
            put(parent, ttk.Combobox(parent, textvariable=var,
                                     values=[str(x) for x in values],
                                     width=4, state="readonly"))
            put(parent, ttk.Label(parent, text=T("min"), style="Muted.TLabel"))

        fr = frow()
        self.v["hydration.on"] = tk.BooleanVar(value=r["hydration"]["on"])
        put(fr, ttk.Checkbutton(fr, text=T("💧 Hydratation"), variable=self.v["hydration.on"]))
        every(fr, "hydration", "every", [45, 60])
        tester(fr, "hydration")
        self._notif_ui(fr, self.v["hydration.on"], r["hydration"], "notif")

        fr = frow()
        self.v["meals.on"] = tk.BooleanVar(value=meals.get("on", False))
        put(fr, ttk.Checkbutton(fr, text=T("🍽 Repas principaux"), variable=self.v["meals.on"]))
        put(fr, ttk.Label(fr, text=T("Midi")))
        self.v["meals.lunch"] = tk.StringVar(value=meals["lunch"])
        put(fr, ttk.Entry(fr, textvariable=self.v["meals.lunch"], width=6))
        put(fr, ttk.Label(fr, text=T("Soir")))
        self.v["meals.dinner"] = tk.StringVar(value=meals["dinner"])
        put(fr, ttk.Entry(fr, textvariable=self.v["meals.dinner"], width=6))
        tester(fr, "meals")
        self._notif_ui(fr, self.v["meals.on"], meals, "notif")

        fr = frow()
        self.v["meals.snack_am_on"] = tk.BooleanVar(value=meals.get("snack_am_on", False))
        put(fr, ttk.Checkbutton(fr, text=T("🍎 Snack matin"), variable=self.v["meals.snack_am_on"]))
        self.v["meals.snack_am"] = tk.StringVar(value=meals["snack_am"])
        put(fr, ttk.Entry(fr, textvariable=self.v["meals.snack_am"], width=6))
        self._notif_ui(fr, self.v["meals.snack_am_on"], meals, "snack_am_notif")

        fr = frow()
        self.v["meals.snack_pm_on"] = tk.BooleanVar(value=meals.get("snack_pm_on", False))
        put(fr, ttk.Checkbutton(fr, text=T("🍪 Snack après-midi"), variable=self.v["meals.snack_pm_on"]))
        self.v["meals.snack_pm"] = tk.StringVar(value=meals["snack_pm"])
        put(fr, ttk.Entry(fr, textvariable=self.v["meals.snack_pm"], width=6))
        self._notif_ui(fr, self.v["meals.snack_pm_on"], meals, "snack_pm_notif")

        ttk.Button(f, text=T("+ Ajouter un créneau personnalisé"), command=self._add_extra_slot).pack(anchor="w", pady=(2, 0))
        self._slots_frame = ttk.Frame(f)
        self._slots_frame.pack(fill="x", anchor="w")
        self._extra_frames = []
        for i, extra in enumerate(meals.get("extra_slots", [])):
            self._build_extra_slot(self._slots_frame, i, extra)

        fr = frow()
        self.v["eyes.on"] = tk.BooleanVar(value=r["eyes"]["on"])
        put(fr, ttk.Checkbutton(fr, text=T("👀 Pause visuelle 20-20-20"), variable=self.v["eyes.on"]))
        every(fr, "eyes", "every", [20])
        tester(fr, "eyes")
        self._notif_ui(fr, self.v["eyes.on"], r["eyes"], "notif")
        ttk.Label(f, text=T("(regarder au loin 20 s)"), style="Muted.TLabel").pack(anchor="w")

        fr = frow()
        self.v["stretch.on"] = tk.BooleanVar(value=r["stretch"]["on"])
        put(fr, ttk.Checkbutton(fr, text=T("🧘 S'étirer / bouger"), variable=self.v["stretch.on"]))
        every(fr, "stretch", "every", [60, 90, 120])
        tester(fr, "stretch")
        self._notif_ui(fr, self.v["stretch.on"], r["stretch"], "notif")

        fr = row(pady=(4, 2))
        self._apply_link = ttk.Label(fr, text=T("Appliquer à tous les rappels"), style="Link.TLabel",
                                     cursor="hand2")
        self._apply_link.pack(side="left", padx=(24, 0))
        self._apply_link.bind("<Button-1>", self._apply_all_notif)

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
        self.rdv_status = auto_wrap(ttk.Label(f, text=T(""), style="Muted.TLabel", justify="left"))
        self.rdv_status.pack(fill="x")
        fr_notif = row(pady=2)
        ttk.Label(fr_notif, text=T("Notification RDV :")).pack(side="left", padx=(0, 8))
        cur = ctx.cfg.get("rdv_notif", "none")
        self.rdv_visual = tk.BooleanVar(value=cur in ("visual", "both"))
        self.rdv_sound = tk.BooleanVar(value=cur in ("sound", "both"))
        ttk.Checkbutton(fr_notif, text=T("Visuel"), variable=self.rdv_visual).pack(side="left", padx=(0, 12))
        ttk.Checkbutton(fr_notif, text=T("Son"), variable=self.rdv_sound).pack(side="left", padx=(0, 12))
        self.rdv_soft = ttk.Label(f, text=T("Aucune alerte : le minuteur ne te préviendra pas."),
                                  style="Muted.TLabel")

        def refresh_rdv_soft(*_):
            if not self.rdv_visual.get() and not self.rdv_sound.get():
                self.rdv_soft.pack(anchor="w", after=fr_notif)
            else:
                self.rdv_soft.pack_forget()

        self.rdv_visual.trace_add("write", refresh_rdv_soft)
        self.rdv_sound.trace_add("write", refresh_rdv_soft)
        refresh_rdv_soft()
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
        for k in ("hydration.on", "meals.on", "meals.snack_am_on", "meals.snack_pm_on",
                  "eyes.on", "stretch.on"):
            self.v[k].trace_add("write", self._refresh_banner)
        self._ready = True
        self._refresh_banner()
        self._arm_autosave()

    def _notif_ui(self, fr, on_var, cfg_obj, key):
        """Deux mini-cases par rappel (🔔 Visuel / 🔊 Son), collées à droite de sa ligne.

        Elles n'apparaissent que quand le rappel est activé ; « Visuel » est coché
        par défaut à l'activation. En mode Sérénité, seule la case « Son » est
        affichée : « Visuel » reste tel qu'enregistré (la valeur n'est jamais
        modifiée par le simple fait de changer de mode). Si plus rien n'est coché,
        une phrase douce prévient au lieu de laisser le rappel muet sans rien dire.
        """
        cur = cfg_obj.get(key, "visual") if isinstance(cfg_obj, dict) else "visual"
        serene = self.ctx.cfg.get("serenity", False)
        vis = tk.BooleanVar(value=cur in ("visual", "both"))
        snd = tk.BooleanVar(value=cur in ("sound", "both"))
        nf = ttk.Frame(fr)
        cb_s = ttk.Checkbutton(nf, text=T("🔊 Son"), variable=snd)
        cb_v = ttk.Checkbutton(nf, text=T("🔔 Visuel"), variable=vis)
        cb_s.pack(side="left", padx=(6, 0))
        if not serene:
            cb_v.pack(side="left", padx=(6, 0))
        soft = ttk.Label(fr.master, text=T("Sans notification ni son, tu ne verras rien."),
                         style="Muted.TLabel")

        def refresh(*_):
            if on_var.get():
                fr.add(nf, right=True)
            else:
                fr.remove(nf)
            if on_var.get() and not serene and not vis.get() and not snd.get():
                soft.pack(anchor="w", pady=(0, 2), after=fr)
            else:
                soft.pack_forget()
            self._refresh_banner()

        def on_on(*_):
            if on_var.get() and not vis.get() and not snd.get() and not serene:
                vis.set(True)
            refresh()

        on_var.trace_add("write", on_on)
        vis.trace_add("write", lambda *_: (refresh(), self._autosave()))
        snd.trace_add("write", lambda *_: (refresh(), self._autosave()))
        refresh()
        self._pairs.append(dict(vis=vis, snd=snd, on=on_var))
        if isinstance(cfg_obj, dict):
            self._notif_targets.append((vis, snd, cfg_obj, key))

    def _apply_all_notif(self, _e=None):
        # La source est le PREMIER rappel activé (pas simplement la première
        # ligne) ; la copie inclut les créneaux personnalisés. En Sérénité, seul
        # « Son » est copié : « Visuel » reste tel qu'enregistré.
        src = next((p for p in self._pairs if p["on"].get()), None)
        if src is None:
            return
        serene = self.ctx.cfg.get("serenity", False)
        for p in self._pairs:
            if p is src:
                continue
            p["snd"].set(src["snd"].get())
            if not serene:
                p["vis"].set(src["vis"].get())
        self.say(T("✔ Appliqué à tous les rappels."))

    def _refresh_banner(self, *_):
        if not getattr(self, "_ready", False):
            return  # pendant la construction de la page, toutes les variables
            # n'existent pas encore : le rafraichissement final aura lieu a la fin.
        m = self.v
        etat = {
            "hydration": {"on": m["hydration.on"].get()},
            "eyes": {"on": m["eyes.on"].get()},
            "stretch": {"on": m["stretch.on"].get()},
            "meals": {"on": m["meals.on"].get(),
                      "snack_am_on": m["meals.snack_am_on"].get(),
                      "snack_pm_on": m["meals.snack_pm_on"].get(),
                      "extra_slots": [{"on": self.v[f"extra_{i}_on"].get()}
                                      for i, _ in self._extra_frames]},
        }
        if getattr(self, "_apply_link", None) is not None:
            if apply_visible([p["on"].get() for p in self._pairs]):
                self._apply_link.pack(side="left", padx=(24, 0))
            else:
                self._apply_link.pack_forget()
        rdv = bool(self.ctx.cfg.get("rdv_time"))
        if banner_utile(etat, rdv):
            self._warn_note.pack(anchor="w")
            self._warn_holder.update_idletasks()
            self._warn_holder.configure(height=max(self._warn_note.winfo_reqheight(), 2))
        else:
            self._warn_note.pack_forget()

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
        # FlowFrame (lot D) : mêmes lignes que les rappels fixes, mêmes règles.
        box = FlowFrame(parent)
        box.pack(fill="x", padx=28, pady=2)
        var_on = tk.BooleanVar(value=extra.get("on", False))
        var_time = tk.StringVar(value=extra.get("time", "15:00"))
        var_name = tk.StringVar(value=extra.get("name", T("Créneau {v0}").format(v0=idx + 1)))
        self.v[f"extra_{idx}_on"] = var_on
        self.v[f"extra_{idx}_time"] = var_time
        self.v[f"extra_{idx}_name"] = var_name
        box.add(ttk.Checkbutton(box, textvariable=var_name, variable=var_on))
        box.add(ttk.Entry(box, textvariable=var_time, width=6))
        box.add(ttk.Label(box, text=T("(HH:MM)"), style="Muted.TLabel"))
        box.add(ttk.Button(box, text=T("✕"), width=3, command=lambda b=box, i=idx: self._remove_extra_slot(b, i)))
        cur = extra.get("notif", "visual")
        serene = self.ctx.cfg.get("serenity", False)
        self.v[f"extra_{idx}_vis"] = tk.BooleanVar(value=cur in ("visual", "both"))
        self.v[f"extra_{idx}_snd"] = tk.BooleanVar(value=cur in ("sound", "both"))
        nf = ttk.Frame(box)
        ttk.Checkbutton(nf, text=T("🔊 Son"), variable=self.v[f"extra_{idx}_snd"]).pack(side="left", padx=(6, 0))
        if not serene:
            ttk.Checkbutton(nf, text=T("🔔 Visuel"), variable=self.v[f"extra_{idx}_vis"]).pack(side="left", padx=(6, 0))

        def show_nf(*_):
            if var_on.get():
                box.add(nf, right=True)
            else:
                box.remove(nf)

        if var_on.get():
            box.add(nf, right=True)
        self._pairs.append(dict(vis=self.v[f"extra_{idx}_vis"],
                                snd=self.v[f"extra_{idx}_snd"], on=var_on))
        for var in (self.v[f"extra_{idx}_vis"], self.v[f"extra_{idx}_snd"]):
            var.trace_add("write", lambda *_a: (show_nf(), self._autosave()))
        var_on.trace_add("write", lambda *_a: show_nf())
        var_on.trace_add("write", self._refresh_banner)
        self._extra_frames.append((idx, box))

    def _add_extra_slot(self):
        idx = len(self._extra_frames)
        new_extra = {"id": f"custom_{idx}", "name": T("Créneau {v0}").format(v0=idx + 1), "time": "15:00", "on": True}
        self._build_extra_slot(self._slots_frame, idx, new_extra)

    def _remove_extra_slot(self, box, idx):
        box.destroy()
        self._extra_frames = [(i, b) for i, b in self._extra_frames if i != idx]
        self._pairs = [p for p in self._pairs if p.get("on") is not self.v.get(f"extra_{idx}_on")]
        self._refresh_banner()

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
        self._refresh_banner()

    def _cancel_rdv(self):
        self.ctx.cfg["rdv_time"] = ""
        self.ctx.cfg["rdv_at"] = ""
        self.ctx.save()
        self.rdv_status.configure(text=T("⏹ Minuteur arrêté. Plus aucun rappel de rendez-vous ne partira."))
        self.ctx.app.scheduler.cancel_rdv()
        self._refresh_banner()

    def test(self, key):
        kind = {"meals": "meal_lunch"}.get(key, key)
        self.ctx.app.show_reminder(kind, test=True)

    def save(self, silent=False):
        r, v = self.ctx.cfg["reminders"], self.v
        bad = []
        serene = self.ctx.cfg.get("serenity", False)

        def _notif(vis_var, snd_var):
            vis_eff, snd_eff = vis_var.get(), snd_var.get()
            res = ("both" if (vis_eff and snd_eff) else "visual" if vis_eff
                   else "sound" if snd_eff else "none")
            # Sérénité : on ne touche jamais un choix enregistré ; si la ligne
            # se retrouve complètement muette (ni visuel ni son), on retombe
            # sur « visual », rien de plus.
            if serene and res == "none":
                return "visual"
            return res

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
        for vis, snd, obj, k in self._notif_targets:
            obj[k] = _notif(vis, snd)
        extras = []
        for i, (orig_idx, _) in enumerate(self._extra_frames):
            t = v.get(f"extra_{orig_idx}_time", tk.StringVar(value="15:00")).get().strip()
            if not _valid_time(t):
                bad.append(T("créneau personnalisé"))
                continue
            vis_v = v.get(f"extra_{orig_idx}_vis", tk.BooleanVar(value=True))
            snd_v = v.get(f"extra_{orig_idx}_snd", tk.BooleanVar(value=False))
            extras.append({"id": f"custom_{orig_idx}", "name": v.get(f"extra_{orig_idx}_name", tk.StringVar(value=T("Créneau {v0}").format(v0=orig_idx + 1))).get(),
                          "time": t, "on": v.get(f"extra_{orig_idx}_on", tk.BooleanVar(value=False)).get(),
                          "notif": _notif(vis_v, snd_v)})
        r["meals"]["extra_slots"] = extras
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
