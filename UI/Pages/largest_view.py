"""Vue « Les plus gros fichiers / plus gros dossiers ».

Lecture seule : aucune suppression, aucune écriture, rien n'est consigné au journal.
Elle vit DANS la page « Fichiers et résidus » (pas d'entrée de menu en plus) et
reste sous « Plus » en mode Sérénité."""
import os
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
from Core.Storage import storage
from Shared.Utils.common import human_size, select_in_explorer
from UI.components import ScrollFrame, run_bg, auto_wrap
from Shared.Utils.lang import T


def _p(n, sing, plur):
    """« 1 fichier » / « 4 fichiers » : le pluriel honest, sans « (s) »."""
    return f"{n} {sing}" if n == 1 else f"{n} {plur}"


def calm_size(n):
    """Taille arrondie et rassurante : « environ 4 Go », jamais un chiffre précis.
    Unités et mot « environ » suivent la langue (EN : about 4 GB)."""
    from Shared.Utils.lang import get_lang
    u = ("KB", "MB", "GB") if get_lang() == "en" else ("Ko", "Mo", "Go")
    n = float(n or 0)
    if n < 1024:
        return T("quelques octets")
    ko, mo, go = n / 1024.0, n / 1048576.0, n / 1073741824.0
    if mo < 1:
        return T("environ {v0}").format(v0=f"{max(1, int(round(ko)))} {u[0]}")
    if go < 1:
        if mo >= 100:
            return T("environ {v0}").format(v0=f"{int(round(mo / 50.0) * 50)} {u[1]}")
        return T("environ {v0}").format(v0=f"{max(1, int(round(mo)))} {u[1]}")
    if go >= 10:
        return T("environ {v0}").format(v0=f"{int(round(go / 5.0) * 5)} {u[2]}")
    return T("environ {v0}").format(v0=f"{max(1, int(round(go)))} {u[2]}")


class WidgetCollapsible(ttk.Frame):
    """Bloc repliable contenant de vrais widgets (le Collapsible standard ne prend
    que des lignes de texte)."""

    def __init__(self, master, title):
        super().__init__(master)
        self.title, self.open = title, False
        self.btn = ttk.Button(self, text=f"▸ {title}", style="Flat.TButton", command=self.toggle)
        self.btn.pack(fill="x")
        self.body = ttk.Frame(self)

    def toggle(self):
        self.open = not self.open
        self.btn.configure(text=("▾ " if self.open else "▸ ") + self.title)
        if self.open:
            self.body.pack(anchor="w", fill="x", pady=(2, 4))
        else:
            self.body.pack_forget()


class _Tooltip:
    """Petite infobulle maison (ttk n'en fournit pas) : apparaît après un court
    survol, disparaît au départ du curseur ou au clic."""

    def __init__(self, w, texte, th):
        self.w, self.texte, self.th = w, texte, th
        self.tip, self._after = None, None
        w.bind("<Enter>", self._enter, add="+")
        w.bind("<Leave>", self._hide, add="+")
        w.bind("<Button-1>", self._hide, add="+")

    def _enter(self, _e):
        self._kill()
        try:
            self._after = self.w.after(450, self._show)
        except tk.TclError:
            pass

    def _kill(self):
        if self._after is not None:
            try:
                self.w.after_cancel(self._after)
            except Exception:
                from Shared.Utils import depannage
                depannage.noter("UI/Pages/largest_view.py:85")
            self._after = None

    def _show(self):
        self._after = None
        try:
            if not self.w.winfo_exists():
                return
            self.tip = tk.Toplevel(self.w)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry("+%d+%d" % (self.w.winfo_rootx(),
                                              self.w.winfo_rooty() + self.w.winfo_height() + 3))
            tk.Label(self.tip, text=self.texte, bg=self.th["card"], fg=self.th["fg"],
                     font=("Segoe UI", 9), padx=8, pady=4,
                     highlightbackground=self.th["line"], highlightthickness=1).pack()
        except tk.TclError:
            self.tip = None

    def _hide(self, _e=None):
        self._kill()
        if self.tip is not None:
            try:
                self.tip.destroy()
            except Exception:
                from Shared.Utils import depannage
                depannage.noter("UI/Pages/largest_view.py:109")
            self.tip = None


