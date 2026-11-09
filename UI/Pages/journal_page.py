import re
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk
from Shared.Utils.common import human_size, data_dir, open_in_explorer
from Shared.Utils import lang
from UI.components import Checklist
from UI.Pages.base import Page
from Shared.Utils.lang import T


# Anciens journaux : les titres « tweaks / démarrage / services » étaient écrits en
# français à l'enregistrement, chiffres inclus. T() ne les reconnaît pas (chaînes
# dynamiques) ; on les reconnaît ici pour qu'un vieux journal reste lisible en anglais.
_TITRES_HISTORIQUES = (
    (re.compile(r"^1 réglage Windows appliqué$"), "1 Windows tweak applied"),
    (re.compile(r"^(\d+) réglages Windows appliqués$"), r"\1 Windows tweaks applied"),
    (re.compile(r"^1 réglage remis comme avant$"), "1 tweak restored to its previous state"),
    (re.compile(r"^(\d+) réglages remis comme avant$"), r"\1 tweaks restored to their previous state"),
    (re.compile(r"^Démarrage : (\d+) programme activé$"), r"Startup: \1 program enabled"),
    (re.compile(r"^Démarrage : (\d+) programmes activés$"), r"Startup: \1 programs enabled"),
    (re.compile(r"^Démarrage : (\d+) programme désactivé$"), r"Startup: \1 program disabled"),
    (re.compile(r"^Démarrage : (\d+) programmes désactivés$"), r"Startup: \1 programs disabled"),
    (re.compile(r"^1 service Windows désactivé$"), "1 Windows service disabled"),
    (re.compile(r"^(\d+) services Windows désactivés$"), r"\1 Windows services disabled"),
    (re.compile(r"^1 service Windows remis comme avant$"), "1 Windows service restored"),
    (re.compile(r"^(\d+) services Windows remis comme avant$"), r"\1 Windows services restored"),
)


def titre_journal(titre):
    """Titre de journal en anglais si la langue l'exige, même s'il a été écrit en français."""
    out = T(titre)
    if out != titre or lang.get_lang() == "fr":
        return out
    for motif, anglais in _TITRES_HISTORIQUES:
        out, n = motif.subn(anglais, titre)
        if n:
            return out
    return titre


def relative(ts):
    d = (date.today() - datetime.strptime(ts, T("%Y-%m-%d %H:%M:%S")).date()).days
    return T("Aujourd'hui") if d <= 0 else T("Hier") if d == 1 else T("Il y a {v0} jours").format(v0=d)


_PHRASE_NETTOYAGE = ("Nettoyage : {v0} mis de côté · {v1} ignorés (utilisés) · "
                     "Corbeille vidée (définitif) : {v2} · Éléments : {v3}")
# Détail de nettoyage écrit avant la version « données seules » : phrase française
# collee dans le journal. On la reconstitue dans la langue courante.
_LEGACY_NETTOYAGE = re.compile(
    r"^Mis en quarantaine : (\d+) élément[s]?\. Ignorés \(utilisés\) : (\d+)\. "
    r"Corbeille vidée \(définitif\) : (\d+) o\. Éléments : (.+)$")
_LEGACY_FICHIERS = (
    (re.compile(r"^(\d+) fichier déplacé\.$"), r"\1 file moved."),
    (re.compile(r"^(\d+) fichiers déplacés\.$"), r"\1 files moved."),
    (re.compile(r"^(\d+) fichier mis en quarantaine\.$"), r"\1 file quarantined."),
    (re.compile(r"^(\d+) fichiers mis en quarantaine\.$"), r"\1 files quarantined."),
)


def phrase_nettoyage(c):
    return T(_PHRASE_NETTOYAGE).format(
        v0=c["q"], v1=c["skip"], v2=human_size(c["recyc"]),
        v3=", ".join(T(n) for n in c["items"]))


def detail_journal(e):
    """Texte du détail dans la langue courante, même si l'entrée a été écrite dans l'autre."""
    c = (e.get("meta") or {}).get("clean")
    if c:
        return phrase_nettoyage(c)
    brut = e.get("details") or ""
    if lang.get_lang() == "fr":
        return brut
    m = _LEGACY_NETTOYAGE.match(brut)
    if m:
        return phrase_nettoyage({"q": int(m.group(1)), "skip": int(m.group(2)),
                                 "recyc": int(m.group(3)),
                                 "items": [s.strip() for s in m.group(4).split(",")]})
    for motif, anglais in _LEGACY_FICHIERS:
        out, n = motif.subn(anglais, brut)
        if n:
            return out
    return T(brut) if brut else brut


def friendly(e):
    b = (e.get("meta") or {}).get("bytes")
    if e["kind"] == "pairs" and b:
        return T("🧹 {v0} mis de côté — ton PC respire mieux").format(v0=human_size(b))
    if e["kind"] == "pairs":
        return T("📦 {v0} — c'est rangé").format(v0=titre_journal(e['title']))
    if e["kind"] == "tweaks":
        return T("🔕 Windows est plus calme")
    if e["kind"] == "startup":
        return "🚀 " + titre_journal(e["title"]).replace(T("Démarrage : "), T("Démarrage — "))
    return "✔ " + titre_journal(e["title"])


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
        self.list = Checklist(self, ctx, (T("Action"), T("Date / état")), checkable=False)
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
        sep = " : " if lang.get_lang() == "fr" else ": "
        txt = "\n".join(f"{relative(e['ts'])}{sep}{friendly(e)}" + (T("  (annulé)") if e["undone"] else "") for e in es[:6]) \
            or T("Pas encore d'historique : ton premier rangement apparaîtra ici. 🌱")
        self.timeline.configure(state="normal")
        self.timeline.delete("1.0", "end")
        self.timeline.insert("1.0", txt)
        self.timeline.configure(state="disabled")
        rows = []
        for e in es:
            state = T("↩ annulée") if e["undone"] else (T("✔ annulable") if e["undo"] else T("définitive"))
            rows.append(dict(id=e["id"], name=titre_journal(e["title"]), info=f"{e['ts']} — {state}", status="info",
                             detail=f"{titre_journal(e['title'])}\n{e['ts']}\n\n{detail_journal(e)}\n\n"
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
