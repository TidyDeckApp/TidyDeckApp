import tkinter as tk
from tkinter import messagebox, ttk
from Core.Debloat import debloat
from Shared.Utils.common import IS_WINDOWS, is_admin
from UI.components import Checklist, FlowFrame, preview_dialog, info_note, auto_wrap
from Core.Tweaks import tweaks
from UI.restore_flow import with_restore_point
from UI.Pages.base import Page
from Shared.Utils.lang import T


class DebloatPage(Page):
    """Désinstallation des appli préinstallées. Réservé au mode avancé."""

    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Applications préinstallées",
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
        self.button(T("✔ Appliquer"), self.apply, accent=True)
        self.button("↻ Actualiser (relire les applis installées)", lambda: self.refresh(True))

        info_frame = tk.Frame(self, bg=ctx.theme["card"], highlightbackground=ctx.theme["line"], highlightthickness=1)
        info_frame.pack(fill="x", pady=(0, 8))
        info_note(info_frame, ctx.theme, ctx.status_colors["info"], "Ce que tu désinstalles :",
                 bold=True, bg=ctx.theme["card"]).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(info_frame, wraplength=850, justify="left", font=("Segoe UI", 9),
                 bg=ctx.theme["card"], fg=ctx.theme["muted"], text=T(
            "• Seules les applis réellement installées sur ta machine apparaissent ici.\n"
            "• Les applis tierces sponsorisées (Candy Crush, Spotify, Netflix, TikTok, Disney+, Prime Video,\n"
            "  Facebook, Instagram, LinkedIn) ont des identifiants qui changent selon la région : elles sont\n"
            "  détectées par mot-clé sur les applis installées, jamais codées en dur.\n"
            "• Les composants essentiels de Windows sont protégés et ne figurent pas dans la liste.\n"
            "• Un point de restauration est tenté avant (Windows demande les droits administrateur). Réinstallable depuis le Microsoft Store.")).pack(
            anchor="w", padx=12, pady=(0, 8))

        self.list = Checklist(self, ctx, ("Application", T("Applications concernées")), checkable=True, box_only=True)
        self.list.pack(fill="both", expand=True)

    def on_show(self):
        if not self.ctx.cache.get("debloat"):
            self.refresh()

    def refresh(self, force=False):
        self._refresh_silent_note()
        self.say("Lecture des applis installées…" if not self.ctx.cache.get("debloat") else "")
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
                text=T("Déjà fait : Windows n'installera plus automatiquement ces applications "
                     "partenaires, ce que tu retires ne reviendra pas."))
        else:
            self.silent_lbl.configure(
                text=T("Avant de retirer des applis, active « Empêcher l'installation automatique "
                     "d'applis sponsorisées » dans Calmer Windows : sinon Windows peut les réinstaller."))

    def _p(self, n, sing, plur):
        return f"{n} {sing if n == 1 else plur}"

    def _draw(self, groups):
        self.groups = groups or []
        rows = []
        for i, g in enumerate(self.groups):
            pkgs = g["packages"]
            kind = T("appli tierce sponsorisée") if g["kind"] == "tierce" else T("appli Microsoft préinstallée")
            rows.append(dict(
                id=str(i), name=T(g["label"]),
                info=self._p(len(pkgs), T("appli concernée"), T("applis concernées")), checked=False,
                status="warn" if g["kind"] == "tierce" else "info",
                detail=(T("Ce que c'est : {v0}.\n\n"
                        "Nom technique : {v1}\n\n"
                        "Action : désinstallation pour ton compte d'utilisateur "
                        "(pas pour les autres comptes de la machine).\n"
                        "Risque : faible. Tout se réinstalle depuis le Microsoft Store si tu le veux plus tard.\n"
                        "Un point de restauration est tenté avant l'action (les droits administrateur sont demandés).").format(v0=kind, v1=', '.join(pkgs)))))
        self.list.set_rows(rows)
        if not rows:
            self.say(T("Aucune des appli connues n'est installée sur ce PC. Rien à débloat. ✔"))
        else:
            n = sum(len(g["packages"]) for g in self.groups)
            self.say(T("{g}, {p}. "
                     "Coche ce que tu veux retirer, puis « Appliquer ».").format(g=self._p(len(rows), T("groupe reconnu"), T("groupes reconnus")), p=self._p(n, T("appli à retirer"), T("applis à retirer"))))

    def apply(self):
        ids = self.list.checked_ids()
        if not ids:
            messagebox.showinfo("TidyDeck", T("Coche d'abord les appli à désinstaller."))
            return
        if not IS_WINDOWS:
            messagebox.showinfo("TidyDeck", T("Le débloat ne concerne que Windows."))
            return
        sel = [self.groups[int(i)] for i in ids]
        pkgs = [p for g in sel for p in g["packages"]]
        lines = []
        for g in sel:
            lines.append(f"• {T(g['label'])}")
            for p in g["packages"]:
                lines.append(f"    {p}")
        if not preview_dialog(self.ctx, T("Aperçu : désinstallation"),
                              self._p(len(pkgs), T("appli va être retirée"), T("applis vont être retirées")) + T(" pour ton compte :"),
                              lines, T("Réinstallable depuis le Microsoft Store."), T("Oui, désinstaller")):
            return
        with_restore_point(self.ctx, self, lambda: self._do(pkgs))

    def _do(self, pkgs):
        self.busy(T("Désinstallation"), "debloat")
        ok, ko = [], []
        for p in pkgs:
            good, msg = debloat.uninstall(p)
            (ok if good else ko).append((p, msg))
        self.idle()
        if ok:
            self.ctx.journal.add("debloat", T("Désinstallé : {v0}").format(v0=', '.join(p for p, _ in ok)),
                                details=self._p(len(ok), T("appli retirée du compte"), T("applis retirées du compte")),
                                meta={"packages": [p for p, _ in ok]})
        msg = "✨ " + self._p(len(ok), T("appli désinstallée"), T("applis désinstallées")) + "."
        if ko:
            msg += T(" {v0} en échec : ").format(v0=len(ko)) + ", ".join(f"{p} ({m})" for p, m in ko[:3])
        self.say(msg)
        self.ctx.cache.pop("debloat", None)
        self.refresh(True)
