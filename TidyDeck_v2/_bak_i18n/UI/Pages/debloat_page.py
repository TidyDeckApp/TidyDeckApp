import tkinter as tk
from tkinter import messagebox, ttk
from Core.Debloat import debloat
from Shared.Utils.common import IS_WINDOWS, is_admin
from UI.components import Checklist, FlowFrame, preview_dialog, info_note, auto_wrap
from Core.Tweaks import tweaks
from UI.restore_flow import with_restore_point
from UI.Pages.base import Page


class DebloatPage(Page):
    """Désinstallation des appli préinstallées. Réservé au mode avancé."""

    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Applis préinstallées",
                         "Désinstalle les applications préinstallées inutiles. "
                         "(Mode avancé uniquement — rien n'est supprimé avant que tu valides l'aperçu.)")
        self.groups = []
        # Lien avec « Calmer Windows » : sans ce réglage, Windows peut réinstaller
        # les applis sponsorisées qu'on vient juste de retirer.
        self.silent_lbl = auto_wrap(ttk.Label(self, style="Muted.TLabel", justify="left"))
        self.silent_lbl.pack(anchor="w", fill="x", pady=(2, 6))
        self._refresh_silent_note()
        self.bar.destroy()
        self.bar = FlowFrame(self)
        self.bar.pack(fill="x", pady=(0, 8))
        self.button("✔ Appliquer", self.apply, accent=True)
        self.button("↻ Actualiser (relire les paquets installés)", lambda: self.refresh(True))

        info_frame = tk.Frame(self, bg=ctx.theme["card"], highlightbackground=ctx.theme["line"], highlightthickness=1)
        info_frame.pack(fill="x", pady=(0, 8))
        info_note(info_frame, ctx.theme, ctx.status_colors["info"], "Ce que tu désinstalles :",
                 bold=True, bg=ctx.theme["card"]).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(info_frame, wraplength=850, justify="left", font=("Segoe UI", 9),
                 bg=ctx.theme["card"], fg=ctx.theme["muted"], text=(
            "• Seules les appli réellement installées sur TA machine apparaissent ici.\n"
            "• Les applis tierces sponsorisées (Candy Crush, Spotify, Netflix, TikTok, Disney+, Prime Video,\n"
            "  Facebook, Instagram, LinkedIn) ont des identifiants qui changent selon la région : elles sont\n"
            "  détectées par mot-clé sur les paquets installés, jamais codées en dur.\n"
            "• Les composants essentiels de Windows sont protégés et ne figurent pas dans la liste.\n"
            "• Un point de restauration est créé avant. Réinstallable depuis le Microsoft Store.")).pack(
            anchor="w", padx=12, pady=(0, 8))

        self.list = Checklist(self, ctx, ("Application", "Paquets concernés"), checkable=True, box_only=True)
        self.list.pack(fill="both", expand=True)

    def on_show(self):
        if not self.ctx.cache.get("debloat"):
            self.refresh()

    def refresh(self, force=False):
        self._refresh_silent_note()
        self.say("Lecture des paquets installés…" if not self.ctx.cache.get("debloat") else "")
        self.load("debloat", debloat.scan, self._draw, ttl=120, force=force)

    def _refresh_silent_note(self):
        """Rappelle le lien avec « Calmer Windows » : le réglage silent_apps est ce
        qui empêche Windows de remettre les applis sponsorisées après retrait.
        En cas de doute (lecture impossible) on affiche l'avertissement."""
        try:
            done = tweaks.is_active(tweaks.BY_ID["silent_apps"])
        except Exception:
            done = False
        if done:
            self.silent_lbl.configure(
                text="Déjà fait : Windows n'installera plus automatiquement ces applications "
                     "partenaires, ce que tu retires ne reviendra pas.")
        else:
            self.silent_lbl.configure(
                text="Avant de retirer des applis, active « Empêcher l'installation automatique "
                     "d'applis sponsorisées » dans Calmer Windows : sinon Windows peut les réinstaller.")

    def _draw(self, groups):
        self.groups = groups or []
        rows = []
        for i, g in enumerate(self.groups):
            pkgs = g["packages"]
            kind = "appli tierce sponsorisée" if g["kind"] == "tierce" else "appli Microsoft préinstallée"
            rows.append(dict(
                id=str(i), name=g["label"],
                info=f"{len(pkgs)} paquet(s)", checked=False,
                status="warn" if g["kind"] == "tierce" else "info",
                detail=(f"Ce que c'est : {kind}.\n\n"
                        f"Paquet(s) : {', '.join(pkgs)}\n\n"
                        "Action : désinstallation pour TON compte d'utilisateur "
                        "(pas pour les autres comptes de la machine).\n"
                        "Risque : faible. Tout se réinstalle depuis le Microsoft Store si tu le veux plus tard.\n"
                        "Un point de restauration est créé avant l'action.")))
        self.list.set_rows(rows)
        if not rows:
            self.say("Aucune des appli connues n'est installée sur ce PC. Rien à débloat. ✔")
        else:
            n = sum(len(g["packages"]) for g in self.groups)
            self.say(f"{len(rows)} groupe(s) reconnus, {n} paquet(s) désinstallables. "
                     "Coche ce que tu veux retirer, puis « Appliquer ».")

    def apply(self):
        ids = self.list.checked_ids()
        if not ids:
            messagebox.showinfo("TidyDeck", "Coche d'abord les appli à désinstaller.")
            return
        if not IS_WINDOWS:
            messagebox.showinfo("TidyDeck", "Le débloat ne concerne que Windows.")
            return
        sel = [self.groups[int(i)] for i in ids]
        pkgs = [p for g in sel for p in g["packages"]]
        lines = []
        for g in sel:
            lines.append(f"• {g['label']}")
            for p in g["packages"]:
                lines.append(f"    {p}")
        if not preview_dialog(self.ctx, "Aperçu : désinstallation",
                              f"{len(pkgs)} paquet(s) vont être désinstallés pour ton compte :",
                              lines, "Réinstallable depuis le Microsoft Store.", "Oui, désinstaller"):
            return
        with_restore_point(self.ctx, self, lambda: self._do(pkgs))

    def _do(self, pkgs):
        self.busy("Désinstallation", "debloat")
        ok, ko = [], []
        for p in pkgs:
            good, msg = debloat.uninstall(p)
            (ok if good else ko).append((p, msg))
        self.idle()
        if ok:
            self.ctx.journal.add("debloat", f"Désinstallé : {', '.join(p for p, _ in ok)}",
                                details=f"{len(ok)} paquet(s) retirés du compte",
                                meta={"packages": [p for p, _ in ok]})
        msg = f"✨ {len(ok)} paquet(s) désinstallé(s)."
        if ko:
            msg += f" {len(ko)} en échec : " + ", ".join(f"{p} ({m})" for p, m in ko[:3])
        self.say(msg)
        self.ctx.cache.pop("debloat", None)
        self.refresh(True)
