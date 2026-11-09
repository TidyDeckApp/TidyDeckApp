"""Nettoyage doux recommandé / « Bouton magique » : une seule validation, que des choses sûres."""
import time
from Shared.Constants.catalog import build_catalog
from Shared.Utils.common import human_size, mots_espace
from Core.Health import cleaner
from Core.Tweaks import tweaks
from UI.components import run_bg, preview_dialog, score_dialog
from Shared.Utils.lang import T

# LISTE BLANCHE DU MODE EXPRESS : seule cette liste peut être rangée sans aperçu.
# Jamais la Corbeille, jamais les fichiers Windows (temp_win), jamais le démarrage,
# les services ou le registre. Toute nouvelle entrée doit être explicitement ajoutée ici.
EXPRESS_WHITELIST = {"temp_user", "chrome", "edge", "brave", "opera", "firefox"}


def gentle_clean(ctx, page, after=None, express=False):
    items = [i for i in build_catalog() if i.simple and i.preselect and not i.special]
    if express:
        items = [i for i in items if i.id in EXPRESS_WHITELIST]
    page.busy(T("Je regarde ce qui peut être rangé…"), "gentle")

    def scanned(res, err):
        page.idle()
        if err:
            page.say(T("Je n'ai pas réussi à analyser pour l'instant. Rien n'a été modifié."))
            return
        sel = [r for r in res.values() if not r.blocked and r.size > 0]
        if express:
            sel = [r for r in sel if r.item.id in EXPRESS_WHITELIST]
        if not sel:
            if ctx.cfg.get("serenity"):
                page.say(T("Il n'y avait rien à ranger pour l'instant."))
            else:
                page.say(T("✨ Rien à faire : ton PC est déjà tranquille. Bravo ! 🌿"))
            return
        total = sum(r.size for r in sel)
        lines = [f"{r.item.icon}  {r.item.name}" for r in sel]
        if not express and not preview_dialog(ctx, T("Nettoyage doux (recommandé)"),
                              T("J'ai repéré environ {v0} sans risque. Rien n'est supprimé tout de suite : "
                              "tu peux tout annuler pendant {v1} jours.").format(v0=human_size(total), v1=ctx.cfg['quarantine_days']), lines,
                              T("Je n'inclus ni la Corbeille, ni les programmes ouverts, ni rien de sensible."),
                              T("Oui, ranger en douceur ✨")):
            page.say(T("D'accord, on ne touche à rien. 🌿"))
            return
        page.busy(T("Je range pour toi…"), "gentle_clean")
        run_bg(ctx.root, lambda: cleaner.clean(sel, ctx.journal), done)

    def done(res, err):
        page.idle()
        if err:
            page.say(T("Oups, quelque chose s'est mal passé. Rien de grave : tu peux regarder le Journal."))
            return
        ctx.cfg["last_calm"] = time.strftime(T("%Y-%m-%d %H:%M:%S"))
        ctx.save()
        serene = bool(ctx.cfg.get("serenity"))
        if serene:
            msg = T("✨ PC apaisé ✓ — tout est mis de côté en douceur, annulable depuis les Journaux.")
        else:
            msg = T("✨ PC apaisé ✓ — {v0} mis de côté, annulable depuis les Journaux.").format(v0=human_size(res['moved']))
        d = tweaks.drift()
        if d:
            _n = len(d)
            if serene:
                msg += T(" (Au passage : des réglages Windows ont été défaits — onglet Calmer Windows.)")
            else:
                msg += (T(" (Au passage : {v0} réglage Windows a été défait — onglet Calmer Windows.)") if _n == 1
                        else T(" (Au passage : {v0} réglages Windows ont été défaits — onglet Calmer Windows.)")).format(v0=_n)
        page.say(msg)
        if res["moved"] or res["n"]:
            score_dialog(ctx, [
                T("{v0} mis de côté ({v1} éléments)").format(v0=human_size(res['moved']), v1=res['n']),
                T("Rien n'est perdu : annulable pendant {v0} jours").format(v0=ctx.cfg['quarantine_days']),
                T("Ton PC respire mieux — bien joué !"),
                T("Tu viens de faire un geste concret pour ton confort. Ça compte.")
            ], serene_text=T("Tu as libéré {espace}. Rien n'est perdu : tu peux tout remettre "
                             "pendant {j} jours.").format(espace=mots_espace(res['moved']),
                                                          j=ctx.cfg['quarantine_days']),
               undo_pairs=res.get("pairs"))
            if hasattr(page, "show_undo") and res.get("pairs"):
                page.show_undo(res["pairs"])
        if after:
            after()

    run_bg(ctx.root, lambda: cleaner.scan_all(items), scanned)
