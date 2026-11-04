"""Composants réutilisés partout."""
import os
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from Shared.Utils.common import (open_in_explorer, human_size, APP_VERSION, open_reg_key,
                                open_windows_settings, reg_path, copy_text)
from Shared.Utils.lang import T

# Intervalle de veille des taches de fond. 40 ms = imperceptible a l'oeil et la
# reponse d'un scan arrive des qu'elle est prete (120 ms ajoutaient jusqu'a
# 80 ms de temps mort apres chaque operation).
POLL_FOND = 40


def info_badge(parent, color, bg, px=18):
    c = tk.Canvas(parent, width=px, height=px, bg=bg, highlightthickness=0)
    c.create_rectangle(2, 2, px - 2, px - 2, outline=color, width=2)
    c.create_text(px / 2, px / 2 + 1, text="i", fill=color, font=("Segoe UI", int(px * 0.62), "bold"))
    return c


def info_note(parent, theme, info_color, text, wraplength=900, bold=False, bg=None):
    text = T(text)
    bg = bg or theme["bg"]
    fr = tk.Frame(parent, bg=bg)
    info_badge(fr, info_color, bg).pack(side="left", anchor="n", padx=(0, 8))
    tk.Label(fr, text=text, bg=bg, fg=theme["fg"], wraplength=wraplength, justify="left",
             font=("Segoe UI", 10, "bold") if bold else ("Segoe UI", 10)).pack(side="left", fill="x", expand=True)
    return fr


def auto_wrap(label):
    def _w(e):
        label.configure(wraplength=max(e.width - 4, 40))
    label.bind("<Configure>", _w)
    return label


def clamp_wrap(widget, avail):
    """Replie tous les libellés a `wraplength` fige qui depassent la largeur utile.

    Les pages portaient des valeurs dures (900, 850, 820) calculees pour une sidebar
    etroite. Des que la sidebar s'elargit (grande / tres grande taille de texte),
    ces valeurs depassent le canvas et le texte est rogne. On re-ajuste sur la
    largeur reellement disponible ; l'operation converge (on ne fait que reduire)."""
    if avail < 60:
        return
    limit = max(40, avail)
    stack = [widget]
    while stack:
        w = stack.pop()
        for c in w.winfo_children():
            stack.append(c)
            try:
                wl = int(str(c.cget("wraplength")))
            except Exception:
                continue
            if wl > limit:
                try:
                    c.configure(wraplength=limit)
                except Exception:
                    pass


def run_bg(root, fn, done):
    box = {}

    def work():
        try:
            box["r"] = fn()
        except Exception as e:  # noqa
            box["e"] = e
    t = threading.Thread(target=work, daemon=True)
    t.start()

    def poll():
        try:
            if t.is_alive():
                root.after(POLL_FOND, poll)   # 40 ms : la fin d'une tache ne traine plus
                return
        except tk.TclError:
            return                        # la fenetre est fermee : rien a rapporter
        try:
            done(box.get("r"), box.get("e"))
        except tk.TclError:
            pass
    poll()


def fit_window(win, ctx, min_w=720, min_h=520):
    win.update_idletasks()
    sc = ctx.scale
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w = min(max(win.winfo_reqwidth(), int(min_w * sc)), int(sw * 0.92))
    h = min(max(win.winfo_reqheight(), int(min_h * sc)), int(sh * 0.9))
    win.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 3)}")
    win.minsize(min(w, 520), min(h, 360))
    win.resizable(True, True)


class FlowFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, height=1)
        self._kids, self._h = [], 1
        self.bind("<Configure>", self._relayout)

    def add(self, w):
        self._kids.append(w)
        self.after_idle(self._relayout)

    def _relayout(self, _e=None):
        width = self.winfo_width()
        if width <= 1:
            width = 1000
        x = y = rowh = 0
        for w in self._kids:
            ww, wh = w.winfo_reqwidth(), w.winfo_reqheight()
            if x + ww > width and x > 0:
                x, y, rowh = 0, y + rowh + 6, 0
            w.place(x=x, y=y)
            x += ww + 8
            rowh = max(rowh, wh)
        h = y + rowh
        if h != self._h and h > 0:
            self._h = h
            self.configure(height=h)


class ScrollFrame(ttk.Frame):
    def __init__(self, master, bg):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=bg)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._win = win
        self.inner.bind("<Configure>", lambda e: self._sync())
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        self.bind("<Destroy>", self._gone)

    def _gone(self, e):
        if e.widget is self:
            try:
                self.canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)
        self._sync()

    def _sync(self):
        ch = self.canvas.winfo_height()
        ih = self.inner.winfo_reqheight()
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), max(ch, ih)))

    def _wheel(self, e):
        # Le canvas peut avoir ete detruit (rebuild) alors que bind_all(<MouseWheel>)
        # pointe encore ici : sans garde, Tk lève "invalid command name ...!canvas".
        try:
            if self.canvas.winfo_exists():
                self.canvas.yview_scroll(int(-e.delta / 120), "units")
        except tk.TclError:
            pass

    def get_view(self):
        try:
            return self.canvas.yview()[0]
        except tk.TclError:
            return 0.0

    def set_view(self, frac):
        try:
            self.canvas.update_idletasks()
            self.canvas.yview_moveto(frac or 0.0)
        except tk.TclError:
            pass


class Collapsible(ttk.Frame):
    def __init__(self, master, title, lines):
        super().__init__(master)
        self.title, self.lines, self.open = T(title), [T(l) for l in lines], False
        self.btn = ttk.Button(self, text=f"▸ {self.title}", style="Flat.TButton", command=self.toggle)
        self.btn.pack(fill="x")
        self.body = ttk.Frame(self)
        for l in self.lines:
            auto_wrap(ttk.Label(self.body, text="      " + l, style="Muted.TLabel", justify="left")).pack(
                anchor="w", fill="x", pady=(0, 5))
        if not lines:
            self.btn.configure(text=f"   {self.title}")

    def toggle(self):
        if not self.lines:
            return
        self.open = not self.open
        self.btn.configure(text=("▾ " if self.open else "▸ ") + self.title)
        if self.open:
            self.body.pack(anchor="w", fill="x", padx=10, pady=(2, 6))
        else:
            self.body.pack_forget()


