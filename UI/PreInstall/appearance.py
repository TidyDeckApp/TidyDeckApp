"""Réglages d'accessibilité et de comportement."""
import tkinter as tk
from tkinter import ttk
from Shared.Utils.common import IS_WINDOWS
from Shared.Utils.lang import T, nom_langue


class AppearancePanel(ttk.Frame):
    def __init__(self, master, cfg, on_apply, button_text="Appliquer"):
        super().__init__(master, padding=8)
        self.cfg, self.on_apply = cfg, on_apply
        self.vars = {
            "theme": tk.StringVar(value=cfg["theme"]), "text_size": tk.StringVar(value=cfg["text_size"]),
            "lang": tk.StringVar(value=cfg.get("lang", "fr")),
            "colorblind": tk.BooleanVar(value=cfg["colorblind"]), "advanced": tk.BooleanVar(value=cfg["advanced"]),
            "serenity": tk.BooleanVar(value=cfg["serenity"]), "close_action": tk.StringVar(value=cfg["close_action"]),
            "sound": tk.BooleanVar(value=cfg["sound"]), "reminder": tk.BooleanVar(value=cfg["reminder"]),
            "stream_mode": tk.BooleanVar(value=cfg["stream_mode"]),
        }
        self._group("Langue", "lang", [(nom_langue("fr"), "fr"), (nom_langue("en"), "en")])
        self._group("Thème", "theme", [("Clair", "clair"), ("Sombre", "sombre")])
        self._group("Taille du texte", "text_size", [("Normale", "normale"), ("Grande", "grande")])
        ttk.Label(self, text=T("Confort"), style="Sub.TLabel").pack(anchor="w", pady=(10, 2))
        for key, text in [
                ("colorblind", "Mode daltonien (bleu / orange). Les états ont toujours un symbole et un mot en plus de la couleur."),
                ("serenity", "Mode Sérénité : des mots rassurants à la place des chiffres et des couleurs d'alerte. "
                            "Pensé pour le TDAH, utile à tous ceux qui se sentent vite submergés."),
                ("advanced", "Mode avancé : plus de détails (composants dépliables, toutes les options de nettoyage). "
                            "Débloque des options sensibles (Corbeille, fichiers Windows). Chacune demande une confirmation."),
                ("sound", "Petit carillon doux quand une action un peu longue est terminée."),
                ("reminder", "Rappel doux, une fois par mois au maximum, pour penser à un petit nettoyage."),
                ("stream_mode", "🕶️ Mode Discret : masque ton nom d'utilisateur, le nom du PC et tes chemins personnels à l'écran "
                                "(et propose de couper les notifications Windows). Ne masque que ce que TidyDeck affiche — pas les "
                                "autres applications. Sortie en un clic depuis la bannière.")]:
            st = ttk.Style()
            bg, fg = st.lookup("TFrame", "background"), st.lookup("TLabel", "foreground")
            tk.Checkbutton(self, text=T(text), variable=self.vars[key], wraplength=820, justify="left", anchor="w",
                           bg=bg, fg=fg, activebackground=bg, activeforeground=fg, selectcolor=st.lookup("TEntry", "fieldbackground"),
                           highlightthickness=0, bd=0).pack(anchor="w", pady=(7, 3))
        _close_opts = [("Fermer TidyDeck", "quit"), ("Réduire dans la barre des tâches", "minimize")]
        if IS_WINDOWS:
            _close_opts.append(("Réduire à côté de l'horloge (zone de notification)", "tray"))
        self._group("Quand je clique sur la croix de la fenêtre", "close_action", _close_opts)
        ttk.Button(self, text=T(button_text), style="Accent.TButton", command=self._apply).pack(anchor="w", pady=14)

    def _group(self, title, key, options):
        from UI.components import RadiOpt
        ttk.Label(self, text=T(title), style="Sub.TLabel").pack(anchor="w", pady=(10, 2))
        row = ttk.Frame(self)
        row.pack(anchor="w")
        for text, val in options:
            RadiOpt(row, text=T(text), value=val, variable=self.vars[key]).pack(side="left", padx=(0, 16))

    def _apply(self):
        prev = dict(self.cfg)
        self.cfg.update({k: v.get() for k, v in self.vars.items()})
        self.on_apply(prev)
