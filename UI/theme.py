"""Thèmes : clair chaleureux, sombre, palette daltonien (bleu/orange, jamais rouge/vert).
Les états ne reposent JAMAIS sur la couleur seule : toujours symbole + mot."""
import tkinter.font as tkfont
from tkinter import ttk

PALETTES = {
    "clair": dict(bg="#FBF8F3", card="#FFFFFF", fg="#23211F", muted="#5E5750",
                  accent="#0072B2", accent_fg="#FFFFFF", line="#E4DDD3"),
    "sombre": dict(bg="#313338", card="#2B2D31", fg="#DBDFE4", muted="#A2A9B2",
                   accent="#5865F2", accent_fg="#FFFFFF", line="#3F4147"),
    # accent : #B3541A et non #E07B39 -> blanc dessus a 5,00:1 au lieu de 2,97:1.
    "tdah": dict(bg="#FFF8E7", card="#FFFDF5", fg="#2C2416", muted="#6B5D4F",
                  accent="#B3541A", accent_fg="#FFFFFF", line="#F0E0C0"),
}
# JAUGES (barre de volume du carillon, barres de disque). Le theme « Chaleureux » est
# destine a un public TDAH : teintes chaudes, desaturees, a faible excitation, jamais le
# vert saturé / rouge alerte des autres themes. Les autres themes gardent leurs jetons d'etat.
# Contrainte : chaque couleur doit atteindre 3:1 sur la carte du theme, sinon la barre
# est invisible. Le pourcentage ou le mot est toujours affiche a cote (double canal).
GAUGES = {
    "clair": {"volume": "#2E7D32", "ok": "#35883B", "mid": "#B87D18", "high": "#B84C30"},
    "sombre": {"volume": "#7BD88F", "ok": "#5FBF6B", "mid": "#E0B25C", "high": "#DE8A72"},
    "tdah": {"volume": "#A9682E", "ok": "#5E8452", "mid": "#B0893C", "high": "#AE6048"},
}
# sidebar_section : titres de section. sidebar_muted : label de version, entrees
# grisees (mode non disponible) et badges [Admin]/[Avance]. Les deux doivent
# atteindre 4,5:1 sur le fond du menu ; avant, sidebar_version servait aux deux et
# tombait a 3,6-4,1:1. sidebar_accent (barre de gauche) doit atteindre 3:1.
SIDEBAR_COLORS = {
    "clair": {"sidebar_bg": "#1E2A3A", "sidebar_fg": "#C8D0D8", "sidebar_active_bg": "#2A3A4E",
              "sidebar_active_fg": "#FFFFFF", "sidebar_hover_bg": "#253545", "sidebar_accent": "#4A90D9",
              "sidebar_section": "#A8B8C8", "sidebar_muted": "#93A3B3"},
    # accent : #7C88F5 et non #5865F2 -> barre a 4,40:1 au lieu de 2,99:1.
    "sombre": {"sidebar_bg": "#2B2D31", "sidebar_fg": "#B5BAC1", "sidebar_active_bg": "#404249",
               "sidebar_active_fg": "#FFFFFF", "sidebar_hover_bg": "#3A3C41", "sidebar_accent": "#7C88F5",
               "sidebar_section": "#B2B5B9", "sidebar_muted": "#9DA0A4"},
    "tdah": {"sidebar_bg": "#3D2E1F", "sidebar_fg": "#E8D5B7", "sidebar_active_bg": "#4A3828",
              "sidebar_active_fg": "#FFFFFF", "sidebar_hover_bg": "#453425", "sidebar_accent": "#E07B39",
              "sidebar_section": "#D8BA98", "sidebar_muted": "#C4A582"},
}
for _c in SIDEBAR_COLORS.values():
    # compat : ancien nom conserve, aligne sur la nouvelle couleur discrete.
    _c["sidebar_version"] = _c["sidebar_muted"]
