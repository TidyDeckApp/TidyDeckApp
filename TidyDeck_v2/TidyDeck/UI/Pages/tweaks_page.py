import time
import tkinter as tk
from tkinter import messagebox, ttk
from Core.Tweaks import tweaks
from Shared.Utils.common import IS_WINDOWS, open_windows_settings
from UI.components import Checklist, FlowFrame, preview_dialog, info_note, auto_wrap
from UI.restore_flow import with_restore_point
from UI.Pages.base import Page
from Shared.Utils.lang import T

BASE = {"active": ("✔ Appliqué", "ok"), "inactive": ("✕ Pas appliqué", "off"), "drift": ("⚠ Défait (mise à jour ?)", "warn")}


class TweaksPage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Calmer Windows",
                         "Coche un réglage pour l'appliquer, décoche-le pour revenir comme avant. "
                         "Tu vois un aperçu avant de valider, et seul ton compte est touché.")
        self.serene = bool(ctx.cfg.get("serenity"))

        # --- Bloc Sérénité : un seul bouton, une phrase, le détail replié ---
        self.serene_box = ttk.Frame(self)
        self.big_btn = ttk.Button(self.serene_box, text=T("✨  Calmer Windows en douceur"),
                                 style="Big.TButton", command=self.serene_apply)
        self.big_btn.pack(anchor="w", pady=(6, 8))
        # auto_wrap + fill="x" : sans wraplength ce libelle rend une seule ligne de
        # ~1164 px en « Grande » pour ~854 disponibles -> un tiers de la phrase
        # etait rogne. Il suit desormais la largeur reelle du bloc.
        auto_wrap(ttk.Label(self.serene_box, style="Muted.TLabel", justify="left",
                  text=T("Coupe les pubs et les suggestions de Windows en une seule fois. "
                       "Une seule confirmation, un point de restauration, et tout reste annulable."))).pack(
            anchor="w", fill="x", pady=(0, 10))
        self.detail_btn = ttk.Button(self.serene_box, text=T("▸ Voir le détail des réglages"),
                                    style="Flat.TButton", command=self._toggle_detail)

        # --- Bloc complet : tableau, boutons, clés de registre ---
        self.adv = ttk.Frame(self)
        info_frame = tk.Frame(self.adv, bg=ctx.theme["card"], highlightbackground=ctx.theme["line"], highlightthickness=1)
        info_frame.pack(fill="x", pady=(0, 8))
        info_note(info_frame, ctx.theme, ctx.status_colors["info"], "À quoi ça sert ?",
                 bold=True, bg=ctx.theme["card"]).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(info_frame, wraplength=850, justify="left", font=("Segoe UI", 10),
                 bg=ctx.theme["card"], fg=ctx.theme["muted"], text=T(
            "Windows affiche des pubs, des suggestions et des applis sponsorisées qui détournent ton attention.\n"
            "Cette page les coupe, une par une :\n"
            "• Moins de pubs dans le menu Démarrer, l'écran de verrouillage et Paramètres.\n"
            "• Plus d'applis sponsorisées installées toutes seules, et moins d'astuces « découvrez Windows ».\n"
            "• Chaque réglage est expliqué, annulable, et ne touche qu'à ton compte utilisateur.")).pack(anchor="w", padx=12, pady=(0, 8))
        # Le FlowFrame est cree DIRECTEMENT dans adv : un re-parentage (pack in=) laisse
        # ses enfants place() sans rendu -> grande zone vide a l'ecran.
        self.bar.destroy()
        self.bar = FlowFrame(self.adv)
        self.bar.pack(fill="x", pady=(0, 8))
        self.button(T("✔ Appliquer mes choix…"), self.apply, accent=True)
        self.button("↻ Actualiser (relire Windows)", self.refresh)
        self.button("🌙 Anti-lumière bleue (veilleuse Windows)", self._open_nightlight)
        self.list = Checklist(self.adv, ctx, (T("Réglage"), T("État")), on_toggle=self._toggled, box_only=True)
        self.list.pack(fill="both", expand=True)
        self.lists = {"all": self.list}

        if self.serene:
            self.subtitle_lbl.configure(
                text=T("Le calme en un clic. Rien ne change sans ton accord."))
            self.serene_box.pack(fill="x")
            self.detail_btn.pack(anchor="w")
        else:
            self.adv.pack(fill="both", expand=True)

    def _toggle_detail(self):
        if self.adv.winfo_manager():
            self.adv.pack_forget()
            self.detail_btn.configure(text=T("▸ Voir le détail des réglages"))
        else:
            self.adv.pack(fill="both", expand=True)
            self.detail_btn.configure(text=T("▾ Masquer le détail"))

    def serene_apply(self):
        on = [t.id for t in tweaks.TWEAKS if not tweaks.is_active(t)]
        if not on:
            self.say(T("✓ Windows est déjà calme : tous les réglages sont actifs."))
            return
        self._apply_ids(on)

    def on_show(self):
        if not getattr(self, "dirty", False) and time.time() - getattr(self, "_t", 0) > 10:
            self.refresh()

    def _toggled(self, iid, new):
        self.dirty = True
        s = tweaks.status(tweaks.BY_ID[iid])
        info = T(BASE[s][0])
        if s == "active" and not new:
            info = T("↩ Sera remis comme avant")
        elif s != "active" and new:
            info = T("✔ Sera appliqué")
        self.list.update_row(iid, info=info)
        return True

    def refresh(self):
        self.dirty, self._t = False, time.time()
        rows = []
        for t in tweaks.TWEAKS:
            s = tweaks.status(t)
            info, st = T(BASE[s][0]), BASE[s][1]
            detail = (T("Ce que c'est : {v0}\nBénéfice : {v1}\nRisque : {v2}\n\n"
                      "Ce qui sera écrit dans le registre (vérifiable avec regedit) :\n").format(v0=T(t.what), v1=T(t.benefit), v2=T(t.risk))
                      + "\n".join("  • " + l for l in tweaks.current_text(t))
                      + T("\n\nSi tu décoches : ") + "\n".join("  • " + l for l in tweaks.revert_text(t))
                      + T("\n\nAnnulable : oui (Journaux > Annuler)."))
            name = T(t.name) if t.group == "Anti-distraction" else f"{T(t.name)}  ·  {T(t.group)}"
            rows.append(dict(id=t.id, name=name, info=info, status=st, reg=(t.hive, t.values[0].key),
                             checked=s in ("active", "drift"), detail=detail))
        self.list.set_rows(rows)
        if self.serene:
            restants = [t for t in tweaks.TWEAKS if not tweaks.is_active(t)]
            if not restants:
                self.big_btn.configure(text=T("✓  Windows est déjà calme"))
                self.big_btn.state(["disabled"])
            else:
                self.big_btn.configure(text=(T("✨  Calmer Windows en douceur  ·  {v0} réglage à activer") if len(restants) == 1
                                                        else T("✨  Calmer Windows en douceur  ·  {v0} réglages à activer")).format(v0=len(restants)))
                self.big_btn.state(["!disabled"])
        d = tweaks.drift()
        self.say(T("⚠ {v0} réglage a été défait depuis ta dernière application : il est recoché, "
                 "clique « Appliquer » pour le remettre." if len(d) == 1 else
                 "⚠ {v0} réglages ont été défaits depuis ta dernière application : ils sont recochés, "
                 "clique « Appliquer » pour les remettre.").format(v0=len(d)) if d else "")

    def _open_nightlight(self):
        if open_windows_settings("nightlight"):
            self.say(T("Paramètres Windows ouverts sur « Lumière nocturne ». Rien n'est modifié ici : "
                     "c'est une page de consultation."))
        else:
            self.say(T("Cette page n'existe pas sur ce PC. Elle se trouve dans "
                     "Paramètres > Système > Affichage."))

    def _p(self, n, sing, plur):
        return f"{n} {sing if n == 1 else plur}"

    def apply(self):
        checked = set(i for l in self.lists.values() for i in l.checked_ids())
        on = [t.id for t in tweaks.TWEAKS if t.id in checked and not tweaks.is_active(t)]
        off = [t.id for t in tweaks.TWEAKS if t.id not in checked and tweaks.is_active(t)]
        forget = [t.id for t in tweaks.TWEAKS if t.id not in checked and tweaks.status(t) == "drift"]
        if forget and not on and not off:
            tweaks.forget(forget)
            self.say(T("D'accord : je ne te signalerai plus ces réglages."))
            self.refresh()
            return
        if not on and not off:
            messagebox.showinfo("TidyDeck", "Rien à changer : ta sélection correspond déjà à l'état de Windows.\n"
                                "Coche un réglage « Pas appliqué » pour l'appliquer, ou décoche un réglage « Appliqué » "
                                "pour le remettre comme avant.")
            return
        self._apply_ids(on, off, forget)

    def _apply_ids(self, on, off=(), forget=()):
        lines = []
        if on:
            lines.append(T("▶ À APPLIQUER"))
            for i in on:
                lines.append(f"■ {tweaks.BY_ID[i].name}")
                lines += ["    " + l for l in tweaks.current_text(tweaks.BY_ID[i])]
        if off:
            lines.append(T("\n↩ À REMETTRE COMME AVANT"))
            for i in off:
                lines.append(f"■ {tweaks.BY_ID[i].name}")
                lines += ["    " + l for l in tweaks.revert_text(tweaks.BY_ID[i])]
        if not preview_dialog(self.ctx, T("Aperçu des réglages"),
                              T("TidyDeck va d'abord tenter de créer un point de restauration Windows, puis écrire "
                              "ces valeurs et les VÉRIFIER en relisant le registre :"), lines,
                              "Tout reste annulable depuis les Journaux.", "Oui, appliquer"):
            return
        with_restore_point(self.ctx, self, lambda: self._do(list(on), list(off), list(forget)))

    def _do(self, on, off, forget):
        try:
            bad = []
            if on:
                bad += tweaks.apply(on, self.ctx.journal)
            if off:
                bad += tweaks.revert(off, self.ctx.journal)
            if forget:
                tweaks.forget(forget)
            if bad:
                self.say(T("⚠ Windows n'a pas conservé : {names}").format(names=", ".join(tweaks.BY_ID[i].name for i in bad)))
            else:
                self.say(T("{a}, {b} — vérifié en relisant le registre.").format(a=self._p(len(on), T("réglage appliqué"), T("réglages appliqués")), b=self._p(len(off), T("réglage remis comme avant"), T("réglages remis comme avant"))))
        except OSError as e:
            self.say(T("Erreur : {err}").format(err=e))
        self.refresh()
