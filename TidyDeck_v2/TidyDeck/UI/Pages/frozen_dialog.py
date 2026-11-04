import tkinter as tk
from tkinter import messagebox, ttk
from Core.Health import frozen
from UI.components import fit_window
from Shared.Utils.lang import T


def show(ctx):
    win = tk.Toplevel(ctx.root)
    win.title(T("Application bloquée ?"))
    win.configure(bg=ctx.theme["bg"])
    win.transient(ctx.root)
    ttk.Label(win, text=T("Applications qui ne répondent plus"), style="Sub.TLabel").pack(anchor="w", padx=18, pady=(16, 4))
    ttk.Label(win, wraplength=600, style="Muted.TLabel", justify="left",
              text=T("Je demande d'abord une fermeture propre. Seulement si ça ne marche pas, je peux forcer "
                     "(tu perdras ce qui n'était pas enregistré dans cette application).")).pack(anchor="w", padx=18)
    lb = tk.Listbox(win, height=8, bg=ctx.theme["card"], fg=ctx.theme["fg"], relief="flat", activestyle="none")
    lb.pack(fill="both", expand=True, padx=18, pady=10)
    items = []

    def load():
        items[:] = frozen.not_responding()
        lb.delete(0, "end")
        for it in items:
            lb.insert("end", T("  {nom}   (n° {pid})").format(nom=it['name'], pid=it['pid']))
        if not items:
            lb.insert("end", T("  ✔ Aucune application bloquée détectée."))

    def sel():
        s = lb.curselection()
        return items[s[0]] if s and items else None

    def polite():
        it = sel()
        if it:
            frozen.close(it["pid"])
            win.after(2000, load)

    def force():
        it = sel()
        if it and messagebox.askyesno("Forcer la fermeture", T("Forcer la fermeture de {nom} ? Le travail non "
                                                              "enregistré dedans sera perdu.").format(nom=it['name']), parent=win):
            frozen.close(it["pid"], force=True)
            win.after(1500, load)
    bar = ttk.Frame(win)
    bar.pack(fill="x", padx=18, pady=12)
    ttk.Button(bar, text=T("Fermer proprement"), style="Accent.TButton", command=polite).pack(side="left")
    ttk.Button(bar, text=T("Forcer"), command=force).pack(side="left", padx=8)
    ttk.Button(bar, text=T("↻"), command=load).pack(side="left")
    ttk.Button(bar, text=T("Fermer"), command=win.destroy).pack(side="right")
    load()
    fit_window(win, ctx, 640, 420)