# JETONS SEMANTIQUES D'ETAT (equivalent des variables CSS --etat-succes etc. ; Tkinter n'a
# pas de variables CSS, donc dictionnaire de jetons : les pages ne consomment que
# ctx.status_colors["ok"|"info"|"warn"|"danger"|"off"] et ctx.symbols[...]).
# Regle d'or : la couleur ne porte JAMAIS l'information seule. Chaque etat = 3 canaux :
#   forme (silhouette distincte) + mot explicite + luminance (lisable en niveaux de gris).
# Palette daltonien = Okabe-Ito universelle (une seule palette, pas de profils par type de
# daltonisme), ajustee par theme pour >= 4.5:1 en texte et >= 3:1 en icone.
# Le theme « Chaleureux » garde son fond/texte chauds : seules les couleurs d'etat sont remplacees.
STATUS = {
    # Palettes normales (couleurs propres au theme)
    ("clair", False): {"ok": "#2E7D32", "warn": "#9A5B00", "info": "#4A5568", "danger": "#C62828", "off": "#4A5568"},
    ("sombre", False): {"ok": "#7BD88F", "warn": "#FFB454", "info": "#BDB8AF", "danger": "#FF8A70", "off": "#BDB8AF"},
    # warn : #A85C1C et non #C67030 -> 4,89:1 sur la carte au lieu de 3,58:1.
    ("tdah", False): {"ok": "#2E7D32", "warn": "#A85C1C", "info": "#6B5D4F", "danger": "#C62828", "off": "#6B5D4F"},
    # Palettes daltonien (Okabe-Ito, contraste ajuste par fond)
    ("clair", True): {"ok": "#0072B2", "warn": "#8A5E00", "info": "#0B4F86", "danger": "#B23A0A", "off": "#4A5568"},
    ("sombre", True): {"ok": "#56B4E9", "warn": "#E69F00", "info": "#5FA3D9", "danger": "#F5764E", "off": "#BDB8AF"},
    ("tdah", True): {"ok": "#0072B2", "warn": "#8A5E00", "info": "#0B4F86", "danger": "#B23A0A", "off": "#6B5D4F"},
}
# Forme + mot : ● cercle = sur, ■ carre = info, ▲ triangle = a verifier,
# ⬢ octogone = irreversible, ✕ = desactive. Le mot accompagne toujours la forme.
SYMBOLS = {"ok": "● Sûr", "warn": "▲ À vérifier", "info": "■ Info", "danger": "⬢ Irréversible", "off": "✕ Désactivé"}
SYMBOLS_SERENE = {"ok": "● Tout est fluide", "warn": "▲ À voir quand tu veux", "info": "■ Info", "danger": "⬢ À faire une seule fois", "off": "✕ Désactivé"}
SIZES = {"normale": 1.0, "grande": 1.25}


