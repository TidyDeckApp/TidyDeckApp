import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk
from Shared.Utils.common import human_size, data_dir, open_in_explorer
from UI.components import Checklist
from UI.Pages.base import Page
from Shared.Utils.lang import T


def relative(ts):
    d = (date.today() - datetime.strptime(ts, T("%Y-%m-%d %H:%M:%S")).date()).days
    return T("Aujourd'hui") if d <= 0 else T("Hier") if d == 1 else T("Il y a {v0} jours").format(v0=d)


def friendly(e):
    b = (e.get("meta") or {}).get("bytes")
    if e["kind"] == "pairs" and b:
        return T("🧹 {v0} mis de côté — ton PC respire mieux").format(v0=human_size(b))
    if e["kind"] == "pairs":
        return T("📦 {v0} — c'est rangé").format(v0=e['title'])
    if e["kind"] == "tweaks":
        return T("🔕 Windows est plus calme")
    if e["kind"] == "startup":
        return "🚀 " + e["title"].replace(T("Démarrage : "), T("Démarrage — "))
    return "✔ " + e["title"]


class JournalPage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Journaux et annulations",
                         "Tout ce que TidyDeck a fait est noté ici. Sélectionne une ligne puis « Annuler ».")
        self.button("↩ Annuler l'action sélectionnée", self.undo, accent=True)
        self.button("📂 Ouvrir dossier journal", self.open_journal_folder)
        self.button("🧹 Nettoyer le parcours", self.clear_journal)
        ttk.Label(self, text=T("Ton parcours"), style="Sub.TLabel").pack(anchor="w")
        self.timeline = tk.Text(self, height=6, wrap="word", relief="flat", padx=12, pady=8, state="disabled",
                                bg=ctx.theme["card"], fg=ctx.theme["fg"])
        self.timeline.pack(fill="x", pady=(2, 8))
        self.list = Checklist(self, ctx, (T("Détail technique"), T("Date / état")), checkable=False)
        self.list.pack(fill="both", expand=True)

    def open_journal_folder(self):
        folder = str(data_dir())
        open_in_explorer(folder)

    def clear_journal(self):
        if not self.ctx.journal.entries:
            messagebox.showinfo("TidyDeck", T("Le parcours est déjà vide."))
            return
        if not messagebox.askyesno("Nettoyer le parcours",
                                   "TidyDeck va effacer tout l'historique des actions.\n\n"
                                   "⚠ Après ça, tu ne pourras plus annuler les actions passées depuis les Journaux.\n"
                                   "Les fichiers déjà mis en quarantaine restent intacts jusqu'à leur purge normale.\n\n"
                                   "Continuer ?"):
            return
        self.ctx.journal.entries = []
        self.ctx.journal._save()
        self.refresh()
        self.say(T("✨ Parcours nettoyé. UI propre, aucune trace. 🌿"))

    def on_show(self):
        self.refresh()

    def refresh(self):
        es = list(reversed(self.ctx.journal.entries))
        txt = "\n".join(f"{relative(e['ts'])} : {friendly(e)}" + (T("  (annulé)") if e["undone"] else "") for e in es[:6]) \
            or T("Pas encore d'historique : ton premier rangement apparaîtra ici. 🌱")
        self.timeline.configure(state="normal")
        self.timeline.delete("1.0", "end")
        self.timeline.insert("1.0", txt)
        self.timeline.configure(state="disabled")
        rows = []
        for e in es:
            state = T("↩ annulée") if e["undone"] else (T("✔ annulable") if e["undo"] else T("définitive"))
            rows.append(dict(id=e["id"], name=e["title"], info=f"{e['ts']} — {state}", status="info",
                             detail=f"{e['title']}\n{e['ts']}\n\n{e['details']}\n\n"
                                    + T("État : {v0}").format(v0=state),
                             folders=[str(data_dir())]))
        self.list.set_rows(rows)

    def undo(self):
        sel = self.list.tree.selection()
        if not sel:
            messagebox.showinfo("TidyDeck", T("Sélectionne d'abord une action dans la liste du bas."))
            return
        self.say(self.ctx.journal.undo(sel[0]))
        self.refresh()
