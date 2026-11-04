import tkinter as tk
from tkinter import ttk
from UI.components import ScrollFrame
from UI.Pages.base import Page
from UI.Profile import profile


class ProfilePage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Profils : partager ou sauvegarder ses réglages",
                         "Transfère tes préférences d'un PC à l'autre en un clin d'œil, ou conserve une copie de secours.")
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f = sf.inner

        ttk.Label(f, text="📱 Transfert rapide par QR Code", style="Sub.TLabel").pack(anchor="w", pady=(4, 2))
        ttk.Label(f, text="Idéal pour passer d'un PC à un autre rapidement.",
                  style="Muted.TLabel").pack(anchor="w")
        ttk.Label(f, wraplength=900, justify="left",
                  text="•  Ce qui est inclus : ton apparence, tes rappels, tes thèmes et tes choix « Calmer Windows »."
                  ).pack(anchor="w", pady=(8, 0))
        ttk.Label(f, wraplength=900, justify="left",
                  text="•  Ce qui reste privé (jamais partagé) : tes fichiers personnels, ton nom d'utilisateur, "
                       "tes chemins d'accès ou tes données sensibles.").pack(anchor="w", pady=(4, 0))
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=(12, 4))
        ttk.Button(row, text="📱 Générer un QR Code", style="Accent.TButton",
                   command=lambda: profile.export_qr(ctx)).pack(side="left")
        ttk.Label(f, wraplength=900, justify="left", style="Muted.TLabel",
                  text="Info rassurante : rien n'est appliqué d'office à l'import. Tu pourras inspecter et valider "
                       "chaque réglage avant qu'il ne touche à ton nouveau PC.").pack(anchor="w", pady=(2, 0))

        if ctx.cfg.get("serenity"):
            t_title = "💾 Sauvegarde de tes réglages"
            t_help = ("Pour garder une copie de secours de tes préférences sur ton PC, "
                     "ou pour les retrouver facilement plus tard.")
            t_exp, t_imp = "💾 Télécharger mes réglages", "📂 Restaurer mes réglages"
        else:
            t_title = "💾 Sauvegarde avancée (Fichier JSON)"
            t_help = ("Pour les passionnés qui préfèrent conserver un fichier de "
                     "configuration brut sur leur machine.")
            t_exp, t_imp = "💾 Exporter un fichier", "📁 Importer un fichier"
        ttk.Label(f, text=t_title, style="Sub.TLabel").pack(anchor="w", pady=(26, 2))
        ttk.Label(f, text=t_help, style="Muted.TLabel").pack(anchor="w")
        row2 = ttk.Frame(f)
        row2.pack(anchor="w", pady=(10, 4))
        ttk.Button(row2, text=t_exp,
                   command=lambda: profile.export_profile(ctx)).pack(side="left", padx=(0, 8))
        ttk.Button(row2, text=t_imp,
                   command=lambda: profile.import_profile(ctx, self._rebuild)).pack(side="left")

    def _rebuild(self):
        self.ctx.app.rebuild()