class VolumeBar(tk.Canvas):
    """Barre de volume visible (remplissage + poignée), cliquable et glissable."""

    def __init__(self, master, theme, var, color, on_release=None, width=260, height=26):
        super().__init__(master, width=width, height=height, bg=theme["bg"],
                       highlightthickness=0, bd=0)
        self.theme, self.var, self.color, self.on_release = theme, var, color, on_release
        self._bar_w = width
        self.bind("<Configure>", self._resize)
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        var.trace_add("write", lambda *a: self._draw())
        self._draw()

    def _resize(self, e):
        self._bar_w = max(80, e.width)
        self.configure(width=self._bar_w)
        self._draw()

    def _drag(self, e):
        inner = self._bar_w - 22
        frac = max(0.0, min(1.0, (e.x - 11) / max(1, inner)))
        self.var.set(int(round(frac * 100)))

    def _release(self, _e=None):
        if self.on_release:
            self.on_release(self.var.get())

    def _draw(self):
        self.delete("all")
        h = int(self.cget("height"))
        v = max(0, min(100, int(self.var.get())))
        pad, bh = 11, 12
        y0, y1 = (h - bh) // 2, (h + bh) // 2
        inner = self._bar_w - 2 * pad
        self.create_rectangle(pad, y0, pad + inner, y1, fill=self.theme["line"], outline="")
        if v > 0:
            self.create_rectangle(pad, y0, pad + int(inner * v / 100.0), y1,
                                 fill=self.color, outline="")
        hx = pad + int(inner * v / 100.0)
        self.create_oval(hx - 9, h // 2 - 9, hx + 9, h // 2 + 9, fill=self.color,
                        outline=self.theme["card"], width=2)
        self.create_text(self._bar_w - 8, h // 2, anchor="e", fill=self.theme["fg"],
                        font=("Segoe UI", 9, "bold"), text=f"{v} %")


def calm_detail(r):
    """Version courte et rassurante du detail, pour le mode Serenite."""
    calm = r.get("calm")
    if calm:
        return calm
    d = (r.get("detail") or "").strip()
    if not d:
        return ""
    for marker in ("Ce qui sera écrit", "Où ça se trouve", "Commande lancée", "État enregistré"):
        i = d.find(marker)
        if i > 0:
            d = d[:i].strip()
    return d + "\n\nRisque : aucun. Tu peux revenir en arrière quand tu veux."


def _clip_text(text, px, font):
    """Tronque `text` pour qu'il tienne dans `px` pixels, point de suspension inclus.

    Un nom coupe net (« decouvrez Wind ») sans signe indicating laisse croire que
    c'est le nom complet. Sans ellipse, on ne sait pas qu'il manque la suite."""
    text = str(text)
    try:
        if font.measure(text) <= px:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + "…") <= px:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + "…"
    except Exception:
        return text


