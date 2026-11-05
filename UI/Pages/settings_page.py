import tkinter as tk
from tkinter import ttk
from Services.Reminders import autostart
from Shared.Utils.common import IS_WINDOWS
from Shared.Utils import config, sound
from Shared.Utils.lang import T
from Shared.Utils import lang
from UI.components import ScrollFrame, info_note, VolumeBar
from tkinter import filedialog


class _PrefsBase(ttk.Frame):
    def __init__(self, master, ctx):
        super().__init__(master, padding=14)
        self.ctx = ctx
        self._key_widgets = {}
        self.vars = {
            "theme": tk.StringVar(value=ctx.cfg["theme"]),
            "text_size": tk.StringVar(value=ctx.cfg["text_size"]),
            "lang": tk.StringVar(value=ctx.cfg.get("lang", "fr")),
            "colorblind": tk.BooleanVar(value=ctx.cfg["colorblind"]),
            "serenity": tk.BooleanVar(value=ctx.cfg["serenity"]),
            "advanced": tk.BooleanVar(value=ctx.cfg["advanced"]),
            "close_action": tk.StringVar(value=ctx.cfg["close_action"]),
            "sound": tk.BooleanVar(value=ctx.cfg["sound"]),
            "reminder": tk.BooleanVar(value=ctx.cfg["reminder"]),
            "stream_mode": tk.BooleanVar(value=ctx.cfg["stream_mode"]),
        }

    def _radio_group(self, parent, title, key, options, per_row=None):
        ttk.Label(parent, text=T(title), style="Sub.TLabel").pack(anchor="w", pady=(10, 2))
        if per_row:
            grid = ttk.Frame(parent)
            grid.pack(anchor="w")
            for i, (text, val) in enumerate(options):
                rb = ttk.Radiobutton(grid, text=T(text), value=val, variable=self.vars[key])
                rb.grid(row=i // per_row, column=i % per_row, sticky="w", padx=(0, 28), pady=2)
                self._key_widgets.setdefault(key, []).append(rb)
            return
        row = ttk.Frame(parent)
        row.pack(anchor="w")
        for text, val in options:
            rb = ttk.Radiobutton(row, text=T(text), value=val, variable=self.vars[key])
            rb.pack(side="left", padx=(0, 16))
            self._key_widgets.setdefault(key, []).append(rb)

    def _check(self, parent, key, text):
        st = ttk.Style()
        bg, fg = st.lookup("TFrame", "background"), st.lookup("TLabel", "foreground")
        cb = tk.Checkbutton(parent, text=T(text), variable=self.vars[key], wraplength=820, justify="left", anchor="w",
                       bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                       selectcolor=st.lookup("TEntry", "fieldbackground"),
                       highlightthickness=0, bd=0)
        cb.pack(anchor="w", pady=(7, 3))
        self._key_widgets.setdefault(key, []).append(cb)
        return cb

    def _check_var(self, parent, var, text, padx=24):
        st = ttk.Style()
        bg, fg = st.lookup("TFrame", "background"), st.lookup("TLabel", "foreground")
        cb = tk.Checkbutton(parent, text=T(text), variable=var, wraplength=820, justify="left", anchor="w",
                       bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                       selectcolor=st.lookup("TEntry", "fieldbackground"),
                       highlightthickness=0, bd=0)
        cb.pack(anchor="w", padx=padx, pady=(4, 3))
        return cb

    def _apply_common(self, on_apply):
        prev = dict(self.ctx.cfg)
        self.ctx.cfg.update({k: v.get() for k, v in self.vars.items()})
        on_apply(prev)

    def enable_live(self, on_apply):
        # Application en direct : chaque changement est appliqué aussitôt (débouncé pour
        # ne pas recréer l'interface à chaque événement). Pas de bouton « Appliquer ».
        self._live_pending = False
        for v in self.vars.values():
            v.trace_add("write", self._live)
        self._live_cb = on_apply

    def _live(self, *_):
        if self._live_pending:
            return
        self._live_pending = True
        self.after(250, self._do_live)

    def _do_live(self):
        self._live_pending = False
        self._apply_common(self._live_cb)


class SettingsPage(_PrefsBase):
    """Onglet Apparence — indépendant de la Configuration."""

    def __init__(self, master, ctx, on_apply):
        super().__init__(master, ctx)
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f = sf.inner
        ttk.Label(f, text=T("Apparence et modes"), style="Title.TLabel").pack(anchor="w")
        self._radio_group(f, "Thème", "theme",
                         [("Clair", "clair"), ("Sombre", "sombre"),
                          ("Chaleureux (confort visuel)", "tdah")])
        ttk.Label(f, style="Muted.TLabel", wraplength=900, justify="left",
                  text=T("Le thème choisit les couleurs. Les modes en dessous changent le comportement : "
                       "Sérénité = ton rassurant, avancé = plus de détails, daltonien = couleurs adaptées. "
                       "« Chaleureux » : contrastes doux, couleurs chaudes, rien d'agressif pour les yeux.")).pack(anchor="w", pady=(6, 6))
        self._radio_group(f, "Taille du texte", "text_size",
                         [("Normale", "normale"), ("Grande", "grande")])
        self._radio_group(f, "Langue", "lang",
                          [(lang.nom_langue("fr"), "fr"), (lang.nom_langue("en"), "en")])
        self._check(f, "colorblind", "Mode daltonien : couleurs adaptées. "
                                    "Les états ont toujours un symbole et un mot en plus de la couleur.")
        self._ser_cb = self._check(f, "serenity", "Mode Sérénité : des mots rassurants à la place des chiffres et des couleurs d'alerte. "
                                               "Pensé pour le TDAH, utile à tous ceux qui se sentent vite submergés.")
        self._adv_cb = self._check(f, "advanced", "Mode avancé : plus de détails (composants dépliables, toutes les options "
                                               "de nettoyage). Débloque des options sensibles (Corbeille, fichiers Windows). "
                                               "Chacune demande une confirmation.")
        # Conteneur à hauteur fixe : la place est réservée, le bouton « Appliquer » ne bouge jamais
        # quand le message apparaît/disparaît (pas de glissement ; Tkinter n'anime pas de toute façon).
        # NB : Tkinter n'expose pas role="status"/aria-live ; l'icône + le mot « Info » devant le texte
        # sont l'équivalent natif pour signaler l'apparition (un lecteur d'écran lit le libellé).
        self._adv_holder = tk.Frame(f, bg=ctx.theme["bg"], height=52)
        self._adv_holder.pack(fill="x", pady=(6, 0))
        self._adv_holder.pack_propagate(False)
        self._adv_note = info_note(self._adv_holder, ctx.theme, ctx.status_colors["info"],
                                  "Info — Ces options demandent plus d'attention : les actions sensibles (Corbeille, "
                                  "fichiers Windows) ne sont jamais cochées par défaut et passent toujours par "
                                  "une confirmation.")
        self.vars["advanced"].trace_add("write", self._refresh_adv_note)
        self.vars["serenity"].trace_add("write", self._refresh_adv_note)
        self._refresh_adv_note()
        ttk.Label(f, style="Muted.TLabel", justify="left",
                  text=T("Les changements s'appliquent immédiatement, pas besoin de valider.")).pack(anchor="w", pady=(8, 4))
        self.enable_live(on_apply)

    def _refresh_adv_note(self, *_):
        if self.vars["advanced"].get() and self.vars["serenity"].get():
            self._adv_note.pack(fill="x")
        else:
            self._adv_note.pack_forget()


class ConfigPage(_PrefsBase):
    """Onglet Configuration — indépendant de l'Apparence."""

    def __init__(self, master, ctx, on_apply):
        super().__init__(master, ctx)
        self.on_apply = on_apply
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f = sf.inner

        # Un seul choix exclusif pour la croix : fermer, barre des tâches, ou
        # horloge. L'ancienne case « tray » se combinait avec « Fermer » et
        # créait des états illogiques ; elle vit désormais comme close_action="tray".
        _close_opts = [("Fermer TidyDeck", "quit"), ("Réduire dans la barre des tâches", "minimize")]
        if IS_WINDOWS:
            _close_opts.append(("Réduire à côté de l'horloge (zone de notification)", "tray"))
        self._radio_group(f, "Comportement de la fenêtre — quand je clique sur la croix", "close_action",
                          _close_opts, per_row=1)
        if IS_WINDOWS:
            ttk.Label(f, style="Muted.TLabel", wraplength=900, justify="left",
                      text=T("Réduire à côté de l'horloge (zone de notification) : la croix cache la fenêtre "
                             "et TidyDeck reste accessible via son icône près de l'horloge — double-clique "
                             "dessus (ou clic droit > Ouvrir) pour le faire revenir.")).pack(anchor="w", pady=(2, 0))

        ttk.Label(f, text=T("Lancement automatique"), style="Sub.TLabel").pack(anchor="w", pady=(6, 2))
        self.auto = tk.BooleanVar(value=IS_WINDOWS and autostart.is_enabled())
        ttk.Checkbutton(f, text=T("Lancer TidyDeck avec Windows, réduit dans la barre des tâches"),
                        variable=self.auto).pack(anchor="w")
        ttk.Label(f, style="Muted.TLabel", text=T("Ajoute une simple entrée dans les programmes de démarrage de ton compte "
                  "(visible et annulable : onglet Démarrage, ou Journaux).")).pack(anchor="w", padx=22)

        ttk.Label(f, text=T("Vie privée"), style="Sub.TLabel").pack(anchor="w", pady=(6, 2))
        self._check(f, "stream_mode", "🕶️ Mode Discret : masque ton nom d'utilisateur, le nom du PC et tes chemins "
                                     "personnels à l'écran. Ne masque que ce que TidyDeck affiche — pas les autres "
                                     "applications. Sortie en un clic depuis la bannière.")
        ttk.Label(f, text=T("Notifications"), style="Sub.TLabel").pack(anchor="w", pady=(6, 2))
        self._check(f, "reminder", "Rappel doux, une fois par mois au maximum, pour penser à un petit nettoyage.")
        ttk.Label(f, style="Muted.TLabel", wraplength=900, justify="left",
                  text=T("La position des pop-ups de rappel se règle sur la page Rappels.")).pack(anchor="w", pady=(0, 0))

        ttk.Label(f, text=T("🎮 Pendant un jeu"), style="Sub.TLabel").pack(anchor="w", pady=(6, 2))
        self.dnd_var = tk.BooleanVar(value=bool(ctx.cfg["reminders"].get("dnd_enabled", False)))
        self._check_var(f, self.dnd_var,
                       T("Ne pas me déranger pendant que je joue (désactivé par défaut : tu choisis)."))
        # Emplacement réservé juste sous la phrase : les options s'affichent toujours ici,
        # jamais en bas de page (pack() ajouterait le bloc à la fin sinon).
        # Le bloc est volontairement compact (une ligne de choix + une note) : activé, il
        # n'ajoute qu'une seule hauteur de ligne et ne repousse pas le bas de page.
        self._dnd_slot = ttk.Frame(f)
        self._dnd_slot.pack(anchor="w", fill="x")
        self._dnd_box = ttk.Frame(self._dnd_slot)
        dnd_row = ttk.Frame(self._dnd_box)
        dnd_row.pack(anchor="w", padx=24, pady=(2, 0))
        ttk.Label(dnd_row, text=T("Pendant un jeu :"), style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.defer_var = tk.StringVar(value=ctx.cfg["reminders"]["defer"])
        ttk.Radiobutton(dnd_row, text=T("Attendre la fin, puis me rappeler"),
                        value="wait", variable=self.defer_var).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(dnd_row, text=T("Rien afficher, juste faire clignoter TidyDeck"),
                        value="flash", variable=self.defer_var).pack(side="left")
        self.auto_detect_var = tk.BooleanVar(value=bool(ctx.cfg["reminders"].get("auto_detect", False)))
        ttk.Checkbutton(dnd_row, text=T("Détecter le jeu / plein écran automatiquement"),
                        variable=self.auto_detect_var).pack(side="left", padx=(16, 0))
        ttk.Label(self._dnd_box, style="Muted.TLabel", wraplength=900, justify="left",
                  text=T("Sans détection auto, seul le Mode Jeu (page Jeu) compte ; un plein écran exclusif "
                       "peut masquer le clignotement.")).pack(anchor="w", padx=24, pady=(2, 0))
        self.dnd_var.trace_add("write", lambda *a: self._dnd_state())
        self._dnd_state()

        ttk.Label(f, text=T("Son"), style="Sub.TLabel").pack(anchor="w", pady=(6, 2))
        self._check(f, "sound", "Petit carillon doux quand une action un peu longue est terminée.")
        snd_row = ttk.Frame(f)
        snd_row.pack(anchor="w", padx=24, pady=(4, 0))
        ttk.Button(snd_row, text=T("🔊 Tester le son"), command=self._test_sound).pack(side="left")
        ttk.Button(snd_row, text=T("🎵 Choisir un son perso…"), command=self._pick_sound).pack(side="left", padx=8)
        vol_row = ttk.Frame(f)
        vol_row.pack(anchor="w", padx=24, pady=(4, 0))
        ttk.Label(vol_row, text=T("Volume du carillon :")).pack(side="left")
        self.vol_var = tk.IntVar(value=int(ctx.cfg.get("sound_volume", 70)))
        VolumeBar(vol_row, ctx.theme, self.vol_var, ctx.theme["volume"],
                  on_release=self._vol_saved).pack(side="left", padx=(10, 0))
        ttk.Label(vol_row, style="Muted.TLabel",
                  text=T("0 = aucun son · lâche le curseur pour entendre le résultat")).pack(side="left", padx=(12, 0))
        self.sound_lbl = ttk.Label(f, style="Muted.TLabel", wraplength=900, justify="left")
        self.sound_lbl.pack(anchor="w", padx=24, pady=(2, 0))
        self._refresh_sound_lbl()

        ttk.Label(f, style="Muted.TLabel", justify="left",
                  text=T("Les changements s'appliquent immédiatement, pas besoin de valider.")).pack(anchor="w", pady=(10, 4))
        self.enable_live(self._do_apply)
        for v in (self.defer_var, self.auto_detect_var, self.auto, self.dnd_var):
            v.trace_add("write", self._live)

    def _refresh_sound_lbl(self):
        c = self.ctx.cfg.get("custom_sound") or ""
        self.sound_lbl.configure(text=(T("Son personnalisé : {v0}").format(v0=c)) if c else T("Son actuel : carillon doux par défaut."))

    def _vol_saved(self, _e=None):
        v = int(round(float(self.vol_var.get())))
        self.ctx.cfg["sound_volume"] = v
        config.save(self.ctx.cfg)
        sound.play(self.ctx.cfg.get("custom_sound") or None, v / 100.0)

    def _test_sound(self):
        sound.play(self.ctx.cfg.get("custom_sound") or None, self.vol_var.get() / 100.0)

    def _pick_sound(self):
        path = filedialog.askopenfilename(title="Choisis un son (fichier WAV)",
                                        filetypes=[("Son WAV", "*.wav"), ("Tous les fichiers", "*.*")])
        if path:
            self.ctx.cfg["custom_sound"] = path
            self.ctx.save()
            self._refresh_sound_lbl()
            sound.play(path, self.vol_var.get() / 100.0)

    def _dnd_state(self):
        if self.dnd_var.get():
            # Déplie : le bloc prend sa taille naturelle et pousse la suite vers le bas.
            self._dnd_slot.pack_propagate(True)
            self._dnd_box.pack(anchor="w", fill="x", padx=24, pady=(2, 0))
        else:
            # Replie : `pack_forget()` seul ne réduit PAS la hauteur demandée du parent
            # sous Tk (le trou reste). On fige donc le slot à 1 px : « Lancement
            # automatique » remonte prendre la place.
            self._dnd_box.pack_forget()
            self._dnd_slot.pack_propagate(False)
            self._dnd_slot.configure(height=1)

    def _do_apply(self, prev=None):
        prev = dict(self.ctx.cfg) if prev is None else prev
        self.ctx.cfg.update({k: v.get() for k, v in self.vars.items()})
        self.ctx.cfg["reminders"]["defer"] = self.defer_var.get()
        self.ctx.cfg["reminders"]["auto_detect"] = self.auto_detect_var.get()
        self.ctx.cfg["reminders"]["dnd_enabled"] = bool(self.dnd_var.get())
        if IS_WINDOWS and self.auto.get() != autostart.is_enabled():
            autostart.set_enabled(self.auto.get(), self.ctx.journal)
        self.on_apply(prev)
