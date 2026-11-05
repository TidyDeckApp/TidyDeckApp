import tkinter as tk
from tkinter import ttk
from Core.SystemInfo import hardware
from Shared.Utils.common import IS_WINDOWS, is_admin, APP_VERSION
from UI.components import ScrollFrame, Collapsible, disk_bar, info_note
from UI.Pages.base import Page
from Shared.Utils.lang import T, get_lang


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
            ttk.Label(self.hw, text=T("Première lecture de ton matériel… quelques secondes. "
                                  "Après, cette page s'affichera instantanément."),
                     style="Muted.TLabel").pack(anchor="w")
        # Recharge a CHAQUE affichage : le releve materiel est deja cache 12 h
        # en interne, donc ca ne coute rien, et la page ne reste pas figee sur
        # des chiffres de ce matin (les disques, eux, sont relus en direct).
        self.load("hardware", hardware.load, lambda d: self.render(d, None), ttl=120)

    def render(self, data, err):
        for w in self.hw.winfo_children():
            w.destroy()
        if err or not data:
            ttk.Label(self.hw, text=T("Je n'ai pas pu lire le matériel pour l'instant."), style="Muted.TLabel").pack(anchor="w")
            return
        adv = self.ctx.advanced
        comps, disks, phys = hardware.describe(data, adv)
        if data.get("demo"):
            ttk.Label(self.hw, text=T("(Mode démonstration : données d'exemple, tu n'es pas sous Windows)"),
                      style="Muted.TLabel").pack(anchor="w")
        self._hw_drawn = True
        for c in comps:
            line = ttk.Frame(self.hw)
            line.pack(fill="x", pady=1)
            ttk.Label(line, text=c["icon"], width=3).pack(side="left")
            # typographie : « : » prend une espace avant en francais, jamais en anglais
            sep = ": " if get_lang() == "en" else " : "
            txt = f"{c['label']}{sep}{c['summary']}"
            if adv:
                Collapsible(line, txt, c["details"]).pack(side="left")
            else:
                ttk.Label(line, text=txt).pack(side="left")
        ttk.Label(self.hw, text=T("💽  Stockage"), style="Sub.TLabel").pack(anchor="w", pady=(6, 2))
        # L'espace libre est relu EN DIRECT : le relevé matériel dort en cache 12 h,
        # et une place libérée ailleurs (nettoyage, résidus) doit se voir ici.
        for dk in disks:
            dk["free"], dk["total"] = hardware.live_disk(dk["dev"], (dk["free"], dk["total"]))
        for dk in disks:
            disk_bar(self.hw, self.ctx.theme, f"📁 {dk['dev']}", dk["free"], dk["total"],
                     dk.get("type", ""), self._games_gauge(dk['free']),
                     status=self.ctx.status_colors, serene=bool(self.ctx.cfg.get("serenity"))).pack(fill="x", pady=1)
        heavy = [dk["dev"] for dk in disks if dk["total"] and dk["free"] / dk["total"] <= 0.10]
        warm = [dk["dev"] for dk in disks if dk["total"] and 0.10 < dk["free"] / dk["total"] <= 0.25]
        if heavy:
            if self.ctx.cfg.get("serenity"):
                info_note(self.hw, self.ctx.theme, self.ctx.status_colors["info"],
                          T("Info — Peu de place restante sur {n}. Un passage dans "
                            "« Fichiers et résidus » ou le Nettoyage te fera respirer, quand tu veux.").format(n=", ".join(heavy))).pack(anchor="w", pady=(6, 0))
            else:
                ttk.Label(self.hw, style="Muted.TLabel", wraplength=900, justify="left",
                        text=T("⚠️ Presque plus de place sur {n} : moins de 10 % libres. Un passage dans "
                        "« Fichiers et résidus » ou le Nettoyage t'aiderait à respirer sans stress.").format(n=", ".join(heavy))).pack(anchor="w", pady=(6, 0))
        elif warm:
            info_note(self.hw, self.ctx.theme, self.ctx.status_colors["info"],
                      T("Info — Place bientôt basse sur {n}. Un petit tour dans "
                        "« Fichiers et résidus » t'aiderait à faire un peu de place sans stress.").format(n=", ".join(warm))).pack(anchor="w", pady=(6, 0))
        else:
            ttk.Label(self.hw, style="Muted.TLabel",
                      text=T("✅ Tes disques ont de la place partout : rien à faire pour l'instant.")).pack(anchor="w", pady=(6, 0))
        if adv and phys:
            Collapsible(self.hw, T("Santé des disques (autotest interne du disque)"), phys).pack(fill="x", pady=(4, 0))

    def _games_gauge(self, free_bytes):
        AAA_GB = 90
        n = int(free_bytes / (AAA_GB * (1 << 30)))
        if n >= 1:
            return (T("de quoi installer environ {v0} jeu AAA de {v1} Go") if n == 1
                    else T("de quoi installer environ {v0} jeux AAA de {v1} Go")).format(v0=n, v1=AAA_GB)
        if free_bytes > 20 * (1 << 30):
            return T("de quoi installer un petit jeu, mais pas un gros")
        return T("très peu de place pour un jeu")
