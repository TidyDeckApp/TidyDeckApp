import tkinter as tk
from tkinter import ttk
from Core.SystemInfo import hardware
from Shared.Utils.common import IS_WINDOWS, is_admin, APP_VERSION
from UI.components import ScrollFrame, Collapsible, disk_bar, info_note
from UI.Pages.base import Page


class InfoPCPage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Info PC",
                         "Les détails techniques de ta machine : processeur, RAM, carte graphique, disques.")
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f = sf.inner
        self.hw = ttk.Frame(f)
        self.hw.pack(fill="x")
        self._hw_drawn = False

    def on_show(self):
        # L'attente annoncee une seule fois : apres, la donnee est en cache.
        if not self._hw_drawn and not hardware.est_chaud():
            ttk.Label(self.hw, text="Première lecture de ton matériel… quelques secondes. "
                                  "Après, cette page s'affichera instantanément.",
                     style="Muted.TLabel").pack(anchor="w")
        # Recharge a CHAQUE affichage : le releve materiel est deja cache 12 h
        # en interne, donc ca ne coute rien, et la page ne reste pas figee sur
        # des chiffres de ce matin (les disques, eux, sont relus en direct).
        self.load("hardware", hardware.load, lambda d: self.render(d, None), ttl=120)

    def render(self, data, err):
        for w in self.hw.winfo_children():
            w.destroy()
        if err or not data:
            ttk.Label(self.hw, text="Je n'ai pas pu lire le matériel pour l'instant.", style="Muted.TLabel").pack(anchor="w")
            return
        adv = self.ctx.advanced
        comps, disks, phys = hardware.describe(data, adv)
        if data.get("demo"):
            ttk.Label(self.hw, text="(Mode démonstration : données d'exemple, tu n'es pas sous Windows)",
                      style="Muted.TLabel").pack(anchor="w")
        self._hw_drawn = True
        for c in comps:
            line = ttk.Frame(self.hw)
            line.pack(fill="x", pady=1)
            ttk.Label(line, text=c["icon"], width=3).pack(side="left")
            txt = f"{c['label']} : {c['summary']}"
            if adv:
                Collapsible(line, txt, c["details"]).pack(side="left")
            else:
                ttk.Label(line, text=txt).pack(side="left")
        ttk.Label(self.hw, text="💽  Stockage", style="Sub.TLabel").pack(anchor="w", pady=(6, 2))
        # L'espace libre est relu EN DIRECT : le relevé matériel dort en cache 12 h,
        # et une place libérée ailleurs (nettoyage, résidus) doit se voir ici.
        for dk in disks:
            dk["free"], dk["total"] = hardware.live_disk(dk["dev"], (dk["free"], dk["total"]))
        for dk in disks:
            disk_bar(self.hw, self.ctx.theme, f"📁 {dk['dev']}", dk["free"], dk["total"],
                     dk.get("type", ""), f"de quoi installer {self._games_gauge(dk['free'])}",
                     status=self.ctx.status_colors, serene=bool(self.ctx.cfg.get("serenity"))).pack(fill="x", pady=1)
        heavy = [dk["dev"] for dk in disks if dk["total"] and dk["free"] / dk["total"] <= 0.10]
        warm = [dk["dev"] for dk in disks if dk["total"] and 0.10 < dk["free"] / dk["total"] <= 0.25]
        if heavy:
            if self.ctx.cfg.get("serenity"):
                info_note(self.hw, self.ctx.theme, self.ctx.status_colors["info"],
                          "Info — " + ", ".join(heavy) + " sont bien pleins. Un passage dans "
                          "« Fichiers & Résidus » ou le Nettoyage leur donnera de l'air, quand tu veux.").pack(anchor="w", pady=(6, 0))
            else:
                ttk.Label(self.hw, style="Muted.TLabel", wraplength=900, justify="left",
                        text="⚠️ " + ", ".join(heavy) + " : presque plein(s), moins de 10 % libres. Un passage dans "
                        "« Fichiers & Résidus » ou le Nettoyage t'aiderait à respirer sans stress.").pack(anchor="w", pady=(6, 0))
        elif warm:
            info_note(self.hw, self.ctx.theme, self.ctx.status_colors["info"],
                      "Info — " + ", ".join(warm) + " commence(nt) à être bien chargé(s). Un petit tour dans l'onglet "
                      "« Fichiers & Résidus » t'aiderait à faire un peu de place sans stress.").pack(anchor="w", pady=(6, 0))
        else:
            ttk.Label(self.hw, style="Muted.TLabel",
                      text="✅ Tes disques ont de la place partout : rien à faire pour l'instant.").pack(anchor="w", pady=(6, 0))
        if adv and phys:
            Collapsible(self.hw, "Santé des disques (autotest interne du disque)", phys).pack(fill="x", pady=(4, 0))

    def _games_gauge(self, free_bytes):
        AAA_GB = 90
        n = int(free_bytes / (AAA_GB * (1 << 30)))
        if n >= 1:
            return f"environ {n} jeu{'x' if n > 1 else ''} Triple A de {AAA_GB} Go"
        return "de quoi installer un petit jeu, mais pas un gros" if free_bytes > 20 * (1 << 30) else "très peu de place pour un jeu"
