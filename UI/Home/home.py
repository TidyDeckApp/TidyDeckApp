import tkinter as tk
from tkinter import ttk
from Shared.Utils.common import IS_WINDOWS, is_admin
from UI.components import ScrollFrame, auto_wrap, run_bg, Collapsible
from UI.Pages.base import Page
from UI import routine
from Shared.Utils.lang import T


class HomePage(Page):
    def __init__(self, master, ctx, goto):
        super().__init__(master, ctx, "Bienvenue sur TidyDeck",
                         "Un coup de main pour nettoyer, ranger et calmer ton PC — sans rien casser, sans te juger.")
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f = sf.inner

        self.banner = auto_wrap(ttk.Label(f, text=T(""), justify="left", style="Sub.TLabel"))
        self.banner.pack(anchor="w", fill="x", pady=(0, 6))

        ttk.Button(f, text=T("✨  Ranger mon PC en douceur"), style="Big.TButton",
                   command=lambda: routine.gentle_clean(ctx, self, self.on_show,
                                                        express=self.express_var.get())).pack(anchor="w", pady=(4, 6))

        exp_row = ttk.Frame(f)
        exp_row.pack(anchor="w")
        self.express_var = tk.BooleanVar(value=ctx.cfg.get("express_mode", False))
        ttk.Checkbutton(exp_row, text=T("Mode express : ne me pose aucune question, fais au plus simple"),
                        variable=self.express_var, command=self._save_express).pack(side="left")
        auto_wrap(ttk.Label(f, style="Muted.TLabel", justify="left",
                  text=T("Avec le mode express, l'étape 2 saute : je range directement les fichiers sûrs "
                       "(Temp + Caches), sans aperçu ni confirmation, d'un seul trait.\nToujours annulable "
                       "pendant {j} jours depuis la page Journaux.").format(j=ctx.cfg['quarantine_days']))).pack(anchor="w", fill="x", pady=(6, 12))

        det_lines = [
            "1. J'analyse (sans rien modifier) uniquement : Fichiers Temp, Caches Navigateurs Web.",
            "2. Je te montre la liste et la place concernée : tu confirmes une seule fois (ou tu annules, et rien ne bouge).",
            T("3. Je mets ces fichiers de côté pendant {j} jours, sans les supprimer tout de "
              "suite : annulable depuis la page Journaux.").format(j=ctx.cfg['quarantine_days']),
            "• Ce que je ne fais jamais ici : vider la Corbeille, toucher à un navigateur ouvert, changer le démarrage, "
            "le registre, les réglages Windows ou les services. Ces zones ne font jamais partie du rangement express.",
        ]
        det = Collapsible(f, "Ce que fait exactement ce bouton", det_lines)
        det.pack(anchor="w", fill="x", pady=(4, 8))
        if not ctx.cfg.get("serenity"):
            det.toggle()

        self.calm = ttk.Label(f, text=T(""), style="Sub.TLabel")
        self.calm.pack(anchor="w", pady=(0, 4))
        self.undo_row = ttk.Frame(f)
        self.undo_row.pack(anchor="w", pady=(0, 12))

        adm = ttk.Frame(f)
        adm.pack(anchor="w", pady=(8, 6))
        if is_admin():
            self.admin_lbl = ttk.Label(adm, text=T("🛡 Mode administrateur actif."))
        else:
            self.admin_lbl = auto_wrap(ttk.Label(adm, text=T("Mode standard actif. « Relancer en administrateur » "
                                                           "ne sert que pour certains nettoyages et les points de restauration."),
                                                justify="left"))
            self.admin_lbl.pack(anchor="w", fill="x")
            ttk.Button(adm, text=T("🛡 Relancer en administrateur"), command=ctx.ask_admin).pack(anchor="w", pady=(8, 0))
        if is_admin():
            self.admin_lbl.pack(anchor="w")

    def _save_express(self):
        self.ctx.cfg["express_mode"] = self.express_var.get()
        self.ctx.save()

    def show_undo(self, pairs):
        self._undo_pairs = pairs
        if not getattr(self, "_undo_btn", None):
            self._undo_btn = ttk.Button(self.undo_row, text=T("↩ Annuler ce rangement"), command=self._undo_last)
        self._undo_btn.pack(anchor="w")
        self._undo_btn.state(["!disabled"])
        self._undo_btn.configure(text=T("↩ Annuler ce rangement"))

    def _undo_last(self):
        from Shared.Utils import quarantine
        pairs = getattr(self, "_undo_pairs", None)
        if not pairs:
            return
        self._undo_btn.state(["disabled"])
        self._undo_btn.configure(text=T("Annulation en cours…"))

        def done(r, e):
            if e or not r:
                self._undo_btn.configure(text=T("Annulation impossible"))
                return
            ok, missing, conflict = r
            txt = (T("✓ {v0} élément remis à sa place") if ok == 1
                   else T("✓ {v0} éléments remis à leur place")).format(v0=ok)
            if missing:
                txt += (T(" — {v0} introuvable") if missing == 1
                        else T(" — {v0} introuvables")).format(v0=missing)
            if conflict:
                txt += T(" — {v0} déjà en place (ignorés)").format(v0=conflict)
            self._undo_btn.configure(text=txt)
        run_bg(self.ctx.root, lambda: quarantine.restore(pairs), done)

    def on_show(self):
        lc = self.ctx.cfg.get("last_calm")
        if lc:
            self.calm.configure(style="Sub.TLabel", text=T("🌿 PC apaisé ✓ — dernier rangement : {v0}").format(v0=self._relative(lc).lower()))
        else:
            self.calm.configure(style="Muted.TLabel", text=T("Aucun rangement pour l'instant."))

    def _relative(self, ts):
        from datetime import date, datetime
        d = (date.today() - datetime.strptime(ts, T("%Y-%m-%d %H:%M:%S")).date()).days
        return T("Aujourd'hui") if d <= 0 else T("Hier") if d == 1 else T("Il y a {v0} jours").format(v0=d)
