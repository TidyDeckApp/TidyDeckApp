import tkinter as tk
from tkinter import ttk
from UI.components import ScrollFrame
from UI.Pages.base import Page
from UI.Profile import profile
from Shared.Utils.lang import T


class ProfilePage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Sauvegarde et transfert",
                         "Transfère tes préférences d'un PC à l'autre en un clin d'œil, ou conserve une copie de secours.")
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f = sf.inner

        ttk.Label(f, text=T("📱 Transfert rapide par QR code"), style="Sub.TLabel").pack(anchor="w", pady=(4, 2))
        ttk.Label(f, wraplength=900, justify="left",
                  text=T("•  Ce qui est inclus : ton apparence, tes rappels, tes thèmes et tes choix « Calmer Windows »."
                  )).pack(anchor="w", pady=(8, 0))
        ttk.Label(f, wraplength=900, justify="left",
                  text=T("•  Ce qui reste privé (jamais partagé) : tes fichiers personnels, ton nom d'utilisateur, "
                       "tes chemins d'accès ou tes données sensibles.")).pack(anchor="w", pady=(4, 0))
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=(12, 4))
        ttk.Button(row, text=T("📱 Générer un QR code"), style="Accent.TButton",
                   command=lambda: profile.export_qr(ctx)).pack(side="left")
        ttk.Label(f, wraplength=900, justify="left", style="Muted.TLabel",
                  text=T("Info rassurante : rien n'est appliqué d'office à l'import. Tu pourras inspecter et valider "
                       "chaque réglage avant qu'il ne touche à ton nouveau PC.")).pack(anchor="w", pady=(2, 0))

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
        ttk.Label(f, text=T(t_title), style="Sub.TLabel").pack(anchor="w", pady=(26, 2))
        ttk.Label(f, text=T(t_help), style="Muted.TLabel").pack(anchor="w")
        row2 = ttk.Frame(f)
        row2.pack(anchor="w", pady=(10, 4))
        ttk.Button(row2, text=T(t_exp),
                   command=lambda: profile.export_profile(ctx)).pack(side="left", padx=(0, 8))
        ttk.Button(row2, text=T(t_imp),
                   command=lambda: profile.import_profile(ctx, self._rebuild)).pack(side="left")

    def _rebuild(self):
        self.ctx.app.rebuild()