class Checklist(ttk.Frame):
    def __init__(self, master, ctx, headers=("Élément", "État"), checkable=True, on_toggle=None,
                 open_label=None, box_only=False):
        super().__init__(master)
        self.ctx, self.checkable, self.on_toggle, self.rows = ctx, checkable, on_toggle, {}
        self._noms = {}
        self._infos = {}
        # box_only : cocher uniquement en cliquant sur le petit carré (1re colonne),
        # un clic sur le texte ne fait que sélectionner la ligne.
        self.box_only = box_only
        pane = ttk.PanedWindow(self, orient="vertical")
        pane.pack(fill="both", expand=True)
        self.pane = pane
        self._sash_h = None
        top, bottom = ttk.Frame(pane), ttk.Frame(pane)
        self.haut_pane, self.bas_pane = top, bottom
        pane.add(top, weight=4)
        pane.add(bottom, weight=2)
        self.tree = ttk.Treeview(top, columns=("chk", "name", "info"), show="headings", selectmode="browse",
                               height=7)
        self.tree.heading("chk", text="")
        self.tree.heading("name", text=T(headers[0]))
        self.tree.heading("info", text=T(headers[1]))
        self.tree.column("chk", width=50, stretch=False, anchor="center")
        self.tree.column("name", width=420)
        self.tree.column("info", width=280)
        # Nombre minimal de lignes visibles dans le tableau (les pages qui
        # montrent beaucoup de résultats le relèvent, ex. Résidus : 4).
        self.tree_min_rows = 2
        if not checkable:
            self.tree.configure(displaycolumns=("name", "info"))
        sb = ttk.Scrollbar(top, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for tag, col in ctx.status_colors.items():
            self.tree.tag_configure(tag, foreground=col)
        th = ctx.theme
        # Un seul bloc : carte unique contenant le détail + le bouton, jamais écrasé
        card = tk.Frame(bottom, bg=th["card"], highlightbackground=th["line"], highlightthickness=1)
        card.pack(fill="both", expand=True, pady=(8, 4))
        bar = ttk.Frame(card)
        bar.pack(side="bottom", fill="x", padx=10, pady=(0, 8))
        self.open_btn = ttk.Button(bar, text=open_label or "📂 Ouvrir l'emplacement (pour vérifier)", command=self._open)
        self._default_open_label = open_label or "📂 Ouvrir l'emplacement (pour vérifier)"
        # Grise des la creation : avant le premier set_rows(), aucune ligne
        # n'est selectionnee et le clic ne produirait aucun effet.
        self.open_btn.state(["disabled"])
        self.open_btn.pack(side="left")
        self.detail = tk.Text(card, height=4, wrap="word", relief="flat", padx=14, pady=8,
                              bg=th["card"], fg=th["fg"], highlightthickness=0, font=("Segoe UI", 10),
                              state="disabled")
        self.detail.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select)
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<space>", lambda e: self._space())
        # Le panneau du bas (detail + bouton) ne doit jamais etre ecrase. En texte
        # Grand il demandait plus que sa part et se retrouvait a 24 px visibles pour
        # 86 requis : le texte coupe a mi-hauteur. On calcule donc combien de
        # lignes du tableau rentrent reellement, et le reste va au detail.
        self.bind("<Configure>", self._fit_sash)
        # Le tableau troncait les noms sans point de suspension (« decouvrez Wind »).
        # On donne a la colonne « Reglage » la place que reclame le nom le plus
        # long, dans la limite de la place disponible.
        self.tree.bind("<Configure>", self._fit_cols)

    def _fit_sash(self, e=None):
        """Redonne sa place au panneau du bas quand la hauteur change
        (redimensionnement, changement de taille de texte)."""
        h = int(getattr(e, "height", 0) or self.winfo_height() or 0)
        if h < 140:
            return
        try:
            self.detail.update_idletasks()
            self.open_btn.update_idletasks()
            self.tree.update_idletasks()
            bas = self.detail.winfo_reqheight() + self.open_btn.winfo_reqheight() + 42
            dispo = h - bas
            if dispo < 60:
                return
            rows_h = 24
            kids = self.tree.get_children()
            if kids:
                try:
                    bb = self.tree.bbox(kids[0])
                    if bb and bb[3] > 8:
                        rows_h = bb[3]
                except Exception:
                    pass
            entete = 30
            n = min(12, max(self.tree_min_rows, int((dispo - entete) / max(1, rows_h))))
            if n != int(self.tree.cget("height")):
                self.tree.configure(height=n)
            pos = max(entete + rows_h * self.tree_min_rows, h - bas)
            if self._sash_h is None or abs(pos - self._sash_h) >= 2:
                self._sash_h = pos
                self.pane.sashpos(0, pos)
        except Exception:
            pass

    def _fit_cols(self, _e=None):
        try:
            total = self.tree.winfo_width()
            if total < 220:
                return
            # La police d'un Treeview vient du style ttk, pas du widget : un
            # cget("font") here leve une TclError et avalerait toute la methode.
            fnt = ttk.Style().lookup("Treeview", "font") or ("Segoe UI", 10)
            f = tkfont.Font(font=fnt)
            chk = 50 if self.checkable else 0
            infos0 = getattr(self, "_infos", {})
            # La colonne « etat » se dimensionne sur son contenu le plus long :
            # en taille Grande, « ✕ Pas appliqué · Désactivable sans risque »
            # depasse les 280 px fixes et le Treeview coupait net, sans ellipse.
            besoin_info = max([f.measure(t) for t in infos0.values()] or [0])
            cap = max(150, int(total * 0.46))
            info = max(150, min(besoin_info + 16, cap))
            dispo = total - chk - info - 10
            need = 0
            noms0 = getattr(self, "_noms", {})
            for i in self.tree.get_children():
                try:
                    nom = noms0.get(i, str(self.tree.set(i, "name")))
                    need = max(need, f.measure(nom))
                except Exception:
                    pass
            w = min(dispo, max(160, need + 18))
            if abs(w - int(self.tree.column("name", "width"))) > 2:
                self.tree.column("name", width=w)
            for i in self.tree.get_children():
                complet = noms0.get(i)
                if complet is not None:
                    vise = _clip_text(complet, max(24, w - 16), f)
                    if self.tree.set(i, "name") != vise:
                        self.tree.set(i, "name", vise)
                complet_i = infos0.get(i)
                if complet_i is not None:
                    vise_i = _clip_text(complet_i, max(24, info - 16), f)
                    if self.tree.set(i, "info") != vise_i:
                        self.tree.set(i, "info", vise_i)
            if abs(info - int(self.tree.column("info", "width"))) > 2:
                self.tree.column("info", width=info)
        except Exception:
            pass

    def _m(self, t):
        return self.ctx.mask(T(t))

    def set_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.rows = {r["id"]: r for r in rows}
        # les noms complets, tels qu'affiches : la troncature se fera par-dessus,
        # avec l'ellipse, selon la largeur reellement disponible
        self._noms = {r["id"]: self._m(r["name"]) for r in rows}
        self._infos = {r["id"]: self._m(r.get("info", "")) for r in rows}
        for r in rows:
            self.tree.insert("", "end", iid=r["id"], tags=(r.get("status", ""),),
                             values=(self._box(r), self._noms[r["id"]], self._infos[r["id"]]))
        self._show("Clique sur une ligne pour voir : ce que c'est, où ça se trouve, le risque.")
        self.open_btn.state(["disabled"])
        if rows:
            first = rows[0]["id"]
            self.tree.selection_set(first)
            self.tree.see(first)
            self._select()
        # Le dimensionnement se refait ici : c'est maintenant que le tableau a ses
        # lignes, donc maintenant qu'on sait reellement combien en rentrent.
        self._fit_sash()
        self.after_idle(self._fit_sash)
        self._fit_cols()
        self.after_idle(self._fit_cols)

    def _box(self, r):
        return ("☑" if r.get("checked") else "☐") if self.checkable and not r.get("locked") else ""

    def checked_ids(self):
        return [i for i, r in self.rows.items() if r.get("checked")]

    def update_row(self, iid, **kw):
        self.rows[iid].update(kw)
        if "name" in kw:
            self._noms[iid] = self._m(kw["name"])
        if "info" in kw:
            # Le texte d'etat change de longueur (« ✕ Pas appliqué » -> « ⏻ Sera
            # desactive ») : sans re-adjustement la valeur la plus longue serait
            # coupee net par la colonne.
            self._infos[iid] = self._m(kw["info"])
        r = self.rows[iid]
        self.tree.item(iid, values=(self._box(r), self._noms.get(iid, self._m(r["name"])),
                                    self._infos.get(iid, self._m(r.get("info", "")))),
                       tags=(r.get("status", ""),))
        if "info" in kw:
            self.after_idle(self._fit_cols)

    def set_all(self, value, only=None):
        n = 0
        for iid, r in self.rows.items():
            if r.get("locked") or (only and not only(r)):
                continue
            self.update_row(iid, checked=value)
            n += 1
        return n

    def _click(self, e):
        iid = self.tree.identify_row(e.y)
        if not iid or not self.checkable or self.tree.identify_region(e.x, e.y) != "cell":
            return
        if self.box_only and self.tree.identify_column(e.x) != "#1":
            return
        self._toggle(iid)

    def _space(self):
        sel = self.tree.selection()
        if sel and self.checkable:
            self._toggle(sel[0])

    def _toggle(self, iid):
        r = self.rows[iid]
        if r.get("locked"):
            return
        new = not r.get("checked")
        if self.on_toggle and self.on_toggle(iid, new) is False:
            return
        self.update_row(iid, checked=new)

    def _can_open(self, r):
        if r.get("settings") or r.get("shell") or r.get("reg"):
            return True
        return any(os.path.exists(f) for f in r.get("folders", []))

    def _select(self, _e=None):
        sel = self.tree.selection()
        if not sel:
            return
        r = self.rows[sel[0]]
        d = r.get("detail", "")
        if self.ctx.cfg.get("serenity"):
            d = calm_detail(r)
        self._show(d)
        can = self._can_open(r)
        self.open_btn.state(["!disabled"] if can else ["disabled"])
        loc = r.get("location")
        if can and loc:
            self.open_btn.configure(text=T("📂 Ouvrir : {lieu}").format(lieu=self._m(loc)))
        else:
            self.open_btn.configure(text=T(self._default_open_label))

    def _open(self):
        sel = self.tree.selection()
        if not sel:
            return
        r = self.rows[sel[0]]
        ok = False
        s = r.get("settings")
        # Une liste = candidats tries dans l'ordre : certaines pages Windows sont
        # depreciees selon la version (ex : privacy-backgroundapps sous Win 11
        # 21H2+), on retombe sur la page qui la remplace.
        for cand in ((s if isinstance(s, (list, tuple)) else [s]) if s else []):
            if open_windows_settings(cand):
                ok = True
                break
        if not ok:
            for f in r.get("folders", []):
                if os.path.exists(f):
                    ok = open_in_explorer(f if os.path.isdir(f) else os.path.dirname(f))
                    break
        if not ok and r.get("shell"):
            ok = open_in_explorer(r["shell"])
        if not ok and r.get("reg"):
            full = reg_path(*r["reg"])
            copied = copy_text(full)
            ok = open_reg_key(*r["reg"])
            if ok:
                self._show("regedit s'ouvre (il ne sait pas se positionner tout seul sur une clé).\n\n"
                          + ("Le chemin complet est dans ton presse-papiers, colle-le avec Ctrl+L :\n    "
                             if copied else "Le chemin à recopier dans regedit :\n    ")
                          + full
                          + "\n\nRien n'a été modifié : tu es en consultation.")
        if not ok:
            self._show("⚠ Impossible d'ouvrir cet emplacement pour l'instant (droits insuffisants, ou "
                      "l'application demandée n'est pas disponible sur ce PC).\n\n"
                      "Rien n'a été modifié : tu peux réessayer plus tard ou le faire à la main depuis le détail ci-dessus.")

    def _show(self, text):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", self._m(text))
        self.detail.configure(state="disabled")