def apply(root, cfg):
    theme_name = cfg["theme"]
    if theme_name in ("tdah_calm", "gamer"):
        theme_name = "sombre"
    if theme_name not in PALETTES:
        theme_name = "clair"
    p = dict(PALETTES[theme_name])
    p.update(SIDEBAR_COLORS[theme_name])
    status = dict(STATUS[(theme_name, bool(cfg["colorblind"]))])
    if cfg.get("serenity"):
        # Sérénité : aucune couleur d'alerte (rouge/orange bannis). Le ton est porté
        # par les mots et les formes, pas par des signaux stressants.
        status["warn"] = status["info"]
        status["danger"] = status["info"]
    symbols = SYMBOLS_SERENE if cfg.get("serenity") else SYMBOLS
    size = int(round(11 * SIZES.get(cfg.get("text_size"), 1.0)))
    for n in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
        try:
            tkfont.nametofont(n).configure(family="Segoe UI" if n != "TkFixedFont" else "Consolas", size=size)
        except Exception:
            pass
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=p["bg"])
    s.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["card"], bordercolor=p["line"])
    s.configure("TFrame", background=p["bg"])
    s.configure("TLabel", background=p["bg"], foreground=p["fg"])
    s.configure("Title.TLabel", font=("Segoe UI", int(size * 1.7), "bold"))
    s.configure("Sub.TLabel", font=("Segoe UI", int(size * 1.2), "bold"))
    s.configure("Muted.TLabel", foreground=p["muted"])
    s.configure("TButton", padding=(12, 7), background=p["card"], foreground=p["fg"], borderwidth=1,
                focuscolor=p["accent"], lightcolor=p["line"], darkcolor=p["line"],
                activebackground=p["line"], activeforeground=p["fg"])
    s.map("TButton", background=[("active", p["line"])],
          foreground=[("active", p["fg"]), ("disabled", p["muted"])])
    s.configure("Accent.TButton", background=p["accent"], foreground=p["accent_fg"], padding=(14, 8))
    s.map("Accent.TButton", background=[("active", p["accent"])])
    s.configure("Big.TButton", background=p["accent"], foreground=p["accent_fg"], padding=(26, 14),
                font=("Segoe UI", int(size * 1.25), "bold"))
    s.map("Big.TButton", background=[("active", p["accent"])])
    s.configure("Flat.TButton", background=p["bg"], borderwidth=0, anchor="w", padding=(4, 5))
    s.map("Flat.TButton", background=[("active", p["line"])])
    s.configure("TCheckbutton", background=p["bg"], foreground=p["fg"], focuscolor=p["accent"])
    s.map("TCheckbutton", indicatorcolor=[("selected", p["accent"])])
    s.configure("TRadiobutton", background=p["bg"], foreground=p["fg"], focuscolor=p["accent"])
    s.map("TRadiobutton", indicatorcolor=[("selected", p["accent"])])
    s.map("TButton", borderwidth=[("focus", 2)])
    s.map("TCheckbutton", borderwidth=[("focus", 2)])
    s.map("TRadiobutton", borderwidth=[("focus", 2)])
    s.map("TNotebook.Tab", focuscolor=[("focus", p["accent"])])
    s.configure("TNotebook", background=p["bg"], borderwidth=0, tabposition="n")
    s.configure("Side.TNotebook", background=p["bg"], borderwidth=0, tabposition="wn", tabmargins=(0, 0, 0, 0))
    s.configure("Side.TNotebook.Tab", padding=(14, 11), anchor="w")
    s.configure("TNotebook.Tab", padding=(12, 7), background=p["line"], foreground=p["fg"])
    s.map("TNotebook.Tab", background=[("selected", p["card"])], foreground=[("selected", p["accent"])])
    s.configure("Treeview", background=p["card"], fieldbackground=p["card"], foreground=p["fg"],
                rowheight=int(size * 2.6), borderwidth=0)
    # En-tetes de tableaux : texte toujours sur fg plein (jamais un gris delave),
    # fond ligne uniforme, aucun changement de teinte au survol/cliquette
    # (le defaut clam eclaircissait le texte sur le beige -> <4,5:1).
    s.configure("Treeview.Heading", background=p["line"], foreground=p["fg"], padding=6,
                relief="flat", borderwidth=1, lightcolor=p["line"], darkcolor=p["line"])
    s.map("Treeview.Heading",
          background=[("active", p["line"]), ("pressed", p["line"])],
          foreground=[("active", p["fg"]), ("pressed", p["fg"])])
    # Combobox (valeurs « every [ ] min » des Rappels) : en clam, un readonly herite
    # des couleurs par defaut tres pales -> texte invisible. On epingle explicitement
    # le champ readonly ET la liste deroulante aux couleurs du theme (>= 4,5:1).
    s.configure("TCombobox", fieldbackground=p["card"], background=p["card"], foreground=p["fg"],
                arrowcolor=p["fg"], bordercolor=p["line"], lightcolor=p["line"],
                darkcolor=p["line"], padding=3)
    s.map("TCombobox",
          fieldbackground=[("readonly", p["card"]), ("disabled", p["line"])],
          foreground=[("readonly", p["fg"]), ("disabled", p["muted"])],
          selectbackground=[("readonly", p["card"])],
          selectforeground=[("readonly", p["fg"])],
          background=[("readonly", p["card"]), ("active", p["line"])])
    root.option_add("*TCombobox*Listbox*Background", p["card"])
    root.option_add("*TCombobox*Listbox*Foreground", p["fg"])
    root.option_add("*TCombobox*Listbox*selectBackground", p["accent"])
    root.option_add("*TCombobox*Listbox*selectForeground", p["accent_fg"])
    s.map("Treeview", background=[("selected", p["accent"])], foreground=[("selected", p["accent_fg"])],
         bordercolor=[("focus", p["accent"])])
    s.configure("Horizontal.TProgressbar", background=p["accent"], troughcolor=p["line"])
    # Jauges : barre de volume du carillon + barres de disque. Le theme « Chaleureux »
    # (public TDAH) utilise ses teintes chaudes desaturees ; Serenite reste neutre.
    gauge = dict(GAUGES.get(theme_name, GAUGES["clair"]))
    if cfg.get("serenity"):
        gauge["volume"] = status["info"]
    if cfg.get("colorblind"):
        # Daltonien : le vert/orange/rouge des jauges n'est pas fiable. On reprend les
        # jetons d'etat (Okabe-Ito), exactement comme pour les pastilles de statut.
        # La barre de volume est traitee comme les autres : en mode daltonien elle ne
        # doit JAMAIS rester verte (#2E7D32 / #7BD88F), on la bascule sur le ton
        # d'information neutre (bleu), comme en Serenite.
        gauge["ok"], gauge["mid"], gauge["high"] = status["ok"], status["warn"], status["danger"]
        gauge["volume"] = status["info"]
    p["gauge"] = gauge
    vol_col = gauge["volume"]
    p["volume"] = vol_col
    s.configure("Volume.Horizontal.TScale", background=vol_col, troughcolor=p["line"],
                borderwidth=0, lightcolor=p["bg"], darkcolor=p["bg"], sliderrelief="flat",
                sliderlength=18, gripcount=0, arrowsize=0)
    s.map("Volume.Horizontal.TScale", background=[("active", vol_col), ("pressed", vol_col)])
    return p, status, symbols
