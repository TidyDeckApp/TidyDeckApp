import tkinter as tk
from tkinter import messagebox, ttk
from Core.Health import services
from Shared.Utils.common import IS_WINDOWS, is_admin
from UI.components import Checklist, preview_dialog
from UI.restore_flow import with_restore_point
from UI.Pages.base import Page

LV = {"safe": "Désactivable sans risque", "maybe": "Selon ton usage"}
# Pas d'emojis dans les filtres : « ⚠️ » et « ✅ » se rendent en glyphes
# décalés sous Tk (le point orange devient un triangle flottant). Symboles
# texte sobres uniquement, comme partout ailleurs dans l'appli.
FILTERS = [("all", "Tous"), ("maybe", "À vérifier (selon ton usage)"),
           ("safe", "Sans risque uniquement")]


class ServicesPage(Page):
    """Coche = service ACTIF ; décoche = désactivé. Rien ne change avant « Appliquer »."""

    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Services Windows non essentiels",
                         "Coche = le service est actif ; décoche = il sera désactivé. Rien ne change avant que tu valides "
                         "l'aperçu. Les services vitaux de Windows ne sont volontairement PAS dans cette liste.")
        self.button("✔ Appliquer", self.apply, accent=True)
        self.button("↻ Actualiser (annule mes choix en attente)", lambda: self.refresh(True))
        fframe = tk.Frame(self, bg=ctx.theme["bg"])
        fframe.pack(fill="x", pady=(0, 6))
        self._filter = tk.StringVar(value="all")
        for val, txt in FILTERS:
            ttk.Radiobutton(fframe, text=txt, variable=self._filter, value=val,
                            command=self._refilter).pack(side="left", padx=(0, 14))
        self.list = Checklist(self, ctx, ("Service", "État"), on_toggle=self._toggled, box_only=True)
        self.list.pack(fill="both", expand=True)
        self.states, self.dirty, self.all_rows = {}, False, {}

    def on_show(self):
        if not self.dirty:
            self.refresh()

    def _base(self, sid):
        dis = self.states.get(sid, {}).get("mode") == "disabled"
        return ("✕ Désactivé" if dis else "✔ Actif") + " · " + LV[services.BY_ID[sid]["level"]]

    def _toggled(self, iid, new):
        self.dirty = True
        dis = self.states.get(iid, {}).get("mode") == "disabled"
        info = self._base(iid)
        if dis and new:
            info = "↩ Sera réactivé · " + LV[services.BY_ID[iid]["level"]]
        elif not dis and not new:
            info = "⏻ Sera désactivé · " + LV[services.BY_ID[iid]["level"]]
        self.list.update_row(iid, info=info)
        return True

    def refresh(self, force=False):
        self.say("Lecture des services…" if not self.ctx.cache.get("services") else "")
        self.load("services", services.read_states, self._draw, ttl=45, force=force)

    def _draw(self, states):
        if self.dirty:
            return
        self.states = states
        rows = []
        for s in services.SERVICES:
            if IS_WINDOWS and s["id"] not in states:
                continue
            dis = states.get(s["id"], {}).get("mode") == "disabled"
            rows.append(dict(id=s["id"], name=s["name"], info=self._base(s["id"]), checked=not dis,
                           level=s["level"],
                             # Emplacement verifiable : services.msc, en consultation seule.
                             # On n'ecrit rien : la console affiche juste le service.
                             shell="services.msc",
                             location=f"services.msc — service « {s['id']} »",
                             status="off" if dis else ("info" if s["level"] == "safe" else "warn"),
                             detail=f"Ce que c'est : {s['what']}\nRisque si désactivé : {s['risk']}\n\n"
                                    f"Nom technique : {s['id']} (visible dans services.msc)\n"
                                    "Modification : droits administrateur requis. Annulable (Journaux)."))
        self.all_rows = {r["id"]: r for r in rows}
        self._refilter()
        self.say("")

    def _refilter(self):
        f = self._filter.get()
        shown = list(self.all_rows.values()) if f == "all" else [r for r in self.all_rows.values() if r["level"] == f]
        self.list.set_rows(shown)

    def apply(self):
        checked = {i for i, r in self.all_rows.items() if r.get("checked")}
        off = [i for i in self.all_rows if i not in checked and self.states.get(i, {}).get("mode") != "disabled"]
        on = [i for i in self.all_rows if i in checked and self.states.get(i, {}).get("mode") == "disabled"]
        if not off and not on:
            messagebox.showinfo("TidyDeck", "Rien à changer.")
            return
        if not is_admin():
            if messagebox.askyesno("Droits administrateur", "Modifier des services demande les droits administrateur.\n\n"
                                   "Relancer TidyDeck en administrateur ?"):
                self.ctx.ask_admin(confirm=False)
            return
        lines = []
        if off:
            lines += ["⏻ À DÉSACTIVER"] + [f"• {services.BY_ID[i]['name']} — {services.BY_ID[i]['risk']}" for i in off]
        if on:
            lines += ["", "↩ À RÉACTIVER"] + [f"• {services.BY_ID[i]['name']}" for i in on]
        if not preview_dialog(self.ctx, "Aperçu : services Windows", "TidyDeck va modifier le mode de démarrage de ces services "
                              "(l'ancien mode est mémorisé) :", lines, "Annulable depuis les Journaux.", "Oui, appliquer"):
            return
        with_restore_point(self.ctx, self, lambda: self._do(off, on))

    def _do(self, off, on):
        d1, f1 = services.disable(off, self.states, self.ctx.journal) if off else ([], [])
        d2, f2 = services.restore(on, self.ctx.journal) if on else ([], [])
        fails = f1 + f2
        self.say(f"✨ {len(d1)} désactivé(s), {len(d2)} réactivé(s)." + (f" Échecs : {', '.join(i for i, _ in fails)}" if fails else ""))
        self.dirty = False
        self.ctx.cache.pop("services", None)
        self.refresh(True)