class Sidebar(tk.Frame):
    """Barre de navigation : sections repliables, navigation clavier complete
    (Fleches / Entree / Tab), badges, et polices qui suivent la taille de texte."""

    def __init__(self, master, items, on_select, colors, disabled=None, scale=1.0,
                 hauteur=None):
        super().__init__(master, bg=colors["sidebar_bg"], width=220)
        self.pack_propagate(False)
        self.colors = colors
        self.on_select = on_select
        self.disabled = set(disabled or ())
        self.nav_items = {}
        self.active = None
        self._sections = {}
        self._all = []
        self._parent = {}
        self.scale = max(0.8, float(scale))
        s = self.scale
        self._fnt = lambda base, weight="": ("Segoe UI", max(8, int(round(base * s))), weight)
        self._pad = lambda base: max(1, int(round(base * (1 + (s - 1) * 0.45))))
        # Le menu entier doit tenir dans la hauteur de la fenetre (750 px) sans
        # ascenseur : en « Grande » taille il debordait de ~100 px et les
        # dernieres entrees (« Sauvegarde et transfert », « A propos ») etaient
        # coupees, donc inaccessibles. On rogne la verticale juste ce qu'il faut,
        # ligne par ligne, jamais la police.
        self._dispo = int(hauteur or 0)
        self._rognage = 0
        self._fitting = False
        self._logo_lbl = None
        self._logo_pad = (0, 0)
        self._ver_lbl = None
        self._ver_pad = 0
        self._row_lbls = []
        self._hdr_lbls = []
        # Largeur necessaire calculee avec les metriques reelles de la police :
        # a « grande » et « tres grande » taille, une sidebar figee a 220 px tronquait
        # « Sauvegarde et transfert », « Applis preinstallnees », etc.
        self._need = 0
        self._logo_lbl = tk.Label(self, text="🌿 TidyDeck", font=self._fnt(18, "bold"),
                                 bg=colors["sidebar_bg"], fg="white", anchor="w")
        self._logo_pad = (self._pad(20), self._pad(2))
        self._logo_lbl.pack(pady=self._logo_pad, padx=self._pad(20), fill="x")
        self._track("🌿 TidyDeck", self._fnt(18, "bold"), self._pad(40))
        self._ver_lbl = tk.Label(self, text=f"version {APP_VERSION}", font=self._fnt(9),
                                bg=colors["sidebar_bg"], fg=colors["sidebar_muted"],
                                anchor="w")
        self._ver_pad = self._pad(12)
        self._ver_lbl.pack(pady=(0, self._ver_pad), padx=self._pad(20), fill="x")
        self._track(f"version {APP_VERSION}", self._fnt(9), self._pad(40))

        for item in items:
            if isinstance(item, tuple):
                self._add_section(item[0], item[1], expanded=(len(item) < 3 or item[2]))
            else:
                self._add_nav_item(item, indent=0)
        self._fit_width()
        self._fit_height(self._dispo)
        # Redimensionnement de la fenetre : on re-ajuste la verticale.
        self.bind("<Configure>", lambda e: self._fit_height(e.height))

    def _measure(self, text, font):
        try:
            return tkfont.Font(font=font).measure(text)
        except Exception:
            return len(text) * 8

    # ------------------------------------------------------ hauteur du menu
    def _besoin(self):
        """Hauteur totale reclamee par ce qui est reellement packs dans le menu.

        Les cadres de sections repliees ne sont pas packs : ils ne comptent pas,
        ce qui rend son air au menu quand l'utilisateur replie une section."""
        total = 0
        for w in self.winfo_children():
            if not w.winfo_manager():
                continue
            try:
                w.update_idletasks()
                total += w.winfo_reqheight()
                pady = w.pack_info().get("pady", 0)
                if isinstance(pady, (tuple, list)):
                    total += int(pady[0]) + int(pady[1])
                else:
                    total += 2 * int(pady)
            except Exception:
                pass
        return total

    def _rogne(self, r):
        """Retriche la verticale de `r` pixels par cote, sans jamais toucher aux
        polices et sans descendre sous une marge minimum lisible."""
        for w, base in self._row_lbls:
            w.configure(pady=max(1, base - r))
        for w, base in self._hdr_lbls:
            w.configure(pady=max(1, base - r))
        t, b = self._logo_pad
        self._logo_lbl.pack_configure(pady=(max(4, t - 2 * r), max(1, b - r)))
        self._ver_lbl.pack_configure(pady=(0, max(2, self._ver_pad - r)))
        self._rognage = r

    def fit_hauteur(self, dispo=None):
        """Met le menu a la hauteur disponible avec le rognage minimal.

        On part du besoin mesure sans rognage, on calcule ce que chaque pixel de
        rognage retire (2 px par ligne : haut + bas), on en deduit r, puis on
        verifie et on rectifie. Dans le cas courant une seule passe suffit."""
        dispo = int(dispo or self.winfo_height() or 0)
        if dispo <= 1 or self._fitting:
            return
        self._fitting = True
        try:
            gain = max(1, 2 * (len(self._row_lbls) + len(self._hdr_lbls)) + 3)
            self._rogne(0)
            besoin = self._besoin()
            r = 0
            if besoin > dispo:
                r = max(1, -(-(besoin - dispo) // gain))     # ceil
                for _ in range(14):
                    self._rogne(min(14, r))
                    if self._besoin() <= dispo or r >= 14:
                        break
                    r += 1
            self._rognage = min(14, r)
        finally:
            self._fitting = False

    def _fit_height(self, dispo=None):
        try:
            self.fit_hauteur(dispo)
        except Exception:
            pass

    def _track(self, text, font, extra=0):
        self._need = max(self._need, self._measure(text, font) + extra)

    def _fit_width(self, minimum=220, cap=340):
        """Largeur = largeur reellement demandee par la ligne la plus longue.

        On mesure apres layout (winfo_reqwidth) plutot qu'au seul metrique de police :
        le badge [Avance] est packed a droite DANS la meme ligne, il mange donc la
        place du libelle. Une sidebar figee a 220 px tronquait des noms des « grande ».
        """
        need = self._need
        for name, (row, border, lbl, fs) in self.nav_items.items():
            try:
                lbl.update_idletasks()
                w = lbl.winfo_reqwidth()
                for sib in row.winfo_children():
                    if sib is border or not isinstance(sib, tk.Label):
                        continue
                    if sib.pack_info().get("side") != "right":
                        continue
                    sib.update_idletasks()
                    w += sib.winfo_reqwidth() + self._pad(12)
                need = max(need, 4 + w + self._pad(14))
            except Exception:
                pass
        for sec in self._sections.values():
            try:
                h = sec["header"][2]
                h.update_idletasks()
                need = max(need, 4 + h.winfo_reqwidth() + self._pad(14))
            except Exception:
                pass
        self.configure(width=max(minimum, min(cap, need)))

    def _mk_row(self, parent, focusable=True):
        row = tk.Frame(parent, bg=self.colors["sidebar_bg"],
                      highlightbackground=self.colors["sidebar_bg"],
                      highlightcolor=self.colors["sidebar_accent"],
                      highlightthickness=1)
        row.pack(fill="x")
        row.configure(takefocus=1 if focusable else 0)
        return row

    def _add_nav_item(self, name, indent=0, subtitle=None, parent_section=None, badge=None):
        off = name in self.disabled
        parent = self if parent_section is None else self._sections[parent_section]["child_frame"]
        row = self._mk_row(parent, focusable=not off)
        row._td_name = name

        border = tk.Frame(row, bg=self.colors["sidebar_bg"], width=4)
        border.pack(side="left", fill="y")

        cursor = "arrow" if off else "hand2"
        if badge:
            bl = tk.Label(row, text=f"[{T(badge)}]", font=self._fnt(8),
                          bg=self.colors["sidebar_bg"],
                          fg=self.colors["sidebar_muted"], cursor=cursor)
            bl.pack(side="right", padx=(0, self._pad(12)))

        pad = self._pad(16 + indent * 16)
        font_size = 11 if indent == 0 else 10
        fg = self.colors["sidebar_muted"] if off else self.colors["sidebar_fg"]
        # 4 px de bordure + retrait gauche + texte + badge eventuel + marge droite
        badge_w = (self._measure(f"[{T(badge)}]", self._fnt(8)) + self._pad(12)) if badge else 0
        self._track(T(name), self._fnt(font_size), 4 + pad + badge_w + self._pad(12))
        if subtitle:
            self._track(T(subtitle), self._fnt(8), 4 + pad + badge_w + self._pad(12))

        box = tk.Frame(row, bg=self.colors["sidebar_bg"])
        box.pack(side="left", fill="x", expand=True)
        rpady = self._pad(7 if indent == 0 else 3)
        lbl = tk.Label(box, text=T(name), font=self._fnt(font_size),
                       bg=self.colors["sidebar_bg"], fg=fg, anchor="w",
                       padx=pad, pady=rpady, cursor=cursor)
        self._row_lbls.append((lbl, rpady))
        lbl.pack(anchor="w", fill="x")
        if subtitle:
            sub = tk.Label(box, text=T(subtitle), font=self._fnt(8),
                          bg=self.colors["sidebar_bg"], fg=self.colors["sidebar_muted"],
                          anchor="w", padx=pad, cursor=cursor)
            sub.pack(anchor="w", fill="x")

        self.nav_items[name] = (row, border, lbl, font_size)
        self._all.append(name)
        if parent_section is not None:
            self._parent[name] = parent_section
            self._sections[parent_section]["children"].append((row, border, lbl))
        if off:
            return
        self._wire(row, name)

    def _add_section(self, name, children, expanded=True):
        self._track("▾ " + T(name), self._fnt(11, "bold"), self._pad(16) + 4 + self._pad(12))
        header_row = self._mk_row(self)
        header_row._td_name = name

        border = tk.Frame(header_row, bg=self.colors["sidebar_bg"], width=4)
        border.pack(side="left", fill="y")

        hpady = self._pad(4)
        lbl = tk.Label(header_row, text=("▾ " if expanded else "▸ ") + T(name),
                      font=self._fnt(11, "bold"),
                      bg=self.colors["sidebar_bg"], fg=self.colors["sidebar_section"],
                      anchor="w", padx=self._pad(16), pady=hpady, cursor="hand2")
        self._hdr_lbls.append((lbl, hpady))
        lbl.pack(side="left", fill="x", expand=True)

        child_frame = tk.Frame(self, bg=self.colors["sidebar_bg"])
        if expanded:
            child_frame.pack(fill="x")

        self._sections[name] = {"header": (header_row, border, lbl), "children": [],
                               "expanded": expanded, "child_frame": child_frame}
        self._all.append(name)
        self._wire(header_row, name)

        for entry in children:
            if isinstance(entry, tuple):
                child_name, badge = entry
            else:
                child_name, badge = entry, None
            self._add_nav_item(child_name, indent=1, parent_section=name, badge=badge)

    def _wire(self, row, name):
        row.bind("<Button-1>", lambda e, n=name: self._click(n))
        row.bind("<Down>", lambda e: self._move(1, row))
        row.bind("<Up>", lambda e: self._move(-1, row))
        row.bind("<Return>", lambda e: self._enter(name))
        row.bind("<KP_Enter>", lambda e: self._enter(name))
        row.bind("<Left>", lambda e: self._arrow(name, False))
        row.bind("<Right>", lambda e: self._arrow(name, True))
        targets = list(row.winfo_children())
        for w in targets:
            targets.extend(w.winfo_children())
        for w in targets:
            w.bind("<Button-1>", lambda e, n=name: self._click(n))
            w.bind("<Enter>", lambda e, r=row, n=name: self._hover(r, n, True))
            w.bind("<Leave>", lambda e, r=row, n=name: self._hover(r, n, False))

    def _focus_row(self, name):
        r = self._row_of(name)
        if r is None:
            return
        try:
            r.focus_force()
        except tk.TclError:
            pass

    def _row_of(self, name):
        if name in self._sections:
            return self._sections[name]["header"][0]
        if name in self.nav_items:
            return self.nav_items[name][0]
        return None

    def _visible(self):
        out = []
        for n in self._all:
            if n in self.disabled:
                continue
            p = self._parent.get(n)
            if p is not None and not self._sections[p]["expanded"]:
                continue
            out.append(n)
        return out

    def _move(self, delta, cur):
        vis = self._visible()
        cur_name = getattr(cur, "_td_name", None)
        if cur_name not in vis:
            return "break"
        i = vis.index(cur_name) + delta
        if 0 <= i < len(vis):
            self._focus_row(vis[i])
        return "break"

    def _enter(self, name):
        if name in self._sections:
            self._toggle_section(name)
            self._focus_row(name)
        else:
            self.select(name)
        return "break"

    def _arrow(self, name, expand):
        if name in self._sections:
            if self._sections[name]["expanded"] != expand:
                self._toggle_section(name)
            self._focus_row(name)
            return "break"
        if expand:
            return "break"
        p = self._parent.get(name)
        if p is None:
            return "break"
        if self._sections[p]["expanded"]:
            self._toggle_section(p)
        self._focus_row(p)
        return "break"

    def _click(self, name):
        self._focus_row(name)
        if name in self._sections:
            self._toggle_section(name)
        else:
            self.select(name)

    def _toggle_section(self, name):
        sec = self._sections.get(name)
        if not sec:
            return
        if sec["expanded"]:
            try:
                cur = self.focus_displayof()
            except tk.TclError:
                cur = None
            w = cur
            while w is not None:
                if w is sec["child_frame"]:
                    self._focus_row(name)
                    break
                w = getattr(w, "master", None)
            sec["child_frame"].pack_forget()
        else:
            sec["child_frame"].pack(fill="x", after=sec["header"][0])
        sec["expanded"] = not sec["expanded"]
        sec["header"][2].configure(text=("▾ " if sec["expanded"] else "▸ ") + T(name))
        # Ouvrir une section change la hauteur necessaire : on re-ajuste (et le
        # menu se remet a respirer quand on replie).
        self._fit_height()

    def select(self, name):
        if name in self._sections:
            self._toggle_section(name)
            return
        if self.active == name:
            return
        if self.active:
            self._deactivate(self.active)
        self.active = name
        if name in self.nav_items:
            row, border, lbl, fs = self.nav_items[name]
            border.configure(bg=self.colors["sidebar_accent"])
            row.configure(bg=self.colors["sidebar_active_bg"])
            lbl.configure(bg=self.colors["sidebar_active_bg"], fg=self.colors["sidebar_active_fg"],
                         font=self._fnt(fs, "bold"))
            for w in row.winfo_children():
                for sub in w.winfo_children():
                    if isinstance(sub, tk.Label) and sub is not lbl:
                        sub.configure(bg=self.colors["sidebar_active_bg"])
        self.on_select(name)

    def _deactivate(self, name):
        if name in self.nav_items:
            row, border, lbl, fs = self.nav_items[name]
            border.configure(bg=self.colors["sidebar_bg"])
            row.configure(bg=self.colors["sidebar_bg"])
            lbl.configure(bg=self.colors["sidebar_bg"], fg=self.colors["sidebar_fg"],
                         font=self._fnt(fs))
            for w in row.winfo_children():
                for sub in w.winfo_children():
                    if isinstance(sub, tk.Label) and sub is not lbl:
                        sub.configure(bg=self.colors["sidebar_bg"])

    def _hover(self, row, name, entering):
        if self.active == name:
            return
        bg = self.colors["sidebar_hover_bg"] if entering else self.colors["sidebar_bg"]
        row.configure(bg=bg)
        for w in row.winfo_children():
            w.configure(bg=bg)
            for sub in w.winfo_children():
                sub.configure(bg=bg)


class ModeBanner(tk.Frame):
    """Banniere PARTAGEE des modes actifs. Le Mode Jeu et le Mode Discret sont
    totalement independants (activer l'un n'active jamais l'autre) mais ils
    partagent une seule et meme banniere : pas d'empilement de bandeaux."""

    MODES = (("game_mode_on", "🎮 Mode Jeu", "Mode Jeu", "rappels en pause"),
             ("stream_mode", "🕶️ Mode Discret", "Mode Discret", "noms et chemins masqués"))

    def __init__(self, master, ctx, on_exit, before=None):
        super().__init__(master, bg=ctx.theme["line"])
        self.ctx = ctx
        self.on_exit = on_exit
        self.before = before
        self.shown = False
        st = ttk.Style()
        st.configure("Banner.TButton", padding=(7, 0))
        self.inner = tk.Frame(self, bg=ctx.theme["card"])
        self.inner.pack(fill="x", padx=10, pady=0)
        self.lbl = tk.Label(self.inner, font=("Segoe UI", 9, "bold"), bg=ctx.theme["card"],
                           fg=ctx.theme["fg"], anchor="w")
        self.lbl.pack(side="left")
        self.btns = tk.Frame(self.inner, bg=ctx.theme["card"])
        self.btns.pack(side="right")

    def active(self):
        return [(k, lab, short, why) for k, lab, short, why in self.MODES if self.ctx.cfg.get(k)]

    def refresh(self):
        for w in self.btns.winfo_children():
            w.destroy()
        act = self.active()
        if not act:
            if self.shown:
                self.pack_forget()
                self.shown = False
            return
        self.lbl.configure(text=" · ".join(
            T("{label} actif ({why})").format(label=T(lab), why=T(why))
            for _, lab, _, why in act))
        for k, _, short, _ in act:
            ttk.Button(self.btns, text=T("Quitter {mode}").format(mode=T(short)),
                       style="Banner.TButton",
                       command=lambda key=k: self.on_exit(key)).pack(side="left", padx=(6, 0))
        if not self.shown:
            self.pack(side="top", fill="x", before=self.before)
            self.shown = True


class CleanCard(tk.Frame):
    def __init__(self, master, ctx, item, result=None, on_toggle=None):
        super().__init__(master, bg=ctx.theme["card"],
                        highlightbackground=ctx.theme["line"], highlightthickness=1)
        self.ctx = ctx
        self.item = item
        self.result = result
        self.on_toggle = on_toggle

        top = tk.Frame(self, bg=ctx.theme["card"])
        top.pack(fill="x", padx=12, pady=(8, 1))

        self.var = tk.BooleanVar(value=False)
        if result and not result.blocked and result.size > 0 and item.preselect:
            self.var.set(True)

        cb = tk.Checkbutton(top, variable=self.var, bg=ctx.theme["card"],
                            activebackground=ctx.theme["card"],
                            command=self._on_check)
        cb.pack(side="left")

        tk.Label(top, text=item.name, font=("Segoe UI", 10, "bold"),
                 bg=ctx.theme["card"], fg=ctx.theme["fg"]).pack(side="left", padx=(4, 0))

        self.status_lbl = tk.Label(top, text="", font=("Segoe UI", 10, "bold"),
                                   bg=ctx.theme["card"], fg=ctx.theme["fg"])
        self.status_lbl.pack(side="right")

        tk.Label(self, text=item.what, font=("Segoe UI", 9),
                 bg=ctx.theme["card"], fg=ctx.theme["muted"],
                 wraplength=700, justify="left", anchor="w").pack(fill="x", padx=32, pady=(0, 1))

        self.sub_lbl = tk.Label(self, text="", font=("Segoe UI", 8),
                                bg=ctx.theme["card"], fg=ctx.theme["muted"],
                                wraplength=700, justify="left", anchor="w")
        self.sub_lbl.pack(fill="x", padx=32, pady=(0, 8))

        self._update_display()

    def _update_display(self):
        r = self.result
        if not r:
            self.status_lbl.configure(text="Pas analysé", fg=self.ctx.theme["muted"])
            self.sub_lbl.configure(text="")
            return

        if r.blocked:
            wc = self.ctx.status_colors.get("warn", "#E67E22")
            badge = ("▲ Droits admin requis" if "administrateur" in r.blocked
                     else "▲ Programme ouvert")
            self.status_lbl.configure(text=badge, fg=wc)
            self.sub_lbl.configure(text=r.blocked, fg=wc)
        elif r.size > 0:
            if self.ctx.cfg.get("serenity"):
                self.status_lbl.configure(
                    text="Beaucoup de place à récupérer" if r.size >= 1 << 30
                        else "Un peu de place à récupérer",
                    fg=self.ctx.theme["fg"])
                self.sub_lbl.configure(text="")
            else:
                self.status_lbl.configure(text=human_size(r.size), fg=self.ctx.theme["fg"])
                self.sub_lbl.configure(text=f"{r.count} fichiers", fg=self.ctx.theme["muted"])
        else:
            self.status_lbl.configure(text="Rien à nettoyer", fg=self.ctx.theme["muted"])
            self.sub_lbl.configure(text="")

    def _on_check(self):
        if self.on_toggle:
            self.on_toggle()

    def set_result(self, result):
        self.result = result
        if result and not result.blocked and result.size > 0 and self.item.preselect:
            self.var.set(True)
        elif result and (result.blocked or result.size == 0):
            self.var.set(False)
        self._update_display()


def disk_bar(parent, theme, label, free, total, type_txt="", extra="", status=None, serene=False,
            compact=False):
    st = status or {}
    frame = tk.Frame(parent, bg=theme["card"], highlightbackground=theme["line"], highlightthickness=1)
    used = max(0, total - free)
    pct = used / total if total else 0
    if serene:
        calm = ("Tu as de la place" if pct < 0.75
                else "Encore un peu de place" if pct < 0.9
                else "La place commence à manquer")
    if compact:
        top = tk.Frame(frame, bg=theme["card"])
        top.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(top, text=label, font=("Segoe UI", 10, "bold"), bg=theme["card"],
                 fg=theme["fg"]).pack(side="left")
        if type_txt:
            tk.Label(top, text=type_txt, font=("Segoe UI", 8), bg=theme["card"],
                     fg=theme["muted"]).pack(side="right")
        tk.Label(frame, text=(calm if serene else
                             f"{human_size(free)} libres  ·  {int(round(pct * 100))} % utilisé"),
                 font=("Segoe UI", 9, "bold"), bg=theme["card"], fg=theme["fg"]).pack(fill="x", padx=10)
        cv = tk.Canvas(frame, height=12, bg=theme["card"], highlightthickness=0)
        cv.pack(fill="x", padx=10, pady=(2, 7))
        bar_h, r = 8, 4
    else:
        top = tk.Frame(frame, bg=theme["card"])
        top.pack(fill="x", padx=12, pady=(8, 2))
        tk.Label(top, text=label, font=("Segoe UI", 10, "bold"), bg=theme["card"], fg=theme["fg"]).pack(side="left")
        right = type_txt + (f"  ·  {extra}" if extra else "")
        if right:
            tk.Label(top, text=right, font=("Segoe UI", 9), bg=theme["card"], fg=theme["muted"]).pack(side="right")
        if serene:
            tk.Label(frame, text=calm,
                     font=("Segoe UI", 9, "bold"), bg=theme["card"], fg=theme["fg"]).pack(fill="x", padx=12)
        else:
            tk.Label(frame, text=f"{human_size(free)} libres sur {human_size(total)}  ·  {int(round(pct * 100))} % utilisé",
                     font=("Segoe UI", 9, "bold"), bg=theme["card"], fg=theme["fg"]).pack(fill="x", padx=12)
        cv = tk.Canvas(frame, height=16, bg=theme["card"], highlightthickness=0)
        cv.pack(fill="x", padx=12, pady=(2, 10))
        bar_h, r = 12, 6

    def draw(_e=None):
        cv.delete("all")
        w = max(cv.winfo_width(), 60)
        h = bar_h
        if serene:
            color = st.get("info", theme["accent"])
        else:
            g = theme.get("gauge") or {}
            color = (g.get("high", "#e5484d") if pct >= 0.9
                     else g.get("mid", "#f5a623") if pct >= 0.75
                     else g.get("ok", "#3fb950"))
        y1, y2 = 2, 2 + h

        def rrect(x1, x2, fill):
            x2 = max(x2, x1 + 2 * r)
            pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                   x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
            cv.create_polygon(pts, smooth=True, fill=fill, outline="")
        rrect(2, w - 2, theme["line"])
        fw = max(2 * r + 2, int((w - 4) * min(max(pct, 0.03), 1)))
        rrect(2, 2 + fw, color)
    cv.bind("<Configure>", draw)
    cv.after(30, draw)
    return frame


def preview_dialog(ctx, title, intro, lines, footer="", ok_text="Confirmer", cancel_text="Annuler"):
    title, intro, footer = T(title), T(intro), T(footer)
    lines = [T(l) for l in lines]
    ok_text, cancel_text = T(ok_text), T(cancel_text)
    win = tk.Toplevel(ctx.root)
    win.title(title)
    win.configure(bg=ctx.theme["bg"])
    win.transient(ctx.root)
    result = {"ok": False}
    wrap = int(640 * ctx.scale)
    ttk.Label(win, text=title, style="Sub.TLabel").pack(side="top", anchor="w", padx=18, pady=(16, 4))
    ttk.Label(win, text=ctx.mask(intro), wraplength=wrap, justify="left").pack(side="top", anchor="w", padx=18)
    bar = ttk.Frame(win)
    bar.pack(side="bottom", fill="x", padx=18, pady=14)
    if footer:
        ttk.Label(win, text=ctx.mask(footer), wraplength=wrap, justify="left",
                  style="Muted.TLabel").pack(side="bottom", anchor="w", padx=18)

    def yes():
        result["ok"] = True
        win.destroy()
    ttk.Button(bar, text=ok_text, style="Accent.TButton", command=yes).pack(side="right")
    ttk.Button(bar, text=cancel_text, command=win.destroy).pack(side="right", padx=8)
    txt = tk.Text(win, wrap="word", relief="flat", padx=12, pady=10, height=10,
                  bg=ctx.theme["card"], fg=ctx.theme["fg"])
    txt.insert("1.0", ctx.mask("\n".join(lines)))
    txt.configure(state="disabled")
    txt.pack(side="top", fill="both", expand=True, padx=18, pady=10)
    fit_window(win, ctx, 720, 480)
    win.grab_set()
    win.wait_window()
    return result["ok"]


def score_dialog(ctx, lines, title="Fiche de score du PC", serene_text=None, undo_pairs=None):
    title = T(title)
    lines = [T(l) for l in lines]
    serene_text = T(serene_text) if serene_text else None
    win = tk.Toplevel(ctx.root)
    win.title(title)
    win.configure(bg=ctx.theme["bg"])
    win.transient(ctx.root)
    serene = bool(ctx.cfg.get("serenity"))

    head = tk.Frame(win, bg=ctx.theme["bg"])
    head.pack(anchor="w", padx=24, pady=(20, 8))
    ico = tk.Canvas(head, width=22, height=22, bg=ctx.theme["bg"], highlightthickness=0)
    ok_col = ctx.status_colors.get("ok", ctx.theme["accent"])
    ico.create_oval(2, 2, 20, 20, outline=ok_col, width=2)
    ico.create_line(7, 11, 10, 15, 16, 7, fill=ok_col, width=2,
                   capstyle="round", joinstyle="round")
    ico.pack(side="left", padx=(0, 8))
    head_lbl = tk.Label(head, text=title, font=("Segoe UI", int(16 * ctx.scale), "bold"),
                       bg=ctx.theme["bg"], fg=ctx.theme["accent"])
    head_lbl.pack(side="left")

    lbl = tk.Label(win, text="", justify="left", font=("Segoe UI", int(12 * ctx.scale), "bold"),
                  bg=ctx.theme["bg"], fg=ctx.theme["fg"])
    lbl.pack(anchor="w", fill="x", padx=24, pady=8)
    auto_wrap(lbl)

    bar = tk.Frame(win, bg=ctx.theme["bg"])
    bar.pack(side="bottom", fill="x", padx=24, pady=16)
    ttk.Button(bar, text=T("Super !"), style="Accent.TButton", command=win.destroy).pack(side="right")
    undo_btn = None
    if undo_pairs:
        from Shared.Utils import quarantine

        def do_undo():
            undo_btn.state(["disabled"])
            undo_btn.configure(text=T("Annulation en cours…"))

            def done(r, e):
                if e or not r:
                    undo_btn.configure(text=T("Annulation impossible"))
                    return
                ok, missing, conflict = r
                txt = T("✓ {ok} élément(s) remis à leur place").format(ok=ok)
                if missing:
                    txt += T(" — {missing} introuvable(s)").format(missing=missing)
                if conflict:
                    txt += T(" — {conflict} déjà en place (ignorés)").format(conflict=conflict)
                undo_btn.configure(text=txt)
            run_bg(win, lambda: quarantine.restore(undo_pairs), done)

        undo_btn = ttk.Button(bar, text="Annuler ce rangement", command=do_undo)
        undo_btn.pack(side="right", padx=8)

    if serene:
        head_lbl.configure(text=T("Un bon rangement !"))
        lbl.configure(text=serene_text or T("Rangement terminé en douceur. Ton PC respire mieux, et toi aussi."))
        det = ttk.Button(win, text=T("Voir les détails (chiffres)"), command=lambda: _reveal())
        det.pack(anchor="w", padx=24, pady=(0, 8))
        shown = []

        def _reveal():
            det.pack_forget()
            step()

        def step(i=0):
            if i < len(lines) and win.winfo_exists():
                shown.append(ctx.mask(lines[i]))
                lbl.configure(text="\n\n".join(shown))
                win.after(550, lambda: step(i + 1))
    else:
        shown = []

        def step(i=0):
            if i < len(lines) and win.winfo_exists():
                shown.append(ctx.mask(lines[i]))
                lbl.configure(text="\n\n".join(shown))
                win.after(550, lambda: step(i + 1))
        step()

    fit_window(win, ctx, 560, 360)
    win.grab_set()
    win.wait_window()
