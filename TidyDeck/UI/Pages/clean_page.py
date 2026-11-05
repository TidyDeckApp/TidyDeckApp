import tkinter as tk
from tkinter import messagebox, ttk
from Shared.Constants.catalog import build_catalog
from Shared.Utils.common import human_size
from Shared.Utils import quarantine
from Core.Health import cleaner
from UI.components import CleanCard, run_bg, preview_dialog, score_dialog, ScrollFrame
from UI.Pages.base import Page
from UI import routine
from Shared.Utils.lang import T


class _Section(tk.Frame):
    def __init__(self, master, theme, title):
        super().__init__(master, bg=theme["bg"])
        self.title_txt, self.open = T(title), False
        self.btn = ttk.Button(self, text=f"▸ {self.title_txt}", style="Flat.TButton", command=self.toggle)
        self.btn.pack(fill="x")
        self.body = tk.Frame(self, bg=theme["bg"])

    def toggle(self):
        self.open = not self.open
        self.btn.configure(text=("▾ " if self.open else "▸ ") + self.title_txt)
        if self.open:
            self.body.pack(fill="x", pady=(2, 4))
        else:
            self.body.pack_forget()


class CleanPage(Page):
    SECTIONS = [
        ("🗂  Fichiers temporaires et système", ["temp_user", "temp_win", "recycle"]),
        ("🌐  Caches des navigateurs", ["chrome", "edge", "brave", "opera", "firefox"]),
        ("🎮  Caches de jeux et graphiques", ["dx", "nvidia"]),
    ]
    BROWSERS = {"chrome", "edge", "brave", "opera", "firefox"}
    GAMES = {"dx", "nvidia"}

    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Nettoyage",
                         "Libère de la place en mettant de côté uniquement des fichiers temporaires et des caches. "
                         "Tu vois tout avant de valider, et tout reste annulable 7 jours, sauf la Corbeille.")
        self.results = {}
        self._pending_preset = None
        self.bar.pack_forget()

        analyze_frame = tk.Frame(self, bg=ctx.theme["bg"])
        analyze_frame.pack(fill="x", pady=(0, 2))
        self.analyze_btn = ttk.Button(analyze_frame, text=T("Analyser mon PC"), style="Accent.TButton", command=self.analyse)
        self.analyze_btn.pack(side="left")
        self.result_lbl = tk.Label(analyze_frame, text=T(""), font=("Segoe UI", 10),
                                   bg=ctx.theme["bg"], fg=ctx.status_colors["ok"])
        self.result_lbl.pack(side="left", padx=(12, 0))

        preset_frame = tk.Frame(self, bg=ctx.theme["bg"])
        preset_frame.pack(fill="x", pady=(4, 4))
        self.btn_all = ttk.Button(preset_frame, text=self._all_label(), command=self._toggle_all)
        self.btn_all.pack(side="left", padx=(0, 8))
        for text, fn in [("Uniquement les navigateurs", lambda: self._preset(self.BROWSERS)),
                        ("Uniquement les caches de jeux", lambda: self._preset(self.GAMES))]:
            ttk.Button(preset_frame, text=T(text), command=fn).pack(side="left", padx=(0, 8))

        self.status.pack_forget()

        self.bottom_bar = tk.Frame(self, bg=ctx.theme["bg"])
        self.bottom_bar.pack(side="bottom", fill="x", pady=(8, 0))
        self.sel_lbl = tk.Label(self.bottom_bar, text=T("Sélection : 0 Go"), font=("Segoe UI", 11, "bold"),
                                bg=ctx.theme["bg"], fg=ctx.theme["fg"])
        self.sel_lbl.pack(side="left")
        self.clean_btn = ttk.Button(self.bottom_bar, text=T("Nettoyer la sélection"), style="Accent.TButton", command=self.clean)
        self.clean_btn.pack(side="right")
        self.clean_btn.state(["disabled"])

        self.status.pack(side="bottom", anchor="w", fill="x", pady=(6, 0))

        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        self.cards_frame = sf.inner

        self.items = [i for i in build_catalog() if ctx.advanced or i.simple]
        self.cards = {}
        self._build_cards()

    def _build_cards(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()
        self.cards = {}
        placed = set()
        for title, ids in self.SECTIONS:
            items = [i for i in self.items if i.id in ids]
            if not items:
                continue
            placed.update(ids)
            sec = _Section(self.cards_frame, self.ctx.theme, title)
            sec.pack(fill="x", pady=(0, 6))
            for item in items:
                self._add_card(sec.body, item)
        rest = [i for i in self.items if i.id not in placed]
        if rest:
            sec = _Section(self.cards_frame, self.ctx.theme, T("📦 Autres"))
            sec.pack(fill="x", pady=(0, 6))
            for item in rest:
                self._add_card(sec.body, item)
        self._update_selection()

    def _add_card(self, parent, item):
        r = self.results.get(item.id)
        card = CleanCard(parent, self.ctx, item, r, on_toggle=self._update_selection)
        card.pack(fill="x", padx=8, pady=(0, 8))
        self.cards[item.id] = card

    def _update_selection(self):
        total = 0
        netting = False
        for iid, card in self.cards.items():
            if card.var.get() and iid in self.results and not self.results[iid].blocked:
                total += self.results[iid].size
                if self.results[iid].size > 0:
                    netting = True
        # « Nettoyer la sélection » reste grisé tant que rien de concret ne peut
        # être nettoyé (rien de coché, tout vide ou tout bloqué) : un clic qui
        # n'aboutit à rien est plus frustrant qu'un bouton désactivé.
        self.clean_btn.configure(state="normal" if netting else "disabled")
        if self.ctx.cfg.get("serenity"):
            self.sel_lbl.configure(text=T("Aucun élément sélectionné") if total == 0
                                   else T("Place sélectionnée : rien de critique, tout est vérifié avant"))
        else:
            txt = T("Sélection : {v0}").format(v0=human_size(total))
            if getattr(self, "_sel_note", None):
                txt += T(" · {v0}").format(v0=self._sel_note)
            self.sel_lbl.configure(text=txt)
        if getattr(self, "btn_all", None):
            self.btn_all.configure(text=self._all_label())

    def _toggle_all(self):
        """Un seul bouton pour les deux : tout cocher, puis tout décocher."""
        if not self.results:
            self._pending_preset = "safe"
            self.say(T("Petite analyse d'abord (quelques secondes), puis je coche tout…"))
            self.analyse()
            return
        if self._tout_coché():
            for card in self.cards.values():
                card.var.set(False)
        else:
            self._apply_preset("safe")
        self._update_selection()

    def _cochables(self):
        """Ids que « Tout cocher » peut honnêtement cocher : ni bloqués, ni définitifs."""
        return [iid for iid in getattr(self, "cards", {})
                if iid in getattr(self, "results", {}) and not self.results[iid].blocked
                and self.results[iid].item.special is None]

    def _tout_coché(self):
        cible = self._cochables()
        return bool(cible) and all(self.cards[i].var.get() for i in cible)

    def _all_label(self):
        if self._tout_coché():
            return T("Tout décocher")
        return T("Tout cocher (sûr)") if self.ctx.cfg.get("serenity") else T("Tout cocher (Recommandé)")

    def _preset(self, mode):
        if not self.results:
            self._pending_preset = mode
            self.say(T("Petite analyse d'abord (quelques secondes), puis j'applique ta sélection…"))
            self.analyse()
            return
        self._apply_preset(mode)

    def _apply_preset(self, mode):
        for iid, card in self.cards.items():
            r = self.results.get(iid)
            if mode == "safe":
                # « blocked » veut deja dire « impossible maintenant » (admin qui
                # manque, programme ouvert). Ajouter needs_admin ici empechait les
                # fichiers temporaires Windows de se cocher MEME en administrateur.
                on = bool(r) and not r.blocked and r.item.special is None
            else:
                on = iid in mode and bool(r) and not r.blocked
            card.var.set(on)
        self._update_selection()

    def checked_ids(self):
        return [iid for iid, card in self.cards.items() if card.var.get()]

    def analyse(self):
        self.busy(T("Analyse en cours"), "scan")
        run_bg(self.ctx.root, lambda: cleaner.scan_all(self.items), self._analysed)

    def _analysed(self, res, err):
        self.idle()
        if err:
            self.say(f"Je n'ai pas pu analyser : {err}")
            return
        self.results = res
        for item in self.items:
            if item.id in self.cards:
                self.cards[item.id].set_result(res[item.id])
        tot = sum(r.size for r in res.values() if not r.blocked and r.item.special is None)
        if self.ctx.cfg.get("serenity"):
            self.result_lbl.configure(
                text=T("Analyse terminée : de la place peut être récupérée, rien d'urgent (hors Corbeille).")
                if tot >= 1 << 30 else
                T("Analyse terminée : peu de place à récupérer en ce moment — ton PC est déjà propre."))
        else:
            self.result_lbl.configure(text=T("Analyse terminée : environ {v0} peuvent être nettoyés (hors Corbeille).").format(v0=human_size(tot)))
        self._update_selection()
        if self._pending_preset:
            mode, self._pending_preset = self._pending_preset, None
            self._apply_preset(mode)
        self._explique_le_reste()

    def _explique_le_reste(self):
        """Après un nettoyage, ce qui n'a pas pu bouger est expliqué : l'utilisateur doit
        comprendre pourquoi il reste des Mo dans la sélection (fichiers utilisés par un
        programme ouvert), au lieu de croire que le nettoyage a échoué."""
        ids, self._cleaned_sel = getattr(self, "_cleaned_sel", None), None
        self._sel_note = ""
        for card in self.cards.values():
            card.note("")
        if not ids:
            return
        rest = [i for i in ids if i in self.results
                and not self.results[i].blocked and self.results[i].size > 0]
        if not rest:
            self.say(T("Rien ne reste : tout ce qui était coché a bien été mis de côté."))
            return
        gauche = sum(self.results[i].size for i in rest)
        for i in rest:
            self.cards[i].note(T("Il reste {v0} sur cette ligne : des fichiers étaient en cours "
                                 "d'utilisation (programme ouvert). Ferme-le, puis relance.")
                               .format(v0=human_size(self.results[i].size)))
        self._sel_note = T("{v0} en cours d'utilisation, donc non déplacés").format(v0=human_size(gauche))
        self._update_selection()
        self.say(T("{v0} n'ont pas pu être déplacés : ce sont des fichiers utilisés par un programme "
                   "ouvert. Ferme ce programme (ou redémarre le PC) puis relance le nettoyage.")
                 .format(v0=human_size(gauche)))

    def clean(self):
        sel = [self.results[i] for i in self.checked_ids()
               if i in self.results and not self.results[i].blocked and self.results[i].size > 0]
        if not self.results:
            messagebox.showinfo("TidyDeck", T("Lance d'abord l'analyse."))
            return
        if not sel:
            messagebox.showinfo("TidyDeck", T("Rien de coché (ou rien à nettoyer)."))
            return
        total = sum(r.size for r in sel)
        serene = bool(self.ctx.cfg.get("serenity"))
        bin_in = any(r.item.special == "recycle_bin" for r in sel)
        if serene:
            lines = [f"• {T(r.item.name)}" + (T("   ⬢ À faire une seule fois") if r.item.special else "") for r in sel]
            intro = T("Voici exactement ce que TidyDeck va faire (rien de coché ici ne touche tes fichiers personnels).")
            foot = T("Les fichiers sont mis de côté : tu peux revenir dessus pendant "
                    "{v0} jours.").format(v0=self.ctx.cfg['quarantine_days'])
            if bin_in:
                foot += (T(" La Corbeille, elle, est vidée tout de suite et sans retour possible — "
                       "c'est justement ce qu'on lui demande."))
        else:
            lines = [f"• {T(r.item.name)} — {human_size(r.size)}" + (T("   ⚠ DÉFINITIF") if r.item.special else "") for r in sel]
            intro = T("Voici exactement ce que TidyDeck va faire. Place concernée : {v0}.").format(v0=human_size(total))
            foot = T("Les fichiers sont déplacés en quarantaine puis supprimés après "
                    "{v0} jours.").format(v0=self.ctx.cfg['quarantine_days'])
            if bin_in:
                foot += T(" La Corbeille, elle, est vidée tout de suite, sans retour possible.")
        if not preview_dialog(self.ctx, T("Aperçu avant nettoyage"),
                              intro, lines, foot, "Oui, nettoyer"):
            return
        self._cleaned_sel = [r.item.id for r in sel]
        self.busy(T("Nettoyage en cours"), "clean")
        run_bg(self.ctx.root, lambda: cleaner.clean(sel, self.ctx.journal), self._cleaned)

    def _msg_apres_nettoyage(self, res):
        """Message de fin de nettoyage : les fichiers laissés sont explicitement expliqués."""
        serene = bool(self.ctx.cfg.get("serenity"))
        if serene:
            msg = T("PC apaisé : des fichiers ont été mis de côté, annulable depuis les Journaux.")
            if res["skipped"]:
                msg += (T(" {v0} fichier était en cours d'utilisation : je n'ai pas pu le "
                          "déplacer, il reste en place (c'est sans risque).") if res["skipped"] == 1
                        else T(" {v0} fichiers étaient en cours d'utilisation : je n'ai pas pu les "
                               "déplacer, ils restent en place (c'est sans risque).")).format(v0=res["skipped"])
            if res["irreversible"]:
                msg += T(" La Corbeille a été vidée.")
        else:
            msg = T("✨ PC apaisé : {v0} mis de côté ({v1} éléments).").format(v0=human_size(res['moved']), v1=res['n'])
            if res["skipped"]:
                msg += (T(" {v0} fichier en cours d'utilisation a été laissé en place "
                          "(programme ouvert) : ferme-le et relance pour l'avoir aussi.") if res["skipped"] == 1
                        else T(" {v0} fichiers en cours d'utilisation ont été laissés en place "
                               "(programme ouvert) : ferme-les et relance pour les avoir aussi."
                               )).format(v0=res["skipped"])

            if res["irreversible"]:
                msg += T(" Corbeille vidée : {v0}.").format(v0=human_size(res['irreversible']))
        return msg

    def _cleaned(self, res, err):
        self.idle()
        if err:
            self.say(f"Erreur : {err}")
            return
        msg = self._msg_apres_nettoyage(res)
        self.say(msg)
        if res["moved"] or res["irreversible"]:
            score_dialog(self.ctx, [T("{v0} mis de côté ({v1} éléments)").format(v0=human_size(res['moved']), v1=res['n']),
                                    T("Annulable depuis les Journaux"), T("PC apaisé")],
                         serene_text=T("Rangement terminé en douceur. Annulable quand tu veux."),
                         undo_pairs=res.get("pairs"))
        # Rien ne reste coché après un nettoyage : la ligne « Sélection : » garder
        # l'ancienne somme ferait croire que du travail attend encore.
        for card in getattr(self, "cards", {}).values():
            card.var.set(False)
        self._update_selection()
        self.analyse()
