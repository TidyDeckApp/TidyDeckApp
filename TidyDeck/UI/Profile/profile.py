"""Export / import de profil — avec QR code pour un transfert simple et rapide.
La bibliothèque qrcode est embarquée dans vendor/ : aucune installation n'est nécessaire."""
import base64
import json
import os
import struct
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
from Core.Tweaks import tweaks
from UI.components import preview_dialog
from Shared.Utils.lang import T


def _load_qrcode():
    """Charge qrcode : installé par l'utilisateur, sinon la copie embarquée dans vendor/."""
    try:
        import qrcode
        return qrcode
    except ImportError:
        vendor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "vendor")
        if vendor not in sys.path:
            sys.path.insert(0, vendor)
        import qrcode
        return qrcode


def matrix_to_png(matrix, scale=8, border=4):
    """Convertit une matrice QR en image PNG 100 % Python (zlib standard, aucune dépendance)."""
    import zlib
    n = len(matrix)
    size = (n + 2 * border) * scale
    lines = []
    for my in range(-border, n + border):
        if 0 <= my < n:
            row = matrix[my]
            line = bytearray(b"\x00")
            for mx in range(-border, n + border):
                v = 0 if (0 <= mx < n and row[mx]) else 255
                line.extend(bytes([v]) * scale)
        else:
            line = b"\x00" + b"\xff" * size
        for _ in range(scale):
            lines.append(bytes(line))
    raw = b"".join(lines)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")

EXPORT_KEYS = ["theme", "text_size", "colorblind", "advanced", "serenity", "close_action", "tray",
               "sound", "reminder", "quarantine_days"]
LABELS = {"theme": "Thème", "text_size": "Taille du texte", "colorblind": "Mode daltonien", "advanced": "Mode avancé",
          "serenity": "Mode Sérénité", "close_action": "Action de la croix", "tray": "Réduire à côté de l'horloge",
          "sound": "Carillon de fin",
          "reminder": "Rappel mensuel",
          "quarantine_days": "Jours de quarantaine"}

EXPLAIN = ("EXPORTER génère un QR code qui contient :\n"
           "  • ton APPARENCE et tes préférences : thème, taille du texte, daltonien, Sérénité, mode avancé, "
           "croix, carillon, rappel, durée de quarantaine ;\n"
           "  • la LISTE (par nom) des réglages « Calmer Windows » actuellement actifs.\n"
           "Il ne contient jamais : tes fichiers, le journal, la quarantaine, les programmes de démarrage, les "
           "services, ton nom d'utilisateur ni aucun chemin personnel.\n\n"
           "IMPORTER (fichier JSON) : chaque valeur est vérifiée à la lecture (type, plage, choix "
           "autorisés). Toute valeur invalide est ignorée et listée dans l'aperçu, jamais appliquée.\n"
           "Les réglages Windows du profil ne sont pas appliqués automatiquement : je te montre la liste, tu les appliques toi-même avec aperçu dans "
           "l'onglet « Calmer Windows ».")


def _build_profile_data(ctx):
    return {"app": "TidyDeck", "version": 1, "config": {k: ctx.cfg[k] for k in EXPORT_KEYS},
            "tweaks": [t.id for t in tweaks.TWEAKS if tweaks.is_active(t)]}


def export_qr(ctx):
    qrcode = _load_qrcode()
    data = _build_profile_data(ctx)
    json_str = json.dumps(data, ensure_ascii=False)
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(json_str)
    qr.make(fit=True)
    png = matrix_to_png(qr.get_matrix())
    tmp_path = os.path.join(tempfile.gettempdir(), "tidydeck_qr.png")
    with open(tmp_path, "wb") as fh:
        fh.write(png)
    win = tk.Toplevel(ctx.root)
    win.title("Ton QR code TidyDeck")
    win.configure(bg=ctx.theme["bg"])
    win.transient(ctx.root)
    tk.Label(win, text=T("📱 Scanne ce QR code avec ton téléphone"), font=("Segoe UI", 12, "bold"),
             bg=ctx.theme["bg"], fg=ctx.theme["fg"]).pack(pady=(16, 8))
    tk.Label(win, text=T("Transfère ta config sur un autre PC en un scan !"), font=("Segoe UI", 10),
             bg=ctx.theme["bg"], fg=ctx.theme["muted"]).pack(pady=(0, 12))
    photo = tk.PhotoImage(data=base64.b64encode(png).decode())
    lbl = tk.Label(win, image=photo)
    lbl.image = photo
    lbl.pack(padx=20, pady=10)
    btn_frame = tk.Frame(win, bg=ctx.theme["bg"])
    btn_frame.pack(pady=12)
    tk.Button(btn_frame, text=T("💾 Enregistrer le QR"), command=lambda: _save_qr(png),
              bg=ctx.theme["accent"], fg=ctx.theme["accent_fg"], padx=12, pady=6).pack(side="left", padx=8)
    tk.Button(btn_frame, text=T("Fermer"), command=win.destroy,
              bg=ctx.theme["card"], fg=ctx.theme["fg"], padx=12, pady=6).pack(side="left", padx=8)
    tk.Label(win, text=T("Contenu : {n1} préférences + {n2} réglage Windows" if len(data['tweaks']) == 1 else "Contenu : {n1} préférences + {n2} réglages Windows").format(n1=len(EXPORT_KEYS), n2=len(data['tweaks'])),
             font=("Segoe UI", 9), bg=ctx.theme["bg"], fg=ctx.theme["muted"]).pack(pady=(0, 12))


