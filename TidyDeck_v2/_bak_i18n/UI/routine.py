"""Nettoyage doux recommandé / « Bouton magique » : une seule validation, que des choses sûres."""
import time
from Shared.Constants.catalog import build_catalog
from Shared.Utils.common import human_size
from Core.Health import cleaner
from Core.Tweaks import tweaks
from UI.components import run_bg, preview_dialog, score_dialog

# LISTE BLANCHE DU MODE EXPRESS : seule cette liste peut être rangée sans aperçu.
# Jamais la Corbeille, jamais les fichiers Windows (temp_win), jamais le démarrage,
# les services ou le registre. Toute nouvelle entrée doit être explicitement ajoutée ici.
EXPRESS_WHITELIST = {"temp_user", "chrome", "edge", "brave", "opera", "firefox"}


def gentle_clean(ctx, page, after=None, express=False):
    items = [i for i in build_catalog() if i.simple and i.preselect and not i.special]
    if express:
        items = [i for i in items if i.id in EXPRESS_WHITELIST]
    page.busy("Je regarde ce qui peut être rangé…", "gentle")

    def scanned(res, err):
        page.idle()
        if err:
            page.say("Je n'ai pas réussi à analyser pour l'instant. Rien n'a été modifié.")
            return
        sel = [r for r in res.values() if not r.blocked and r.size > 0]
        if express:
            sel = [r for r in sel if r.item.id in EXPRESS_WHITELIST]
        if not sel:
            page.say("✨ Rien à faire : ton PC est déjà tranquille. Bravo ! 🌿")
            return
        total = sum(r.size for r in sel)
        lines = [f"{r.item.icon}  {r.item.name}" for r in sel]
        if not express and not preview_dialog(ctx, "Nettoyage doux (recommandé)",
                              f"J'ai repéré environ {human_size(total)} sans risque. Rien n'est supprimé tout de suite : "
                              f"tu peux tout annuler pendant {ctx.cfg['quarantine_days']} jours.", lines,
                              "Je n'inclus ni la Corbeille, ni les programmes ouverts, ni rien de sensible.",
                              "Oui, ranger en douceur ✨"):
            page.say("D'accord, on ne touche à rien. 🌿")
            return
        page.busy("Je range pour toi…", "gentle_clean")
        run_bg(ctx.root, lambda: cleaner.clean(sel, ctx.journal), done)

    def done(res, err):
        page.idle()
        if err:
            page.say("Oups, quelque chose s'est mal passé. Rien de grave : tu peux regarder le Journal.")
            return
        ctx.cfg["last_calm"] = time.strftime("%Y-%m-%d %H:%M:%S")
        ctx.save()
        msg = f"✨ PC apaisé ✓ — {human_size(res['moved'])} mis de côté, annulable depuis les Journaux."
        d = tweaks.drift()
        if d:
            msg += f" (Au passage : {len(d)} réglage(s) Windows ont été défaits — onglet Calmer Windows.)"
        page.say(msg)
        if res["moved"] or res["n"]:
            score_dialog(ctx, [
                f"{human_size(res['moved'])} mis de côté ({res['n']} éléments)",
                f"Rien n'est perdu : annulable pendant {ctx.cfg['quarantine_days']} jours",
                "Ton PC respire mieux — bien joué !",
                "Tu viens de faire un geste concret pour ton confort. Ça compte."
            ], serene_text="Un bon rangement ! Ton PC respire mieux, et toi aussi. "
                         "Rien n'est perdu : tout est annulable.",
               undo_pairs=res.get("pairs"))
            if hasattr(page, "show_undo") and res.get("pairs"):
                page.show_undo(res["pairs"])
        if after:
            after()

    run_bg(ctx.root, lambda: cleaner.scan_all(items), scanned)
