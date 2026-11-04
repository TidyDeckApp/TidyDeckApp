import time
import tkinter as tk
from tkinter import messagebox, ttk
from Core.Tweaks import tweaks
from Shared.Utils.common import IS_WINDOWS, open_windows_settings
from UI.components import Checklist, FlowFrame, preview_dialog, info_note, auto_wrap
from UI.restore_flow import with_restore_point
from UI.Pages.base import Page

BASE = {"active": ("✔ Appliqué", "ok"), "inactive": ("✕ Pas appliqué", "off"), "drift": ("⚠ Défait (mise à jour ?)", "warn")}


class TweaksPage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Calmer Windows",
                         "Coche un réglage pour l'appliquer, décoche-le pour revenir comme avant. "
                         "Tu vois un aperçu avant de valider, et seul ton compte est touché.")
        self.serene = bool(ctx.cfg.get("serenity"))

        # --- Bloc Sérénité : un seul bouton, une phrase, le détail replié ---
        self.serene_box = ttk.Frame(self)
        self.big_btn = ttk.Button(self.serene_box, text="✨  Calmer Windows en douceur",
                                 style="Big.TButton", command=self.serene_apply)
        self.big_btn.pack(anchor="w", pady=(6, 8))
        # auto_wrap + fill="x" : sans wraplength ce libelle rend une seule ligne de
        # ~1164 px en « Grande » pour ~854 disponibles -> un tiers de la phrase
        # etait rogne. Il suit desormais la largeur reelle du bloc.
        auto_wrap(ttk.Label(self.serene_box, style="Muted.TLabel", justify="left",
                  text="Coupe les pubs et les suggestions de Windows en une seule fois. "
                       "Une seule confirmation, un point de restauration, et tout reste annulable.")).pack(
            anchor="w", fill="x", pady=(0, 10))
        self.detail_btn = ttk.Button(self.serene_box, text="▸ Voir le détail des réglages",
                                    style="Flat.TButton", command=self._toggle_detail)

        # --- Bloc complet : tableau, boutons, clés de registre ---
        self.adv = ttk.Frame(self)
        info_frame = tk.Frame(self.adv, bg=ctx.theme["card"], highlightbackground=ctx.theme["line"], highlightthickness=1)
        info_frame.pack(fill="x", pady=(0, 8))
        info_note(info_frame, ctx.theme, ctx.status_colors["info"], "À quoi ça sert ?",
                 bold=True, bg=ctx.theme["card"]).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(info_frame, wraplength=850, justify="left", font=("Segoe UI", 10),
                 bg=ctx.theme["card"], fg=ctx.theme["muted"], text=(
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
        self.button("✔ Appliquer mes choix…", self.apply, accent=True)
        self.button("↻ Actualiser (relire Windows)", self.refresh)
        self.button("🌙 Anti-lumière bleue (veilleuse Windows)", self._open_nightlight)
        self.list = Checklist(self.adv, ctx, ("Réglage", "État"), on_toggle=self._toggled, box_only=True)
        self.list.pack(fill="both", expand=True)
        self.lists = {"all": self.list}

        if self.serene:
            self.subtitle_lbl.configure(
                text="Le calme en un clic. Rien ne change sans ton accord.")
            self.serene_box.pack(fill="x")
            self.detail_btn.pack(anchor="w")
        else:
            self.adv.pack(fill="both", expand=True)

    def _toggle_detail(self):
        if self.adv.winfo_manager():
            self.adv.pack_forget()
            self.detail_btn.configure(text="▸ Voir le détail des réglages")
        else:
            self.adv.pack(fill="both", expand=True)
            self.detail_btn.configure(text="▾ Masquer le détail")

    def serene_apply(self):
        on = [t.id for t in tweaks.TWEAKS if not tweaks.is_active(t)]
        if not on:
            self.say("✓ Windows est déjà calme : tous les réglages sont actifs.")
            return
        self._apply_ids(on)

    def on_show(self):
        if not getattr(self, "dirty", False) and time.time() - getattr(self, "_t", 0) > 10:
            self.refresh()

    def _toggled(self, iid, new):
        self.dirty = True
        s = tweaks.status(tweaks.BY_ID[iid])
        info = BASE[s][0]
        if s == "active" and not new:
            info = "↩ Sera remis comme avant"
        elif s != "active" and new:
            info = "✔ Sera appliqué"
        self.list.update_row(iid, info=info)
        return True

    def refresh(self):
        self.dirty, self._t = False, time.time()
        rows = []
        for t in tweaks.TWEAKS:
            s = tweaks.status(t)
            info, st = BASE[s]
            detail = (f"Ce que c'est : {t.what}\nBénéfice : {t.benefit}\nRisque : {t.risk}\n\n"
                      "Ce qui sera écrit dans le registre (vérifiable avec regedit) :\n"
                      + "\n".join("  • " + l for l in tweaks.current_text(t))
                      + "\n\nSi tu décoches : " + "\n".join("  • " + l for l in tweaks.revert_text(t))
                      + "\n\nAnnulable : oui (Journaux > Annuler).")
            name = t.name if t.group == "Anti-distraction" else f"{t.name}  ·  {t.group}"
            rows.append(dict(id=t.id, name=name, info=info, status=st, reg=(t.hive, t.values[0].key),
                             checked=s in ("active", "drift"), detail=detail))
        self.list.set_rows(rows)
        if self.serene:
            restants = [t for t in tweaks.TWEAKS if not tweaks.is_active(t)]
            if not restants:
                self.big_btn.configure(text="✓  Windows est déjà calme")
                self.big_btn.state(["disabled"])
            else:
                self.big_btn.configure(text=f"✨  Calmer Windows en douceur  ·  {len(restants)} réglage(s) à activer")
                self.big_btn.state(["!disabled"])
        d = tweaks.drift()
        self.say(f"⚠ {len(d)} réglage(s) ont été défaits depuis ta dernière application : ils sont recochés, "
                 "clique « Appliquer » pour les remettre." if d else "")

    def _open_nightlight(self):
        if open_windows_settings("nightlight"):
            self.say("Paramètres Windows ouverts sur « Lumière nocturne ». Rien n'est modifié ici : "
                     "c'est une page de consultation.")
        else:
            self.say("Cette page n'existe pas sur ce PC. Elle se trouve dans "
                     "Paramètres > Système > Affichage.")

    def apply(self):
        checked = set(i for l in self.lists.values() for i in l.checked_ids())
        on = [t.id for t in tweaks.TWEAKS if t.id in checked and not tweaks.is_active(t)]
        off = [t.id for t in tweaks.TWEAKS if t.id not in checked and tweaks.is_active(t)]
        forget = [t.id for t in tweaks.TWEAKS if t.id not in checked and tweaks.status(t) == "drift"]
        if forget and not on and not off:
            tweaks.forget(forget)
            self.say("D'accord : je ne te signalerai plus ces réglages.")
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
            lines.append("▶ À APPLIQUER")
            for i in on:
                lines.append(f"■ {tweaks.BY_ID[i].name}")
                lines += ["    " + l for l in tweaks.current_text(tweaks.BY_ID[i])]
        if off:
            lines.append("\n↩ À REMETTRE COMME AVANT")
            for i in off:
                lines.append(f"■ {tweaks.BY_ID[i].name}")
                lines += ["    " + l for l in tweaks.revert_text(tweaks.BY_ID[i])]
        if not preview_dialog(self.ctx, "Aperçu des réglages",
                              "TidyDeck va d'abord tenter de créer un point de restauration Windows, puis écrire "
                              "ces valeurs et les VÉRIFIER en relisant le registre :", lines,
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
                self.say("⚠ Windows n'a pas conservé : " + ", ".join(tweaks.BY_ID[i].name for i in bad))
            else:
                self.say(f"✨ {len(on)} appliqué(s), {len(off)} remis comme avant — vérifié en relisant le registre.")
        except OSError as e:
            self.say(f"Erreur : {e}")
        self.refresh()