def _save_qr(png):
    path = filedialog.asksaveasfilename(defaultextension=".png", initialfile="tidydeck-qr.png",
                                       filetypes=[("Image PNG", "*.png")])
    if path:
        with open(path, "wb") as f:
            f.write(png)
        messagebox.showinfo("TidyDeck", T("QR code sauvegardé : {path}").format(path=path))


BOOL_KEYS = ("colorblind", "advanced", "serenity", "sound", "reminder", "tray")
CHOICES = {"theme": {"clair", "sombre", "tdah"},
           "text_size": {"normale", "grande"},
           "close_action": {"quit", "minimize"}}
# Anciens noms de theme encore presents dans de vieux fichiers de profil.
LEGACY_THEME = {"tdah_calm": "tdah", "gamer": "sombre"}
RANGES = {"quarantine_days": (1, 365)}


def _shown(v):
    return T("« {v0} »").format(v0=v) if isinstance(v, str) else str(v)


def sanitize(raw):
    """Valide chaque valeur d'un profil importe : type, plage, liste de choix autorises.

    Tout ce qui est invalide est IGNORE, jamais applique, et reporte a l'utilisateur.
    Retourne (valeurs_valides, motifs_des_rejets).
    """
    ok, skipped = {}, []
    if not isinstance(raw, dict):
        return ok, [T("bloc « config » absent ou mal formé")]
    for k in EXPORT_KEYS:
        if k not in raw:
            continue
        v = raw[k]
        label = LABELS.get(k, k)
        if k in BOOL_KEYS:
            if isinstance(v, bool):
                ok[k] = v
            else:
                skipped.append(f"{label} : {_shown(v)} n'est pas oui/non")
        elif k in CHOICES:
            val = LEGACY_THEME.get(v, v) if (k == "theme" and isinstance(v, str)) else v
            if isinstance(val, str) and val in CHOICES[k]:
                ok[k] = val
            else:
                skipped.append(T("{v0} : {v1} n'est pas un choix autorisé").format(v0=label, v1=_shown(v)))
        elif k in RANGES:
            lo, hi = RANGES[k]
            if isinstance(v, bool) or not isinstance(v, int):
                skipped.append(f"{label} : {_shown(v)} n'est pas un nombre entier")
            elif not lo <= v <= hi:
                skipped.append(f"{label} : {v} hors plage {lo}–{hi}")
            else:
                ok[k] = v
        else:
            skipped.append(T("{v0} : clé non reconnue").format(v0=label))
    return ok, skipped


def _valid_tweaks(raw):
    """Garde uniquement les identifiants de réglages qui existent vraiment."""
    if not isinstance(raw, list):
        return []
    return [i for i in raw if isinstance(i, str) and i in tweaks.BY_ID]


def _preview_lines(ctx, new, tweak_ids):
    diff = [f"• {LABELS[k]} : {ctx.cfg[k]}  →  {v}" for k, v in new.items()
            if ctx.cfg.get(k) != v]
    names = [tweaks.BY_ID[i].name for i in tweak_ids]
    return ([T("Apparence et préférences qui vont changer")] + (diff or [T("• (rien : déjà identique)")])
            + ["", T("Réglages Windows du profil (non appliqués automatiquement)")]
            + ([f"• {n}" for n in names] or [T("• aucun")]))


def export_profile(ctx):
    path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="tidydeck-profil.json")
    if not path:
        return
    data = _build_profile_data(ctx)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    messagebox.showinfo("TidyDeck", T("Profil exporté : {n1} préférences + {n2} réglage Windows listé." if len(data['tweaks']) == 1 else "Profil exporté : {n1} préférences + {n2} réglages Windows listés.").format(n1=len(EXPORT_KEYS), n2=len(data['tweaks'])))


def import_profile(ctx, after):
    path = filedialog.askopenfilename(filetypes=[("Profil TidyDeck", "*.json")])
    if not path:
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        messagebox.showerror("TidyDeck", T("Fichier illisible : {err}").format(err=e))
        return
    if not isinstance(data, dict) or data.get("app") != "TidyDeck":
        messagebox.showerror("TidyDeck", T("Ce fichier n'est pas un profil TidyDeck."))
        return
    new, skipped = sanitize(data.get("config"))
    tweak_ids = _valid_tweaks(data.get("tweaks"))
    if not new and not tweak_ids:
        messagebox.showwarning(
            "TidyDeck",
            "Aucune valeur exploitable dans ce profil.\n\n"
            + "\n".join(f"• {s}" for s in skipped[:8]))
        return
    lines = _preview_lines(ctx, new, tweak_ids)
    if skipped:
        lines += ["", T("Valeurs ignorées (non valides)")] + [f"• {s}" for s in skipped[:12]]
        if len(skipped) > 12:
            lines.append(f"• … et {len(skipped) - 12} autre(s)")
    if preview_dialog(ctx, "Importer ce profil ?",
                      T("Voici exactement ce que l'import va faire. Les valeurs non valides sont ignorées :"),
                      lines, "", "Oui, importer"):
        ctx.cfg.update(new)
        after()
