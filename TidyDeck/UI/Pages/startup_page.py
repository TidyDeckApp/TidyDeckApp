import os
import time
from tkinter import messagebox, ttk
from Core.Startup import startup
from Shared.Utils.common import IS_WINDOWS
from UI.components import Checklist, FlowFrame, auto_wrap, preview_dialog
from UI.Pages.base import Page
from Shared.Utils.lang import T

LEVEL = {"keep": ("🛡", "Essentiel — à garder", "ok"), "safe": ("💤", "Désactivable sans risque", "info"),
         "maybe": ("⚖", "Selon ton usage", "info"), "unknown": ("❓", "Inconnu — à vérifier", "warn")}


class StartupPage(Page):
    """Coche = lancé au démarrage. Tu coches / décoches librement, PUIS tu valides : rien ne change avant."""

    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Démarrage",
                         T("Coche = le programme se lance au démarrage ; décoche = désactivé, jamais supprimé. "
                         "Rien ne change tant que tu ne cliques pas sur « Appliquer mes choix »."))
        self.serene = bool(ctx.cfg.get("serenity"))

        # --- Bloc Sérénité : un bouton, une phrase, le détail replié ---
        self.serene_box = ttk.Frame(self)
        self.big_btn = ttk.Button(self.serene_box, text=T("💤  Désactiver les programmes inutiles au démarrage"),
                                 style="Big.TButton", command=self.serene_apply)
        self.big_btn.pack(anchor="w", pady=(6, 8))
        auto_wrap(ttk.Label(self.serene_box, style="Muted.TLabel", justify="left",
                  text=T("Uniquement les programmes marqués « désactivable sans risque ». "
                       "Rien ne se lance sans que tu voies la liste, et tout est annulable."
                  ))).pack(anchor="w", fill="x", pady=(0, 10))
        self.detail_btn = ttk.Button(self.serene_box, text=T("▸ Voir le détail des programmes"),
                                    style="Flat.TButton", command=self._toggle_detail)

        # --- Bloc complet : barre + tableau (le tableau seul fait défiler la liste) ---
        self.adv = ttk.Frame(self)
        # Cree directement dans adv : un re-parentage (pack in=) laisse les enfants
        # place() du FlowFrame sans rendu -> grande zone vide a l'ecran.
        self.bar.destroy()
        self.bar = FlowFrame(self.adv)
        self.bar.pack(fill="x", pady=(0, 8))
        self.button(T("✔ Appliquer mes choix…"), self.apply, accent=True)
        self._all_on = False
        self.sel_all_btn = ttk.Button(self.bar, text=T("☐ Tout sélectionner"), command=self._toggle_all)
        self.bar.add(self.sel_all_btn)
        self.button("↻ Actualiser (annule mes choix en attente)", lambda: self.refresh(True))
        self.admin_button()
        self.list = Checklist(self.adv, ctx, (T("Programme"), T("État · conseil")), on_toggle=self._toggled,
                             open_label="📂 Ouvrir « Applications au démarrage » (Windows)", box_only=True)
        self.list.pack(fill="both", expand=True)
        self.entries, self.dirty, self._t = {}, False, 0

        if self.serene:
            self.subtitle_lbl.configure(
                text=T("Allège ton démarrage en un clic. Rien ne change sans ton accord, et tout est annulable."))
            self.serene_box.pack(fill="x")
            self.detail_btn.pack(anchor="w")
        else:
            self.adv.pack(fill="both", expand=True)

    def _toggle_detail(self):
        if self.adv.winfo_manager():
            self.adv.pack_forget()
            self.detail_btn.configure(text=T("▸ Voir le détail des programmes"))
        else:
            self.adv.pack(fill="both", expand=True)
            self.detail_btn.configure(text=T("▾ Masquer le détail"))

    def serene_apply(self):
        off = [e for e in self.entries.values()
               if e["enabled"] and e["level"] == "safe" and not e.get("policy")]
        if not off:
            self.say(T("✓ Aucun programme inutile à désactiver : ton démarrage est déjà léger."))
            return
        self._apply_lists(off, [])

    def on_show(self):
        if not self.dirty and time.time() - self._t > 15:      # ne jamais écraser des choix en attente
            self.refresh()

    def _p(self, n, sing, plur):
        return f"{n} {sing if n == 1 else plur}"

    @staticmethod
    def _st(info):
        """Couleur selon l'ÉTAT affiché, jamais selon le conseil : ✕ (désactivé,
        introuvable) ne doit jamais être vert même pour un programme « à garder »."""
        if info.startswith("✔"):
            return "ok"
        if info.startswith("✕"):
            return "warn"
        return "info"

    def _info(self, e, checked):
        if e.get("policy"):
            return T("🔒 Géré par ton administrateur")
        if e.get("missing"):
            return T("✕ Introuvable · le programme n'existe plus sur ce PC")
        state = T("✔ Actif") if e["enabled"] else T("✕ Désactivé")
        conseil = T(LEVEL[e["level"]][1])
        if e["enabled"] and not checked:
            return T("⏻ Sera désactivé · ") + conseil
        if not e["enabled"] and checked:
            return T("⏼ Sera réactivé · ") + conseil
        if e["enabled"]:
            return state + " · " + conseil
        return state

    def refresh(self, force=False):
        if force:
            self.dirty = False
        if not IS_WINDOWS:
            self.say(T("Cette page lit le registre Windows : elle est vide sur un autre système."))
        self._t = time.time()
        self.entries = {e["id"]: e for e in startup.list_entries()}
        rows = []
        for e in self.entries.values():
            icon, label, st = LEVEL[e["level"]]
            info = self._info(e, e["enabled"])
            st = self._st(info)
            appr = (T("État enregistré dans : HKEY_{v0}\\{v1}\n\n").format(v0='CURRENT_USER' if e['hive'] == 'HKCU' else 'LOCAL_MACHINE', v1=e['approved'])
                    if e.get("approved") else T("État : valeur « State » de la clé ci-dessus : seul 2 = activé, toute autre valeur = désactivé.\n\n"))
            detail = (T("Ce que c'est : {v0}\n\nCommande lancée : {v1}\n\n"
                      "Où ça se trouve : {v2}\n    entrée « {v3} »  ({v4})\n{v5}"
                      "Risque : aucun, la désactivation est réversible (recoche, ou bouton Annuler des Journaux).\n\n"
                      "Impact mesuré par Windows : Gestionnaire des tâches > Démarrage > colonne « Impact ».").format(v0=T(e['hint']), v1=e['command'], v2=e['where'], v3=e['name'], v4=T(e['scope']), v5=appr))
            row = dict(id=e["id"], name=f"{icon}  {T(e['name'])}", info=info, status=st,
                     checked=e["enabled"], detail=detail, locked=bool(e.get("policy")))
            # URI officiel verifie (docs Microsoft Learn) : « Startup apps » =
            # ms-settings:startupapps — et NON ms-settings:startup (page inexistante).
            row["settings"] = "startupapps"
            rows.append(row)
        self.list.set_rows(rows)
        if self.serene:
            n_safe = sum(1 for e in self.entries.values()
                        if e["enabled"] and e["level"] == "safe" and not e.get("policy"))
            if n_safe:
                self.big_btn.configure(text=(T("💤  Désactiver {v0} programme inutile au démarrage") if n_safe == 1
                                             else T("💤  Désactiver {v0} programmes inutiles au démarrage")).format(v0=n_safe))
                self.big_btn.state(["!disabled"])
            else:
                self.big_btn.configure(text=T("✓  Démarrage déjà allégé"))
                self.big_btn.state(["disabled"])
        self._all_on = False
        self.sel_all_btn.configure(text=T("☐ Tout sélectionner"))
        if rows:
            n_actifs = sum(1 for e in self.entries.values() if e["enabled"])
            compte = T("{v0} trouvés, dont {v1} actifs").format(v0=len(rows), v1=n_actifs)
            self.say(compte + ".")

    def _toggled(self, iid, new):
        e = self.entries[iid]
        if e["level"] == "keep" and not new and e["enabled"]:
            if not messagebox.askyesno("Élément essentiel", T("« {nom} » est un élément essentiel (sécurité, audio…).\n"
                                                             "Le décocher n'est pas recommandé. Le décocher quand même ?").format(nom=e['name'])):
                return False
        self.dirty = True
        info = self._info(e, new)
        self.list.update_row(iid, info=info, status=self._st(info))
        return True

    def _toggle_all(self):
        if not self._all_on:
            if not messagebox.askyesno("Tout sélectionner",
                                       "Cocher « Tout sélectionner » active aussi des programmes essentiels "
                                       "(antivirus, audio, sécurité) : ce n'est pas recommandé.\n\n"
                                       "Veux-tu quand même tout cocher ?"):
                return
            n = self.list.set_all(True)
            self._all_on = True
            self.sel_all_btn.configure(text=T("☑ Tout désélectionner"))
            msg = (T("{v0} ligne cochée. Clique « Appliquer mes choix » pour valider.") if n == 1
                   else T("{v0} lignes cochées. Clique « Appliquer mes choix » pour valider.")).format(v0=n)
        else:
            n = self.list.set_all(False)
            self._all_on = False
            self.sel_all_btn.configure(text=T("☐ Tout sélectionner"))
            msg = (T("{v0} ligne décochée. Clique « Appliquer mes choix » pour valider.") if n == 1
                   else T("{v0} lignes décochées. Clique « Appliquer mes choix » pour valider.")).format(v0=n)
        for iid, r in self.list.rows.items():
            self.list.update_row(iid, info=self._info(self.entries[iid], r["checked"]))
        self.dirty = True
        self.say(msg)

    def apply(self):
        checked = set(self.list.checked_ids())
        off = [e for i, e in self.entries.items() if e["enabled"] and i not in checked and not e.get("policy")]
        on = [e for i, e in self.entries.items() if not e["enabled"] and i in checked and not e.get("policy")]
        if not off and not on:
            messagebox.showinfo("TidyDeck", T("Rien à changer : ta sélection correspond déjà à l'état de Windows."))
            return
        self._apply_lists(off, on)

    def _apply_lists(self, off, on):
        lines = []
        if off:
            lines += [T("⏻ À DÉSACTIVER AU DÉMARRAGE")] + [f"• {e['name']}" for e in off]
        if on:
            lines += ["", T("⏼ À RÉACTIVER AU DÉMARRAGE")] + [f"• {e['name']}" for e in on]
        if not preview_dialog(self.ctx, T("Aperçu du démarrage"), T("Voici exactement ce que TidyDeck va changer (rien n'est supprimé) :"),
                              lines, T("Annulable depuis les Journaux. Les changements sont vérifiés en relisant Windows."), "Oui, appliquer"):
            return
        n1, f1 = startup.set_many(off, False, self.ctx.journal) if off else (0, [])
        n2, f2 = startup.set_many(on, True, self.ctx.journal) if on else (0, [])
        failed = f1 + f2
        self.dirty = False
        if failed:
            msg = T("{a}, {b}. Impossible pour :\n\n").format(a=self._p(n1, T("programme désactivé"), T("programmes désactivés")), b=self._p(n2, T("programme réactivé"), T("programmes réactivés"))) + "\n".join(f"• {n} — {w}" for n, w in failed)
            if any("admin" in w for _, w in failed) and messagebox.askyesno("Droits administrateur", msg + T("\n\nRelancer TidyDeck en administrateur ?")):
                self.ctx.ask_admin(confirm=False)
            elif not any("admin" in w for _, w in failed):
                messagebox.showwarning("TidyDeck", msg)
        else:
            self.say(T("{a}, {b} — vérifié en relisant Windows.").format(a=self._p(n1, T("programme désactivé"), T("programmes désactivés")), b=self._p(n2, T("programme réactivé"), T("programmes réactivés"))))
        self.refresh(True)
