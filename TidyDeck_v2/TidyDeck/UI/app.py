import time
import tkinter as tk
from tkinter import messagebox, ttk
from Services.Logger.journal import Journal
from Shared.Utils import config, quarantine, privacy, registry
from Shared.Utils.common import IS_WINDOWS, APP_NAME, relaunch_as_admin, appliquer_icone, identifier_processus_tache
from Shared.Utils import instance
from UI import theme
from UI import tray
from UI.components import ScrollFrame, Sidebar, ModeBanner
from UI.Home.home import HomePage
from UI.Pages.check_page import ChecksPage
from UI.Pages.services_page import ServicesPage
from UI.Pages.tweaks_page import TweaksPage
from UI.Pages.debloat_page import DebloatPage
from UI.Pages.clean_page import CleanPage
from UI.Pages.startup_page import StartupPage
from UI.Pages.storage_page import StoragePage
from UI.Pages.games_page import GamesPage
from UI.Pages.journal_page import JournalPage
from UI.Pages.reminders_page import RemindersPage
from UI.Pages.settings_page import SettingsPage, ConfigPage
from UI.Pages.profile_page import ProfilePage
from UI.Pages.about_page import AboutPage
from UI.Pages.info_pc_page import InfoPCPage
from UI.PreInstall.welcome import show_welcome
from UI import routine
from UI.toast import show_toast
from Services.Reminders.scheduler import Scheduler, MESSAGES
from Services.Reminders import autostart
from Shared.Utils import winui
from Shared.Utils import lang, tkmsg
from Core.Health.report import run_checks
from Shared.Utils.lang import T

NAV_ITEMS = [
    "Accueil",
    ("Nettoyer", ["Nettoyage", "Fichiers et résidus"]),
    ("Régler Windows", ["Calmer Windows", "Démarrage",
                        ("Services", "Admin"), ("Applications préinstallées", "Avancé")]),
    "Jeu et live",
    "Rappels bien-être",
    ("Suivre", ["État des lieux", "Journaux", "Info PC"]),
    ("Paramètres", ["Apparence et modes", "Configuration", "Sauvegarde et transfert"]),
    "À propos",
]
TOAST_KEY = r"Software\Microsoft\Windows\CurrentVersion\PushNotifications"
ADVANCED_ONLY = {"Applications préinstallées"}
SERENE_TOP = ["Accueil", "Nettoyage", "Calmer Windows",
              "Rappels bien-être", "État des lieux", "Jeu et live"]


def flatten_nav(items):
    out = []
    for it in items:
        if isinstance(it, tuple):
            for c in it[1]:
                out.append((c[0], c[1]) if isinstance(c, tuple) else (c, None))
        else:
            out.append((it, None))
    return out


class Context:
    root = cfg = journal = theme = status_colors = symbols = app = None

    def __init__(self):
        self.cache, self.loading = {}, set()

    @property
    def advanced(self):
        return self.cfg["advanced"]

    @property
    def scale(self):
        return theme.SIZES[self.cfg["text_size"]]

    def mask(self, text):
        return privacy.mask(text, self.cfg["stream_mode"])

    def save(self):
        config.save(self.cfg)

    def ask_admin(self, confirm=True):
        if not IS_WINDOWS:
            messagebox.showinfo("TidyDeck", T("Les droits administrateur ne concernent que Windows."))
            return
        if confirm and not messagebox.askyesno("Droits administrateur",
                                               "TidyDeck va se relancer avec les droits administrateur.\n"
                                               "Windows te demandera ton accord. Continuer ?"):
            return
        if relaunch_as_admin():
            self.root.destroy()
        else:
            messagebox.showwarning("TidyDeck", T("La demande a été refusée ou n'a pas pu partir. Rien n'a changé."))


