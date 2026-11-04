from UI.components import Checklist
from UI.Pages.base import Page


def check_rows(ctx, checks):
    rows = []
    checks = sorted(checks, key=lambda c: {"info": 0, "warn": 1, "ok": 2}.get(c.status, 3))   # ℹ INFOS en haut
    for i, c in enumerate(checks):
        row = dict(id=str(i), name=f"{ctx.symbols[c.status]}   {c.name}", info=c.detail, status=c.status,
                   detail=f"Ce que je vois : {c.detail}\n\nQue faire : {c.advice or 'Rien, tout va bien.'}")
        # Emplacement verifiable : transmis tel quel au bouton « Ouvrir » du Checklist.
        path = getattr(c, "path", "")
        if path:
            row["folders"] = [path]
        if getattr(c, "settings", ""):
            row["settings"] = c.settings
        if getattr(c, "shell", ""):
            row["shell"] = c.shell
        if getattr(c, "reg", ()):
            row["reg"] = tuple(c.reg)
        if getattr(c, "location", ""):
            row["location"] = c.location
        rows.append(row)
    return rows


class ChecksPage(Page):
    """Constat + « que faire » (chargé en arrière-plan, avec cache)."""

    def __init__(self, master, ctx, provider, key):
        super().__init__(master, ctx, "État des lieux",
                         "Un état des lieux clair, et pour chaque point : que faire. Les infos sont en haut.")
        self.provider, self.key = provider, key
        self.button("↻ Actualiser", lambda: self.refresh(True), accent=True)
        self.list = Checklist(self, ctx, ("Contrôle", "Ce que je vois"), checkable=False)
        self.list.pack(fill="both", expand=True)

    def on_show(self):
        self.refresh()

    def refresh(self, force=False):
        if force:
            self.say("Actualisation…")
        # La cle de cache inclut le mode Serenite : un changement de mode invalide
        # immediatement l'ancien rapport (sinon on voit l'ancien ton pendant le TTL).
        key = f"{self.key}:{'s' if self.ctx.cfg.get('serenity') else 'n'}"
        self.load(key, self.provider, lambda r: (self.list.set_rows(check_rows(self.ctx, r)), self.say("") if force else None),
                  ttl=60, force=force)
