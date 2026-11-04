import os
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
from Shared.Utils.common import APP_VERSION, DONATION_URL, IS_WINDOWS, is_admin
from Shared.Utils import dossiers
from UI.components import ScrollFrame, Collapsible, run_bg
from Services.UpdateChecker import checker
from Shared.Utils.lang import T

# Texte juridique complet : fait foi en toutes circonstances.
CONDITIONS_FULL = [
    "Réversibilité : les fichiers nettoyés sont mis en quarantaine et annulables pendant la durée "
    "choisie (7 jours par défaut), depuis l'onglet Journaux.",
    "Exception unique et assumée : vider la Corbeille est immédiat et définitif. TidyDeck te le "
    "signale explicitement chaque fois que la Corbeille est dans la sélection.",
    "Absence de garantie : dans les limites permises par la loi, le logiciel est fourni « en l'état », "
    "sans garantie implicite de qualité marchande ou d'adéquation à un usage particulier. Une opération "
    "sur un système d'exploitation peut avoir des effets inattendus. Utilise le point de restauration "
    "proposé : tu restes responsable de ta machine et de tes sauvegardes.",
    "Privilèges : les fonctions qui demandent une élévation la demandent explicitement, une fois, et "
    "Windows te redemande ton accord. Rien n'est élevé sans ton accord.",
    "Applications préinstallées : TidyDeck liste, explique et propose. Rien n'est désinstallé sans que tu "
    "valides la liste exacte des programmes concernés ; les composants essentiels de Windows ne sont "
    "jamais proposés, et un programme retiré reste réinstallable chez son éditeur ou dans le Microsoft Store.",
    "Vie privée : aucun compte, aucune inscription, aucune collecte et aucune télémétrie. Aucune donnée "
    "ne quitte ta machine : le seul accès réseau est le bouton « Mises à jour », et il ne part que si "
    "tu cliques dessus.",
    "Rappels : ils ne fonctionnent que si TidyDeck reste ouvert (réduit dans la barre des tâches). "
    "TidyDeck ne peut pas t'avertir s'il est fermé, et ne le promet pas.",
    "Mode Discret : il masque à l'écran ce que TidyDeck affiche. Pas les notifications des autres "
    "applications, ni ce que Windows transmet à Microsoft. Ne compte pas dessus pour autre chose.",
    "Licence : GPL-3.0 (GNU General Public License v3), voir le fichier LICENSE fourni avec le "
    "livrable. Tu peux lire, modifier et redistribuer ce code aux mêmes conditions, sans aucune "
    "garantie, dans les limites permises par la loi.",
]

# Même contenu, ton adouci pour le mode Sérénité : rien n'est retiré sur le fond,
# seule la formulation change. Le texte complet reste accessible juste en dessous.
CONDITIONS_CALM = [
    "Tu peux revenir en arrière : ce que TidyDeck déplace reste récupérable pendant la durée que tu "
    "as choisie (7 jours par défaut), depuis l'onglet Journaux.",
    "Une seule exception, et on te la redit à chaque fois : vider la Corbeille est définitif. "
    "Rien de tout cela n'arrive sans que tu aies dit oui.",
    "Le logiciel est fourni « en l'état », dans les limites permises par la loi. Il fait attention, "
    "mais il touche à Windows : garde un point de restauration, ça ne coûte rien et ça rassure.",
    "On ne demande les droits administrateur que quand c'est vraiment nécessaire, une seule fois, et "
    "Windows te redemande ton accord avant. Rien ne monte sans que tu aies dit oui.",
    "Les applis préinstallées : on te montre la liste et ce que chaque programme fait. Rien n'est "
    "désinstallé sans que tu aies coché et validé, les morceaux importants de Windows ne sont jamais "
    "proposés, et un programme retiré se remet chez son éditeur ou dans le Microsoft Store.",
    "Tes données restent chez toi : pas de compte, pas d'inscription, pas de collecte, pas de "
    "télémétrie. Rien ne part sur internet, sauf si tu cliques toi-même sur « Mises à jour ».",
    "Les rappels fonctionnent seulement si TidyDeck reste ouvert, réduit dans la barre des tâches. "
    "S'il est fermé, il ne peut pas t'avertir — il ne te promet pas l'impossible.",
    "Le Mode Discret masque ce que TidyDeck affiche à l'écran, pas les notifications des autres "
    "applications. Il fait ce qu'il dit, rien de plus.",
    "Le code est sous licence GPL-3.0 : tu peux le lire, le modifier et le redistribuer librement, "
    "les mêmes droits pour tout le monde. Le fichier LICENSE est fourni avec le livrable.",
]


