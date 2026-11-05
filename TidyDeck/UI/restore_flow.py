"""Point de restauration avant une action sensible, avec les bons choix proposés à chaque échec."""
from tkinter import messagebox
from Services import restore
from UI.components import run_bg
from Shared.Utils.lang import T


def with_restore_point(ctx, page, proceed):
    """Appelle proceed() quand on peut continuer (point créé, ou l'utilisateur choisit de continuer sans)."""
    def attempt(enable=False):
        page.busy(T("Création du point de restauration"), "restore")
        run_bg(ctx.root, lambda: restore.create_restore_point(enable_if_needed=enable),
               lambda r, e: result(r, enable))

    def result(r, tried_enable):
        page.idle()
        ok, msg, code = r if r else (False, "Erreur inconnue.", "other")
        if ok:
            page.say("🛟 " + msg)
            proceed()
            return
        if code == "admin":
            a = messagebox.askyesnocancel(
                "Point de restauration", msg + T("\n\nOui = relancer en administrateur\nNon = continuer sans point "
                "de restauration (tout reste annulable avec TidyDeck)\nAnnuler = ne rien faire"))
            if a:
                ctx.ask_admin(confirm=False)
            elif a is False:
                proceed()
            else:
                page.say(T("Rien n'a été modifié."))
            return
        if not tried_enable:
            a = messagebox.askyesnocancel(
                "Point de restauration", msg + T("\n\nSouvent, la « Protection du système » est désactivée sur ce PC. "
                "Oui = l'activer sur ton disque Windows puis réessayer\nNon = continuer sans point de restauration\n"
                "Annuler = ne rien faire"))
            if a:
                attempt(True)
            elif a is False:
                proceed()
            else:
                page.say(T("Rien n'a été modifié."))
            return
        if messagebox.askyesno("Point de restauration", msg + T("\n\nContinuer quand même ? (annulable avec TidyDeck)")):
            proceed()
        else:
            page.say(T("Rien n'a été modifié."))
    attempt()