class App:
    def __init__(self, minimized=False):
        self.ctx = Context()
        self.ctx.cfg = config.load()
        lang.set_lang(self.ctx.cfg.get("lang", "fr"))
        tkmsg.installe()
        self.ctx.journal = Journal()
        autostart.reparer_entree_orpheline(self.ctx.journal)
        if not self.ctx.cfg["installed"]:
            self.ctx.cfg["installed"] = time.strftime(T("%Y-%m-%d %H:%M:%S"))
        quarantine.purge(self.ctx.cfg["quarantine_days"])
        instance.activer_dpi()          # avant tk.Tk() : apres, c'est trop tard
        identifier_processus_tache()    # idem : la tache doit porter l'identite TidyDeck
        self.root = self.ctx.root = tk.Tk()
        self.ctx.app = self
        self.title = T("{v0} — Le ménage de ton PC, tout en douceur").format(v0=APP_NAME)
        self.root.title(self.title)
        appliquer_icone(self.root)   # avant la 1re image : apres, la tache a deja sa plume Tk
        self.root.bind("<FocusIn>", lambda e: self.root.title(self.title))
        self._size_window()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.pages = {}
        self.current_page = None
        self.build()
        if self.ctx.cfg["first_run"]:
            self.ctx.cfg["first_run"] = False
            self.ctx.save()
            show_welcome(self.ctx, self.rebuild)
        else:
            self.root.after(2500, self.maybe_remind)
        self.scheduler = Scheduler(self.ctx, self.show_reminder, self.flash_reminder)
        self.scheduler.start()
        if minimized:
            self.root.after(400, self.root.iconify)
        self.prefetch()
        self.root.after(600, self._poll_tray)

    def prefetch(self):
        """Rechauffe les lectures lentes pendant que l'utilisateur prend ses marques.

        Le relevé matériel coute ~4,5 s (PowerShell + WMI) : il ne doit jamais tomber
        sur le chemin d'un clic. On le lance des que la fenetre est en place ; il est
        en plus garde 12 h sur disque, donc en pratique la page « Info PC » s'affiche
        deja prte. En cas de clic pendant le relevé, le verrou du module evite de
        payer deux fois."""
        from Core.SystemInfo import hardware
        from UI.components import run_bg

        def job():
            try:
                hardware.load()
            except Exception:  # noqa: BLE001  un prefetch rate n'est pas grave
                pass
        run_bg(self.root, job, lambda r, e: None)

    def _size_window(self):
        if getattr(self, "_sized_once", False):
            # Rebuild (theme/taille/mode) : on garde la position actuelle de la fenetre,
            # on ne re-centre pas et on ne reimplose pas la geometrie par defaut.
            return
        self._sized_once = True
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        # Taille standard identique pour tous les modes (stabilite de l'interface) :
        # 1200 x 750, reduite seulement si l'ecran est plus petit.
        w, h = min(1200, sw - 20), min(750, sh - 40)
        self._fen_h = h
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 3)}")
        self.root.minsize(min(900, w), min(600, h))

    def on_close(self):
        # L'option « pres de l'horloge » prime sur le choix de la croix : cocher
        # la case doit visiblement changer le comportement, sinon elle est
        # trompeuse quand « Fermer TidyDeck » est coche par ailleurs.
        if self.ctx.cfg.get("tray") and tray.afficher(T("Ouvrir TidyDeck"), T("Quitter TidyDeck")):
            self.root.withdraw()      # discret pres de l'horloge ; l'icene ramene la fenetre
            return
        if self.ctx.cfg["close_action"] == "minimize":
            self.root.iconify()
        else:
            tray.retirer()
            self.root.destroy()

    # --- zone de notification (option « pres de l'horloge ») ---
    def _poll_tray(self):
        for ev in tray.events():
            if ev == "restore":
                self._tray_restore()
            elif ev == "quit":
                self._tray_quit()
        self.root.after(250, self._poll_tray)

    def _tray_restore(self):
        tray.retirer()
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except tk.TclError:
            pass

    def _tray_quit(self):
        tray.retirer()
        self.root.destroy()

    def build(self, keep=None):
        self.ctx.theme, self.ctx.status_colors, self.ctx.symbols = theme.apply(self.root, self.ctx.cfg)

        self.main = tk.Frame(self.root, bg=self.ctx.theme["bg"])
        self.main.pack(fill="both", expand=True)

        self.sidebar = Sidebar(self.main, self._nav_items(), self._on_nav, self.ctx.theme,
                             disabled=self._nav_disabled(), scale=self.ctx.scale,
                             hauteur=getattr(self, "_fen_h", 750))
        self.sidebar.pack(side="left", fill="y")

        self.content = tk.Frame(self.main, bg=self.ctx.theme["bg"])
        self.content.pack(side="left", fill="both", expand=True, padx=(16, 0))
        self._wrap_avail = 0
        self.content.bind("<Configure>", self._on_content_resize)

        # Banniere PARTAGEE (Mode Jeu + Mode Discret) placee dans la zone de contenu :
        # la sidebar garde toute sa hauteur. Les pages vivent dans pages_host, ce qui
        # garde la banniere au-dessus d'elles quel que soit l'ordre des pack().
        self.pages_host = tk.Frame(self.content, bg=self.ctx.theme["bg"])
        self.pages_host.pack(side="top", fill="both", expand=True)
        self.banner = ModeBanner(self.content, self.ctx, self.exit_mode, before=self.pages_host)
        self.banner.refresh()

        ctx = self.ctx
        self.pages["Accueil"] = HomePage(self.pages_host, ctx, self.goto)
        self.pages["Nettoyage"] = CleanPage(self.pages_host, ctx)
        self.pages["Fichiers et résidus"] = StoragePage(self.pages_host, ctx)
        self.pages["Calmer Windows"] = TweaksPage(self.pages_host, ctx)
        self.pages["Démarrage"] = StartupPage(self.pages_host, ctx)
        self.pages["Services"] = ServicesPage(self.pages_host, ctx)
        self.pages["Applications préinstallées"] = DebloatPage(self.pages_host, ctx)
        self.pages["Jeu et live"] = GamesPage(self.pages_host, ctx)
        self.pages["Rappels bien-être"] = RemindersPage(self.pages_host, ctx)
        self.pages["État des lieux"] = ChecksPage(self.pages_host, ctx, lambda: run_checks(ctx.cfg["serenity"]), "health")
        self.pages["Journaux"] = JournalPage(self.pages_host, ctx)
        self.pages["Info PC"] = InfoPCPage(self.pages_host, ctx)
        self.pages["Apparence et modes"] = SettingsPage(self.pages_host, ctx, self.apply_appearance)
        self.pages["Configuration"] = ConfigPage(self.pages_host, ctx, self.apply_appearance)
        self.pages["Sauvegarde et transfert"] = ProfilePage(self.pages_host, ctx)
        self.pages["À propos"] = AboutPage(self.pages_host, ctx)

        target = keep if keep in self.pages else "Accueil"
        self.goto(target)

    def goto(self, name):
        if name not in self.pages:
            return
        self.sidebar.select(name)

    def _fit_wrap(self, page):
        from UI.components import clamp_wrap
        avail = getattr(self, "_wrap_avail", 0)
        if not avail:
            w = self.content.winfo_width()
            avail = max(60, w - 48)
        clamp_wrap(page, avail)

    def _on_content_resize(self, e):
        self._wrap_avail = max(60, e.width - 48)
        if self.current_page in self.pages:
            self._fit_wrap(self.pages[self.current_page])

    def _nav_disabled(self):
        return set() if self.ctx.advanced else set(ADVANCED_ONLY)

    def _nav_items(self):
        if not self.ctx.cfg.get("serenity"):
            return NAV_ITEMS
        rest = []
        for name, badge in flatten_nav(NAV_ITEMS):
            if name in SERENE_TOP:
                continue
            rest.append((name, badge) if badge else name)
        return list(SERENE_TOP) + [("PLUS", rest, False)]

    def _on_nav(self, name):
        if name in ADVANCED_ONLY and not self.ctx.advanced:
            return
        if name not in self.pages:
            for item in NAV_ITEMS:
                if isinstance(item, tuple) and item[0] == name and item[1]:
                    name = item[1][0]
                    break
            else:
                return
        for page in self.pages.values():
            page.pack_forget()
        self.current_page = name
        page = self.pages[name]
        page.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self._fit_wrap(page)
        if hasattr(page, "on_show"):
            page.on_show()

    def current(self):
        return self.current_page

    def apply_appearance(self, prev=None):
        if prev is not None and self.ctx.cfg["stream_mode"] != prev.get("stream_mode"):
            self._stream_toasts(self.ctx.cfg["stream_mode"])
        self.rebuild()

    def exit_mode(self, key):
        """Sortie d'un mode depuis la banniere : un clic, aucune confirmation.
        Le Mode Jeu et le Mode Discret sont independants : quitter l'un laisse l'autre."""
        self.ctx.cfg[key] = False
        self.ctx.save()
        if key == "stream_mode":
            self._stream_toasts(False)
        self.rebuild()

    def _stream_toasts(self, on):
        if not IS_WINDOWS:
            return
        cfg = self.ctx.cfg
        try:
            if on:
                if messagebox.askyesno("Mode Discret", "Couper aussi les notifications Windows pendant que le mode est actif ?\n"
                                       "(Elles seront rétablies quand tu quitteras ce mode.)"):
                    cfg["toasts_prev"] = registry.read("HKCU", TOAST_KEY, "ToastEnabled")
                    cfg["toasts_prev"] = 1 if cfg["toasts_prev"] is None else cfg["toasts_prev"]
                    registry.write("HKCU", TOAST_KEY, "ToastEnabled", 0)
            elif cfg.get("toasts_prev") is not None:
                registry.write("HKCU", TOAST_KEY, "ToastEnabled", cfg["toasts_prev"])
                cfg["toasts_prev"] = None
        except OSError as e:
            messagebox.showwarning("TidyDeck", T("Impossible de modifier les notifications : {err}").format(err=e))

    def maybe_remind(self):
        cfg = self.ctx.cfg
        if not cfg["reminder"] or cfg["first_run"]:
            return
        fmt = T("%Y-%m-%d %H:%M:%S")

        def days(ts):
            return (time.time() - time.mktime(time.strptime(ts, fmt))) / 86400 if ts else 9999
        if days(cfg.get("last_calm") or cfg["installed"]) >= 30 and days(cfg.get("last_reminder")) >= 30:
            cfg["last_reminder"] = time.strftime(fmt)
            self.ctx.save()
            if messagebox.askyesno("Petit rappel doux 🌿", "Ça fait un moment : on fait un petit nettoyage de 10 secondes ?\n\n"
                                   "(Une seule validation, rien n'est supprimé tout de suite, tout est annulable.)"):
                self.goto("Accueil")
                routine.gentle_clean(self.ctx, self.pages["Accueil"], self.pages["Accueil"].on_show)

    def show_reminder(self, kind, test=False):
        title, text, countdown = MESSAGES[kind]
        show_toast(self.ctx, title, text, countdown, on_snooze=None if test else (lambda: self.scheduler.snooze(kind)))

    def flash_reminder(self, kind):
        winui.flash_taskbar(self.root)
        self.root.title(f"{self.title}   ·   {MESSAGES[kind][0]}")

    def rebuild(self):
        keep = self.current()
        self.ctx.save()
        lang.set_lang(self.ctx.cfg.get("lang", "fr"))
        tkmsg.installe()   # la langue peut changer à chaud
        self._size_window()
        for w in self.root.winfo_children():
            w.destroy()
        self.build(keep)
        self.root.focus_set()

    def run(self):
        self.root.mainloop()