class AboutPage(ttk.Frame):
    def __init__(self, master, ctx):
        super().__init__(master, padding=14)
        self.ctx = ctx
        serene = bool(ctx.cfg.get("serenity"))
        sf = ScrollFrame(self, ctx.theme["bg"])
        sf.pack(fill="both", expand=True)
        f = sf.inner

        ttk.Label(f, text=T("À propos de TidyDeck"), style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(f, text=f"Version {APP_VERSION}", style="Sub.TLabel").pack(anchor="w", pady=(0, 16))

        ttk.Label(f, text=T("Nos engagements"), style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(f, wraplength=900, justify="left", text=T(
            "• Aucune donnée collectée, rien d'envoyé sur internet (sauf si tu cliques « Mises à jour »).\n"
            "• Pas de nettoyeur de registre, pas de promesse de « boost ×3 ».\n"
            "• Tout ce qui peut être touché est listé avec son chemin réel : tu peux le vérifier toi-même.\n"
            "• Code ouvert : lis-le, modifie-le, vérifie-le.")).pack(anchor="w", pady=(0, 16))

        ttk.Label(f, text=T("Comment ça marche"), style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(f, wraplength=900, justify="left", text=T(
            "TidyDeck analyse ton PC, te montre ce qui peut être nettoyé ou rangé, et attend ta validation "
            "avant toute action. Les fichiers sont mis en quarantaine (annulable) avant suppression définitive.\n\n"
            "Les seules actions non annulables sont explicitement signalées (Corbeille vidée).")).pack(anchor="w", pady=(0, 16))

        ttk.Label(f, text=T("Sécurité"), style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        # En Sérénité, la liste de sécurité est repliée : même contenu, moins de bloc
        # de texte d'un coup. En mode normal, elle reste visible directement.
        if serene:
            Collapsible(f, T("Ce qui protège ta machine (7 points)"), [
                T("TidyDeck ne modifie jamais le registre sans te montrer exactement ce qui sera écrit."),
                T("Les services Windows vitaux ne figurent pas dans la liste des services désactivables."),
                T("Un point de restauration Windows est proposé avant les actions sensibles."),
                T("Toutes les actions sont journalisées et annulables depuis l'onglet Journaux."),
                T("Rien ne se lance sans que tu aies validé la liste exacte des éléments concernés."),
                T("Les suppressions passent par la quarantaine, jamais par une suppression directe."),
                T("Tu peux tout arrêter à tout moment : aucune action planifiée en arrière-plan sur tes fichiers."),
            ]).pack(anchor="w", fill="x", pady=(0, 16))
        else:
            ttk.Label(f, wraplength=900, justify="left", text=T(
                "• TidyDeck ne modifie jamais le registre sans te montrer exactement ce qui sera écrit.\n"
                "• Les services Windows vitaux ne figurent pas dans la liste des services désactivables.\n"
                "• Un point de restauration Windows est proposé avant les actions sensibles.\n"
                "• Toutes les actions sont journalisées et annulables depuis l'onglet Journaux.")).pack(anchor="w", pady=(0, 16))

        adm = ttk.Frame(f)
        adm.pack(anchor="w", pady=10)
        if is_admin():
            ttk.Label(adm, text=T("🛡 Mode administrateur actif.")).pack(anchor="w")
        else:
            ttk.Label(adm, text=T("Sans droits administrateur : suffisant pour presque tout.")).pack(anchor="w")
            ttk.Label(adm, text=T("L'admin sert pour certains nettoyages, les services et les points de restauration.\n"
                      "Si tu cliques, Windows t'affichera une demande de confirmation (fenêtre UAC)."),
                      style="Muted.TLabel", justify="left").pack(anchor="w", pady=(2, 0))
            ttk.Button(adm, text=T("🛡 Relancer en administrateur"), command=ctx.ask_admin).pack(anchor="w", pady=(8, 0))

        # BLOC « Mises à jour » : le SEUL accès réseau du logiciel, uniquement sur clic.
        maj = ttk.Frame(f)
        maj.pack(anchor="w", pady=(10, 4))
        ttk.Label(maj, text=T("Mises à jour"), style="Sub.TLabel").pack(anchor="w")
        ttk.Label(maj, style="Muted.TLabel", justify="left", wraplength=760,
                  text=T("Vérifie la version publiée sur la page des versions de TidyDeck, puis "
                         "télécharge le zip vérifié dans ton dossier Téléchargements. Rien n'est "
                         "installé, rien n'est écrasé.")).pack(anchor="w", pady=(2, 6))
        ligne = ttk.Frame(maj)
        ligne.pack(anchor="w")
        self.maj_btn = ttk.Button(ligne, text=T("🌐 Vérifier les mises à jour"), command=self._maj)
        self.maj_btn.pack(side="left")
        self.maj_cancel = ttk.Button(ligne, text=T("✕ Annuler le téléchargement"),
                                     command=self._maj_stop)
        self.maj_lbl = ttk.Label(maj, text="", style="Muted.TLabel", justify="left", wraplength=760)
        self.maj_lbl.pack(anchor="w", pady=(4, 0))
        self._arrete = False

        ttk.Label(f, text=T("Conditions d'utilisation"), style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        if serene:
            # Ton adouci par défaut, texte intégral juste en dessous : le fond du
            # message est identique, seule la formulation change.
            Collapsible(f, T("Ce que TidyDeck te promet, dit simplement"), [T(x) for x in CONDITIONS_CALM]).pack(
                anchor="w", fill="x", pady=(0, 6))
            Collapsible(f, T("Le même texte, dans sa formulation juridique complète"), [T(x) for x in CONDITIONS_FULL]).pack(
                anchor="w", fill="x", pady=(0, 16))
        else:
            Collapsible(f, T("Ce que le logiciel promet — et ce qu'il ne promet pas"), [T(x) for x in CONDITIONS_FULL]).pack(
                anchor="w", fill="x", pady=(0, 16))

        # Canal de don UNIQUE. Rien d'autre n'est affiche si DONATION_URL est vide,
        # et ce bloc ne doit jamais etre duplique ailleurs dans l'application.
        if DONATION_URL:
            don = ttk.Frame(f)
            don.pack(anchor="w", pady=(0, 12))
            ttk.Label(don, text=T("Soutenir TidyDeck"), style="Sub.TLabel").pack(anchor="w")
            ttk.Label(don, style="Muted.TLabel", justify="left",
                      text=T("Aucun don n'est requis, aucun n'est rappelé, aucun ne débloque quoi que ce soit."
                      )).pack(anchor="w", pady=(2, 6))
            ttk.Button(don, text=T("❤️ Faire un don"),
                       command=lambda: webbrowser.open(DONATION_URL)).pack(anchor="w")

        ttk.Label(f, text=T("TidyDeck {v} — Le ménage de ton PC, tout en douceur 🌿").format(v=APP_VERSION),
                  style="Muted.TLabel").pack(anchor="w", pady=(20, 20))

    # ------------------------------------------------------------------ mises à jour
    # Tout le réseau de TidyDeck tient dans ces quelques méthodes : rien ne part
    # sans un clic, jamais de vérification en arrière-plan.
    def _dire(self, txt):
        try:
            self.ctx.root.after(0, lambda: self.maj_lbl.configure(text=txt))
        except tk.TclError:
            pass

    def _maj(self):
        self.maj_btn.state(["disabled"])
        self._dire(T("Vérification, juste après ton clic…"))

        def fini(r, e):
            self.maj_btn.state(["!disabled"])
            self._dire("")
            if e or not r or r.get("statut") == "hors_ligne":
                messagebox.showinfo("TidyDeck", T("Impossible de joindre la page des versions."))
                return
            if r["statut"] == "inverifiable":
                messagebox.showinfo("TidyDeck", T("Je ne peux pas vérifier ce fichier, donc je ne le télécharge pas."))
                return
            if r["statut"] == "jour":
                messagebox.showinfo("TidyDeck", T("Tu as la dernière version ({v}).").format(v=APP_VERSION))
                return
            oui = messagebox.askyesno("TidyDeck", T(
                "Version {t} disponible (tu as {v}).\n\n"
                "Je peux télécharger le zip vérifié dans ton dossier Téléchargements. "
                "Je n'installe rien : plus tard, tu fermes TidyDeck, tu décompresses le zip "
                "et tu remplaces le dossier.\n\nTélécharger maintenant ?").format(t=r["tag"], v=APP_VERSION))
            if oui:
                self._telecharge(r)

        run_bg(self.ctx.root, checker.verifier, fini)

    def _telecharge(self, r):
        dossier = dossiers.connu("downloads")
        if not dossier:
            messagebox.showinfo("TidyDeck", T("Je ne trouve pas ton dossier Téléchargements."))
            return
        self._arrete = False
        self.maj_btn.state(["disabled"])
        self.maj_cancel.pack(side="left", padx=(8, 0))
        box = {}

        def tache():
            try:
                box["r"] = checker.telecharger(dossier, r["zip"], r["sha"],
                                               proges=self._dire_pct, annule=lambda: self._arrete)
            except Exception:
                box["r"] = {"statut": "reseau"}

        th = threading.Thread(target=tache, daemon=True)
        th.start()

        def sonde():
            if th.is_alive():
                self.ctx.root.after(300, sonde)
                return
            self.maj_cancel.pack_forget()
            self.maj_btn.state(["!disabled"])
            st = (box.get("r") or {}).get("statut", "reseau")
            if st == "ok":
                self._dire("")
                if messagebox.askyesno("TidyDeck", T(
                        "Fichier intact. Il est dans Téléchargements.\n\n"
                        "Ouvrir le dossier maintenant ?")):
                    try:
                        os.startfile(dossier)
                    except Exception:
                        messagebox.showinfo("TidyDeck", T("Je n'ai pas pu ouvrir le dossier. Il est quand même dans Téléchargements."))
            elif st == "abime":
                self._dire("")
                messagebox.showwarning("TidyDeck", T("Le fichier est abîmé, je ne le garde pas. Réessaie."))
            elif st == "annule":
                self._dire(T("Téléchargement annulé : rien n'est resté sur le disque."))
            elif st == "inverifiable":
                self._dire("")
                messagebox.showinfo("TidyDeck", T("Je ne peux pas vérifier ce fichier, donc je ne le télécharge pas."))
            else:
                self._dire("")
                messagebox.showinfo("TidyDeck", T("Pas de connexion. Rien n'a été téléchargé."))

        sonde()

    def _dire_pct(self, recu, total):
        pct = int(recu * 100 / total) if total else 0
        self._dire(T("Téléchargement… {p} %").format(p=pct))

    def _maj_stop(self):
        self._arrete = True
        self.maj_cancel.state(["disabled"])