class LargestView(ttk.Frame):
    """Les 20 plus gros fichiers et les 20 plus gros dossiers directs d'une zone."""

    def __init__(self, master, ctx, on_close=None):
        super().__init__(master, padding=0)
        self.ctx = ctx
        self.on_close_cb = on_close
        th = ctx.theme
        self.serene = bool(ctx.cfg.get("serenity"))
        self.adv = bool(ctx.cfg.get("advanced"))
        self.cancel = threading.Event()
        self.busy = False
        self.stack = []
        self.zone = list(storage.largest_zone())
        self.limit = tk.IntVar(value=20)
        self.shown = 5 if self.serene else 20
        self.data = {"files": [], "folders": [], "system": [], "scanned": 0, "cancelled": False}
        self._fitmap = {}
        self._last_fit = {}
        self._busy_fit = False
        self._barw = max(90, int(150 * float(ctx.scale)))
        self._after = None
        self._build()
        self._after = self.after(60, self._kick)
        self.bind("<Destroy>", self._on_destroy)

    def _kick(self):
        self._after = None
        if not self.winfo_exists():
            return
        self.start_scan()

    def _on_destroy(self, e):
        if e.widget is not self:
            return
        self.cancel.set()
        try:
            self.busy_bar.stop()
        except Exception:
            from Shared.Utils import depannage
            depannage.noter("UI/Pages/largest_view.py:152")
        if self._after is not None:
            try:
                self.after_cancel(self._after)
            except Exception:
                from Shared.Utils import depannage
                depannage.noter("UI/Pages/largest_view.py:157")
            self._after = None

    # ------------------------------------------------------------------ build
    def _build(self):
        th = self.ctx.theme
        top = ttk.Frame(self)
        top.pack(fill="x")
        # Pas de bouton « Retour » : on change d'onglet avec les boutons du haut.
        self.up_btn = ttk.Button(top, text=T("↑ Remonter"), style="Flat.TButton", command=self.go_up)
        # Volontairement pas pack ici : le bouton n'apparaît qu'après un
        # double-clic dans un dossier (voir _update_up).
        self.re_btn = ttk.Button(top, text=T("🔄 Relancer l'analyse"), style="Flat.TButton",
                                 command=lambda: self.start_scan(self.zone))
        self.re_btn.pack(side="right")
        self.stop_btn = ttk.Button(top, text=(T("Ça suffit") if self.serene else "Arrêter"),
                                  style="Flat.TButton", command=self.stop_scan)

        self.intro_lbl = auto_wrap(ttk.Label(self, style="Muted.TLabel", justify="left"))
        self.intro_lbl.pack(anchor="w", fill="x", pady=(6, 0))
        # Barre de chargement (mode « indeterminate ») : le scan peut durer,
        # une barre annonce qu'il se passe quelque chose, sans texte redondant
        # avec le sous-titre de la page.
        self.busy_bar = ttk.Progressbar(self, mode="indeterminate", length=260)
        self._set_intro()

        self._build_options()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, pady=(8, 0))
        fp = ttk.Frame(self.nb)
        self.nb.add(fp, text=T("📄 Fichiers"))
        self.files_sf = ScrollFrame(fp, th["bg"])
        self.files_sf.pack(fill="both", expand=True)
        dp = ttk.Frame(self.nb)
        self.nb.add(dp, text=T("📁 Dossiers"))
        self.fold_sf = ScrollFrame(dp, th["bg"])
        self.fold_sf.pack(fill="both", expand=True)
        # Un <Configure> ne doit JAMAIS modifier la geometrie lui-meme : Tk rentre
        # alors dans sa propre passe de layout et peut planter. On note la largeur
        # demandee et on applique a l'idle.
        self._pending, self._sched_after = {}, None
        # On ecoute le canvas, pas le cadre interieur : la largeur du canvas est
        # pilotee par la fenetre, jamais par le contenu. Ecouter le contenu cree
        # une boucle de retour (le fit change la largeur demandee -> Configure).
        self.files_sf.canvas.bind("<Configure>", lambda e: self._schedule(self.files_sf, e.width))
        self.fold_sf.canvas.bind("<Configure>", lambda e: self._schedule(self.fold_sf, e.width))

        self.foot = auto_wrap(ttk.Label(self, style="Muted.TLabel", justify="left"))
        self.foot.pack(anchor="w", fill="x", pady=(6, 0))
        self._set_foot()

    def _build_options(self):
        """Nombre de lignes : avancé uniquement.
        En Sérénité + Avancé, présentation Sérénité et options planquées dans un
        bloc « Options » replié."""
        if not self.adv:
            self.opts = None
            return
        if self.serene:
            holder = WidgetCollapsible(self, "Options")
            holder.pack(fill="x", pady=(6, 0))
            body = holder.body
            self.opts = holder
        else:
            body = ttk.Frame(self)
            body.pack(fill="x", pady=(6, 0))
            self.opts = None
        row2 = ttk.Frame(body)
        row2.pack(anchor="w", fill="x", pady=(4, 0))
        ttk.Label(row2, text=T("Nombre de lignes :"), style="Muted.TLabel").pack(side="left")
        for v in (20, 50, 100):
            ttk.Radiobutton(row2, text=str(v), value=v, variable=self.limit,
                            command=self._limit_changed).pack(side="left", padx=(6, 0))

    def _limit_changed(self):
        self.shown = self._cap()
        self.start_scan(self.zone)

    def _cap(self):
        try:
            return int(self.limit.get()) if self.adv else 20
        except Exception:
            return 20

    # ------------------------------------------------------------------ scan
    def start_scan(self, zones=None):
        if self.busy:
            return
        if zones is not None:
            self.zone = [str(z) for z in zones if z]
        self.cancel.clear()
        self.busy = True
        self.stop_btn.pack(side="right", padx=(8, 0))
        self.re_btn.state(["disabled"])
        self.busy_bar.pack(after=self.intro_lbl, anchor="w", pady=(6, 0))
        self.busy_bar.start(12)
        zones, lim = list(self.zone), self._cap()
        run_bg(self.ctx.root,
               lambda: storage.find_largest(zones, cancel=self.cancel.is_set, limit=lim),
               self._scanned)

    def stop_scan(self):
        self.cancel.set()

    def _scanned(self, res, err):
        self.busy = False
        try:
            self.busy_bar.stop()
            self.busy_bar.pack_forget()
            self.stop_btn.pack_forget()
            self.re_btn.state(["!disabled"])
        except tk.TclError:
            return
        if err is not None:
            self._set_intro(T("L'analyse n'a pas pu aboutir : {v0}. Rien n'a été modifié.").format(v0=err))
            return
        self.data = res or self.data
        self._render()

    # ------------------------------------------------------------------ nav
    def go_up(self):
        if not self.stack:
            return
        self.zone = self.stack.pop()
        self.start_scan()

    def drill(self, path):
        self.stack.append(list(self.zone))
        self.zone = [path]
        self.start_scan()

    def close(self):
        self.cancel.set()
        if self.on_close_cb:
            self.on_close_cb()

    # --------------------------------------------------------------- render
    def _shown(self):
        return max(1, min(self.shown, self._cap()))

    def _render(self):
        n = self._shown()
        files = self.data.get("files", [])
        folds = self.data.get("folders", [])
        self._fill(self.files_sf, files[:n], "file",
                  more=len(files) > n, total=len(files))
        self._fill(self.fold_sf, folds[:n], "dir",
                  more=len(folds) > n, total=len(folds))
        self._update_up()
        self._set_foot()
        # Les rangees sont creees avant que la largeur utile ne soit connue : on
        # re-mesure a l'idle, sinon les chemins resteraient vides.
        self.after_idle(self._refit_all)

    def _schedule(self, sf, width):
        self._pending[id(sf)] = (sf, int(width))
        if self._sched_after is None:
            self._sched_after = self.after_idle(self._flush)

    def _flush(self):
        self._sched_after = None
        todo = list(self._pending.values())
        self._pending.clear()
        for sf, w in todo:
            try:
                if w > 1 and sf.inner.winfo_exists():
                    self._refit(sf, w)
            except tk.TclError:
                pass

    def _refit_all(self):
        if not self.winfo_exists():
            return
        for sf in (self.files_sf, self.fold_sf):
            w = sf.canvas.winfo_width()
            if w > 1:
                self._refit(sf, w)

    def _fill(self, sf, items, kind, more=False, total=0):
        inner = sf.inner
        for w in inner.winfo_children():
            w.destroy()
        self._fitmap[sf.inner] = []
        self._last_fit.pop(id(sf.canvas), None)
        if not items:
            ttk.Label(inner, text=(T("Aucun fichier trouvé dans cette zone.") if kind == "file"
                                  else "Aucun dossier dans cette zone."),
                      style="Muted.TLabel").pack(anchor="w", padx=8, pady=12)
            return
        for it in items:
            if kind == "file":
                size, path, mtime = it
                self._row(inner, os.path.basename(path), path, size, mtime, kind)
            else:
                name, path, size = it
                # Date du dossier lui-meme (celle que l'Explorateur affiche),
                # calculée seulement pour les lignes affichees.
                try:
                    mtime = os.stat(path).st_mtime
                except OSError:
                    mtime = None
                self._row(inner, name, path, size, mtime, kind)
        if more:
            ttk.Button(inner, text=(T("Voir plus ({v0} au total)").format(v0=total) if self.serene
                                   else T("Afficher les {v0} premiers").format(v0=self._cap())),
                       style="Flat.TButton", command=self.show_more).pack(anchor="w", padx=8, pady=(6, 10))

    def _row(self, parent, name, path, size, mtime, kind):
        th = self.ctx.theme
        system = size is None
        row = tk.Frame(parent, bg=th["card"], highlightbackground=th["line"], highlightthickness=1)
        row.pack(fill="x", pady=2)
        for c in range(4):
            row.grid_columnconfigure(c, weight=0)

        if system:
            stxt = "—"
        elif self.serene:
            stxt = calm_size(size)
        else:
            stxt = human_size(size)
        sz = tk.Label(row, text=stxt, bg=th["card"], fg=th["fg"],
                      font=("Segoe UI", 10, "bold"), anchor="e")
        sz.grid(row=0, column=1, sticky="e", padx=(0, 8))

        dtxt = "—" if not mtime else time.strftime(T("%d/%m/%Y"), time.localtime(mtime))
        dl = tk.Label(row, text=dtxt, bg=th["card"], fg=th["muted"], font=("Segoe UI", 9))
        dl.grid(row=0, column=2, sticky="e", padx=(0, 8))

        # Lecture seule : aucun bouton de suppression, jamais.
        acts = ttk.Frame(row)
        acts.grid(row=0, column=3, sticky="e", padx=(0, 6))
        if system:
            ttk.Label(acts, text=T("Système, ne pas toucher"), style="Muted.TLabel").pack(side="left")
        else:
            ttk.Button(acts, text=T("📂 Ouvrir l'emplacement"), style="Flat.TButton",
                       command=lambda p=path: self.open_loc(p)).pack(side="left", padx=(0, 4))
            if self.adv:
                cop = ttk.Button(acts, text=T("Copier"), style="Flat.TButton",
                                 command=lambda p=path: self.copy_path(p))
                _Tooltip(cop, T("Copier le chemin d'accès"), th)
                cop.pack(side="left")

        cell = tk.Frame(row, bg=th["card"])
        cell.grid(row=0, column=0, sticky="w", padx=(8, 0))
        nl = tk.Label(cell, text=name, bg=th["card"], fg=th["fg"],
                      font=("Segoe UI", 10, "bold"), anchor="w")
        nl.pack(side="left")
        pl = tk.Label(cell, text=T(""), bg=th["card"], fg=th["muted"],
                      font=("Segoe UI", 9), anchor="w")
        pl.pack(side="left", padx=(8, 0))
        # fixed est recalcule au moment du fit : a la creation, les widgets ne
        # sont pas encore passes en layout et winfo_reqwidth() renvoie des valeurs
        # minuscules (152 au lieu de ~520), ce qui faisait exploser la rangee.
        self._fitmap.setdefault(parent, []).append(
            dict(row=row, nl=nl, pl=pl, sz=sz, dl=dl, acts=acts,
                 full=name, pfull=self._disp_path(path)))
        if kind == "dir" and not system:
            row.bind("<Double-1>", lambda e, p=path: self.drill(p))
        nl.bind("<Button-1>", lambda e, p=path: self._show_path(p))

    def _disp_path(self, path):
        return self.ctx.mask(os.path.dirname(str(path)))

    def _refit(self, sf, width):
        """Repartit la largeur reelle dans la ligne.

        Taille, date et boutons ne se compressent pas : sans repartition explicite,
        c'est le nom qui absorbait tout le manque et il tombait a 37 px en
        « Grande » + avance. On fige donc les deux largeurs ici."""
        jobs = self._fitmap.get(sf.inner)
        if not jobs:
            return
        # Garde anti-boucle : _refit modifie la geometrie de la rangee, ce qui
        # declenche un nouveau <Configure> sur le cadre interieur. Sans ca, on
        # sature la pile (aller-retour Configure -> refit -> Configure).
        width = int(width)
        if self._busy_fit or self._last_fit.get(id(sf.canvas)) == width:
            return
        self._busy_fit = True
        try:
            self._apply_fit(sf, width)
        finally:
            self._busy_fit = False
        self._last_fit[id(sf.canvas)] = width

    def _apply_fit(self, sf, width):
        jobs = self._fitmap.get(sf.inner) or []
        # Le cadre interieur peut se retrouver plus large que le canvas (il herite
        # d'une largeur anterieure) : on le re-fige sur la largeur visible.
        try:
            sf.canvas.itemconfigure(sf._win, width=width)
        except Exception:
            from Shared.Utils import depannage
            depannage.noter("UI/Pages/largest_view.py:451")
        for j in jobs:
            fixed = (j["sz"].winfo_reqwidth() + j["dl"].winfo_reqwidth()
                     + j["acts"].winfo_reqwidth() + 36)
            name_w = max(70, int(width) - fixed)
            j["row"].grid_columnconfigure(0, minsize=name_w, weight=0)
            # -20 : padding gauche de la cellule (8) + padding gauche du chemin (8)
            # + marge d'arrondi. Sans ca, la cellule depassait la colonne de ~12 px.
            inner_w = max(56, name_w - 20)
            na = max(24, int(inner_w * 0.62))
            pa = max(24, inner_w - na)
            j["nl"].configure(text=_clip(j["full"], na, j["nl"]))
            j["pl"].configure(text=_clip(j["pfull"], pa, j["pl"]))

    # ------------------------------------------------------------- actions
    def show_more(self):
        self.shown = self._cap()
        self._render()

    def copy_path(self, path):
        try:
            self.clipboard_clear()
            self.clipboard_append(str(path))
            self._show_path(path, copied=True)
        except Exception:
            from Shared.Utils import depannage
            depannage.noter("UI/Pages/largest_view.py:476")

    def open_loc(self, path):
        if self.ctx.cfg.get("stream_mode"):
            if not messagebox.askyesno(
                    "Mode Discret",
                    "L'Explorateur Windows affichera ton vrai chemin à l'écran.\n"
                    "Quelqu'un qui regarde ton écran pourra le lire.\n\nOuvrir quand même ?"):
                return
        if not select_in_explorer(path):
            self._show_path(path, fail=True)

    def _show_path(self, path, copied=False, fail=False):
        if fail:
            self.foot.configure(text=self.ctx.mask(
                T("⚠ Impossible d'ouvrir cet emplacement (droits insuffisants ou chemin introuvable). "
                "Rien n'a été modifié.")))
            return
        if copied:
            self.foot.configure(text=self.ctx.mask(T("Chemin copié : {v0}").format(v0=path)))
            return
        self.foot.configure(text=self.ctx.mask(f"Emplacement : {path}"))

    # -------------------------------------------------------------- texts
    def _set_intro(self):
        if self.serene:
            self.intro_lbl.configure(
                text=T("Voici ce qui prend le plus de place. Rien n'est supprimé."))
        else:
            self.intro_lbl.configure(text=T("Les plus gros éléments de ta zone."))

    def _set_foot(self):
        d = self.data
        fin = (T("rien dans le journal") if self.serene
               else T("aucune suppression, rien dans le journal"))
        base = (f"{_p(d.get('scanned', 0), T('fichier parcouru'), T('fichiers parcourus'))} · "
               f"{_p(len(d.get('files', [])), T('fichier'), T('fichiers'))} {T('et')} "
               f"{_p(len(d.get('folders', [])), T('dossier classé'), T('dossiers classés'))} · "
               + fin)
        if d.get("cancelled"):
            base = T("Analyse arrêtée. ") + base
        locked = d.get("locked") or []
        if locked:
            noms = ", ".join(n for n, _ch in locked[:3])
            plus = T(" (+{v0} autres)").format(v0=len(locked) - 3) if len(locked) > 3 else ""
            base += (T(" · {v0} "
                    "non classé{v1} : {v2}{v3} "
                    "— il faudrait les droits administrateur").format(v0=_p(len(locked), 'dossier inaccessible', 'dossiers inaccessibles'), v1=T('s') if len(locked) != 1 else '', v2=noms, v3=plus))
        nuage = d.get("nuage") or 0
        if nuage:
            if nuage == 1:
                base += (T(" · 1 fichier « dans le nuage » non compté : il n'occupe pas de "
                         "place sur ce disque, l'ouvrir le téléchargerait"))
            else:
                base += (T(" · {v0} fichiers « dans le nuage » non comptés : ils n'occupent "
                         "pas de place sur ce disque, les ouvrir les téléchargerait").format(v0=nuage))
        self.foot.configure(text=self.ctx.mask(base))

    def _update_up(self):
        try:
            if self.stack:
                self.up_btn.pack(side="left", padx=(8, 0))
            else:
                self.up_btn.pack_forget()
        except tk.TclError:
            pass


def _clip(text, px, widget):
    """Tronque `text` pour qu'il tienne dans `px` pixels, avec un point de
    suspension. Mesure reelle via la police du widget."""
    text = str(text)
    try:
        f = tkfont.Font(font=widget.cget("font"))
    except Exception:
        return text
    if f.measure(text) <= px:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if f.measure(text[:mid] + "…") <= px:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "…"
