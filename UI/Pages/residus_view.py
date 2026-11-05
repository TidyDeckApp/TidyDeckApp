"""Vue « Résidus d'applications » (Phase 0 : lecture seule).

Liste les dossiers laissés par des programmes désinstallés. Rien n'est
déplacé, rien n'est supprimé, rien n'est écrit : la mise en quarantaine
n'arrivera qu'en Phase 1, après validation sur de vraies machines.
Elle vit DANS la page « Fichiers et résidus » et n'existe qu'en mode Avancé.
Même design que « Fichiers oubliés » : tableau « Dossier / Détail » et
panneau du bas qui explique la ligne sélectionnée, bouton
« Ouvrir l'emplacement (pour vérifier) ».
"""
import threading
import time
import tkinter as tk
from tkinter import ttk

from Core.Storage import residus
from UI.components import Checklist, run_bg, auto_wrap
from UI.Pages.largest_view import calm_size
from Shared.Utils.lang import T

DUREES = (30, 90, 180)


class ResidusView(ttk.Frame):
    """Résidus probables d'applications désinstallées (lecture seule)."""

    def __init__(self, master, ctx, on_close=None, loader=None):
        super().__init__(master, padding=0)
        self.ctx = ctx
        self.on_close_cb = on_close
        self.charger = loader or self._charger
        self.cancel = threading.Event()
        self.busy = False
        self.jours = tk.IntVar(value=90)
        self.resultat = {"lignes": [], "scan_partiel": False, "non_lus": []}
        self._after = None
        self._build()
        self._after = self.after(80, self._kick)
        self.bind("<Destroy>", self._on_destroy)

    # ------------------------------------------------------------------ build
    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        # Pas de bouton « Retour » : on change d'onglet avec les boutons du haut.
        self.re_btn = ttk.Button(top, text=T("🔄 Relancer la recherche"), style="Flat.TButton",
                                 command=self.start)
        self.re_btn.pack(side="right")
        self.stop_btn = ttk.Button(top, text=T("Arrêter"), style="Flat.TButton", command=self.cancel.set)

        self.intro_lbl = auto_wrap(ttk.Label(self, style="Muted.TLabel", justify="left"))
        self.intro_lbl.pack(anchor="w", fill="x", pady=(4, 0))
        # Barre de chargement plutôt qu'un texte « recherche en cours » : le scan
        # peut durer, la barre rassure sans répéter ce qui est déjà écrit plus haut.
        self.busy_bar = ttk.Progressbar(self, mode="indeterminate", length=260)
        self._set_intro()

        opts = ttk.Frame(self)
        opts.pack(anchor="w", fill="x", pady=(2, 0))
        ttk.Label(opts, text=T("Dossiers sans activité depuis :"), style="Muted.TLabel").pack(side="left")
        for v in DUREES:
            ttk.Radiobutton(opts, text=T("{v0} jours").format(v0=v), value=v, variable=self.jours,
                            command=self.start).pack(side="left", padx=(6, 0))

        # Même design que « Fichiers oubliés » : tableau + panneau de détail.
        self.list = Checklist(self, self.ctx, (T("Dossier"), T("Taille · Confiance")),
                              checkable=False)
        self.list.tree_min_rows = 4
        self.list.pack(fill="both", expand=True, pady=(4, 0))

        self.foot = auto_wrap(ttk.Label(self, style="Muted.TLabel", justify="left"))
        self.foot.pack(anchor="w", fill="x", pady=(6, 0))

    def _set_intro(self, txt=None):
        if txt is None:
            txt = T("Dossiers laissés par des logiciels qui ne semblent plus installés.")
        self.intro_lbl.configure(text=txt)

    def _kick(self):
        self._after = None
        if self.winfo_exists():
            self.start()

    def _on_destroy(self, e):
        if e.widget is not self:
            return
        self.cancel.set()
        try:
            self.busy_bar.stop()
        except Exception:
            pass
        if self._after is not None:
            try:
                self.after_cancel(self._after)
            except Exception:
                pass
            self._after = None

    # ------------------------------------------------------------------ scan
    def _charger(self, jours, cancel):
        return residus.analyse(jours=jours, cancel=cancel,
                               processus=residus.processus_actifs())

    def start(self):
        if self.busy:
            return
        self.busy = True
        self.cancel.clear()
        self.stop_btn.pack(side="right", padx=(8, 0))
        self.re_btn.state(["disabled"])
        self.busy_bar.pack(after=self.intro_lbl, anchor="w", pady=(6, 0))
        self.busy_bar.start(12)
        jours = int(self.jours.get())
        run_bg(self.ctx.root, lambda: self.charger(jours, self.cancel.is_set), self._done)

    def _done(self, res, err):
        self.busy = False
        try:
            self.busy_bar.stop()
            self.busy_bar.pack_forget()
            self.stop_btn.pack_forget()
            self.re_btn.state(["!disabled"])
        except tk.TclError:
            return
        if err is not None:
            self._set_intro(T("La recherche n'a pas pu aboutir : {v0}. Rien n'a été modifié.").format(v0=err))
            return
        self.resultat = res or self.resultat
        self._set_intro()
        self._render()

    def close(self):
        self.cancel.set()
        if self.on_close_cb:
            self.on_close_cb()

    # ---------------------------------------------------------------- render
    def _render(self):
        if self.resultat.get("installs_illisibles"):
            # Garde-fou : sans liste des logiciels installés, on ne peut rien dire.
            self._set_intro(T("Je n'ai pas pu lire la liste des logiciels installés, "
                            "donc je ne propose rien."))
            self.list.set_rows([])
            self.foot.configure(text=T(""))
            return
        lignes = self.resultat.get("lignes", [])
        self.list.set_rows([self._row(r, i) for i, r in enumerate(lignes)])
        if lignes:
            parts = [T("1 résidu proposé") if len(lignes) == 1 else T("{v0} résidus proposés").format(v0=len(lignes))]
            if self.resultat.get("scan_partiel"):
                parts.append(T("certains dossiers n'ont pas pu être vérifiés"))
            if self.resultat.get("non_lus"):
                n = len(self.resultat["non_lus"])
                parts.append("1 dossier non lu" if n == 1 else f"{n} dossiers non lus")
        else:
            parts = [T("Aucun résidu probable trouvé. Soit tout est propre, "
                     "soit les durées choisies sont trop courtes.")]
        parts.append(T("Un dossier proposé n'est pas forcément inutile : vérifie avant."))
        self.foot.configure(text=T(" · ").join(parts))

    def _row(self, r, i):
        symbole, mot = ("✔", T("Élevée")) if r["confiance"] == T("Élevée") else ("~", T("Moyenne"))
        date = time.strftime(T("%d/%m/%Y"), time.localtime(time.time() - r["age_jours"] * 86400))
        detail = (T("Dans {v0}\n"
                  "Chemin : {v1}\n"
                  "Pourquoi : {v2}\n"
                  "Confiance {v3} {v4} · Dernière activité : {v5} jours "
                  "(le {v6})\n\n"
                  "TidyDeck ne fait que te le montrer : rien ne sera déplacé ni supprimé. "
                  "Ouvre l'emplacement pour vérifier avant d'en conclure quoi que ce soit.").format(v0=r['zone'], v1=r['chemin'], v2=r['motif'], v3=symbole, v4=mot, v5=r['age_jours'], v6=date))
        return dict(id=str(i), name=r["nom"],
                    info=f"{calm_size(r['taille'])} · {symbole} {mot}",
                    status="info", folders=[r["chemin"]], detail=detail)
