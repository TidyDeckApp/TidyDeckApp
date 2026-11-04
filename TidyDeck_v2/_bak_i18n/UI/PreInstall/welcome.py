import tkinter as tk
from tkinter import ttk
from UI.components import fit_window, ScrollFrame
from UI.PreInstall.appearance import AppearancePanel


def show_welcome(ctx, on_done):
    win = tk.Toplevel(ctx.root)
    win.title("Bienvenue dans TidyDeck")
    win.configure(bg=ctx.theme["bg"])
    win.transient(ctx.root)
    sf = ScrollFrame(win, ctx.theme["bg"])
    sf.pack(fill="both", expand=True)
    f = sf.inner
    ttk.Label(f, text="Bienvenue 👋", style="Title.TLabel").pack(anchor="w", padx=20, pady=(18, 2))
    ttk.Label(f, wraplength=int(600 * ctx.scale), justify="left", style="Muted.TLabel",
              text="TidyDeck démarre avec toutes les options désactivées : choisis ici ton thème, "
                   "ta taille de texte et les modes qui te vont.\nRien n'est définitif — tu peux tout "
                   "changer à tout moment dans « Apparence et modes », dans le menu de gauche.").pack(anchor="w", padx=20)

    def done(*_):
        # La sélection devient la préférence : elle est enregistrée tout de suite
        # et retrouvée au prochain lancement.
        ctx.save()
        if win.winfo_exists():
            win.destroy()
        on_done()
    AppearancePanel(f, ctx.cfg, done, "C'est parti").pack(anchor="w", padx=12)
    win.protocol("WM_DELETE_WINDOW", done)
    f.update_idletasks()
    win.geometry("700x640")
    fit_window(win, ctx, 700, 640)
