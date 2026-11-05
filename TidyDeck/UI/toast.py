"""Petite bulle de rappel : en bas à droite, sans voler le focus clavier, se ferme toute seule."""
import tkinter as tk
from tkinter import ttk
from Shared.Utils import sound
from Shared.Utils.lang import T


def show_toast(ctx, title, text, countdown=0, on_snooze=None, auto_close=30):
    win = tk.Toplevel(ctx.root)
    win.overrideredirect(True)
    try:
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.97)
    except tk.TclError:
        pass
    th = ctx.theme
    outer = tk.Frame(win, bg=th["accent"], padx=2, pady=2)
    outer.pack()
    box = tk.Frame(outer, bg=th["card"], padx=18, pady=14)
    box.pack()
    tk.Label(box, text=ctx.mask(title), bg=th["card"], fg=th["fg"], font=("Segoe UI", int(12 * ctx.scale), "bold"),
             justify="left").pack(anchor="w")
    lbl = tk.Label(box, text=ctx.mask(text), bg=th["card"], fg=th["muted"], wraplength=int(340 * ctx.scale), justify="left")
    lbl.pack(anchor="w", pady=(4, 8))
    cd = tk.Label(box, text=T(""), bg=th["card"], fg=th["accent"], font=("Segoe UI", int(11 * ctx.scale), "bold"))
    if countdown:
        cd.pack(anchor="w", pady=(0, 6))
    bar = tk.Frame(box, bg=th["card"])
    bar.pack(anchor="e", fill="x")
    ttk.Button(bar, text=T("OK ✓"), style="Accent.TButton", command=win.destroy).pack(side="right")
    if on_snooze:
        ttk.Button(bar, text=T("Dans 10 min"), command=lambda: (on_snooze(), win.destroy())).pack(side="right", padx=8)
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    pos = ctx.cfg.get("toast_position", "bottom-right")
    if pos == "bottom-left":
        x, y = 24, sh - h - 80
    elif pos == "top-right":
        x, y = sw - w - 24, 80
    elif pos == "top-left":
        x, y = 24, 80
    else:
        x, y = sw - w - 24, sh - h - 80
    win.geometry(f"+{x}+{y}")
    if ctx.cfg["reminders"].get("sound", True):
        sound.chime()

    def tick(n):
        if not win.winfo_exists():
            return
        if countdown:
            if n > 0:
                cd.configure(text=f"⏳ Plus que {n} s…")
                win.after(1000, lambda: tick(n - 1))
            else:
                cd.configure(text=T("✔ C'est bon, tu peux reprendre !"))
                win.after(2500, lambda: win.winfo_exists() and win.destroy())
        else:
            if n > 0:
                win.after(1000, lambda: tick(n - 1))
            else:
                win.destroy()
    tick(countdown or auto_close)
    return win
