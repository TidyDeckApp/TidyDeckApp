from tkinter import ttk
from Core.Health import report
from UI.Pages.check_page import ChecksPage
from UI.Pages.services_page import ServicesPage
from UI.Pages.tweaks_page import TweaksPage
from UI.Pages.clean_page import CleanPage
from UI.Pages.startup_page import StartupPage
from UI.Pages.storage_page import StoragePage


class HealthPage(ttk.Frame):
    """Santé PC > Constat · Services · Calmer Windows · Nettoyage · Démarrage · Rangement."""

    def __init__(self, master, ctx):
        super().__init__(master)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.subs = [
            ("❤ Constat", ChecksPage(self.nb, ctx, lambda: report.run_checks(ctx.cfg["serenity"]), "health")),
            ("⚙ Services", ServicesPage(self.nb, ctx)),
            ("🔕 Calmer Windows", TweaksPage(self.nb, ctx)),
            ("🧹 Nettoyage", CleanPage(self.nb, ctx)),
            ("🚀 Démarrage", StartupPage(self.nb, ctx)),
            ("🗂 Rangement", StoragePage(self.nb, ctx)),
        ]
        for title, page in self.subs:
            self.nb.add(page, text=f" {title} ")
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.on_show())

    def on_show(self):
        try:
            page = self.subs[self.nb.index("current")][1]
        except Exception:
            return
        if hasattr(page, "on_show"):
            page.on_show()
