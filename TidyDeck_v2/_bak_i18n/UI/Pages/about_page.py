import tkinter as tk
import webbrowser
from tkinter import ttk
from Shared.Utils.common import APP_VERSION, DONATION_URL, IS_WINDOWS, is_admin
from UI.components import ScrollFrame, Collapsible

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
    "Applis préinstallées : TidyDeck liste, explique et propose. Rien n'est désinstallé sans que tu "
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

        ttk.Label(f, text="À propos de TidyDeck", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(f, text=f"Version {APP_VERSION}", style="Sub.TLabel").pack(anchor="w", pady=(0, 16))

        ttk.Label(f, text="Nos engagements", style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(f, wraplength=900, justify="left", text=(
            "• Aucune donnée collectée, rien d'envoyé sur internet (sauf si TU cliques « Mises à jour »).\n"
            "• Pas de nettoyeur de registre, pas de promesse de « boost ×3 ».\n"
            "• Tout ce qui peut être touché est listé avec son chemin réel : tu peux le vérifier toi-même.\n"
            "• Code ouvert : lis-le, modifie-le, vérifie-le.")).pack(anchor="w", pady=(0, 16))

        ttk.Label(f, text="Comment ça marche", style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(f, wraplength=900, justify="left", text=(
            "TidyDeck analyse ton PC, te montre ce qui peut être nettoyé ou optimisé, et attend ta validation "
            "avant toute action. Les fichiers sont mis en quarantaine (annulable) avant suppression définitive.\n\n"
            "Les seules actions non annulables sont explicitement signalées (Corbeille vidée).")).pack(anchor="w", pady=(0, 16))

        ttk.Label(f, text="Sécurité", style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        # En Sérénité, la liste de sécurité est repliée : même contenu, moins de bloc
        # de texte d'un coup. En mode normal, elle reste visible directement.
        if serene:
            Collapsible(f, "Ce qui protège ta machine (7 points)", [
                "TidyDeck ne modifie jamais le registre sans te montrer exactement ce qui sera écrit.",
                "Les services Windows vitaux ne figurent pas dans la liste des services désactivables.",
                "Un point de restauration Windows est proposé avant les actions sensibles.",
                "Toutes les actions sont journalisées et annulables depuis l'onglet Journaux.",
                "Rien ne se lance sans que tu aies validé la liste exacte des éléments concernés.",
                "Les suppressions passent par la quarantaine, jamais par une suppression directe.",
                "Tu peux tout arrêter à tout moment : aucune action planifiée en arrière-plan sur tes fichiers.",
            ]).pack(anchor="w", fill="x", pady=(0, 16))
        else:
            ttk.Label(f, wraplength=900, justify="left", text=(
                "• TidyDeck ne modifie jamais le registre sans te montrer exactement ce qui sera écrit.\n"
                "• Les services Windows vitaux ne figurent pas dans la liste des services désactivables.\n"
                "• Un point de restauration Windows est proposé avant les actions sensibles.\n"
                "• Toutes les actions sont journalisées et annulables depuis l'onglet Journaux.")).pack(anchor="w", pady=(0, 16))

        adm = ttk.Frame(f)
        adm.pack(anchor="w", pady=10)
        if is_admin():
            ttk.Label(adm, text="🛡 Mode administrateur actif.").pack(anchor="w")
        else:
            ttk.Label(adm, text="Sans droits administrateur : suffisant pour presque tout.").pack(anchor="w")
            ttk.Label(adm, text="L'admin sert pour certains nettoyages, les services et les points de restauration.\n"
                      "Si tu cliques, Windows t'affichera une demande de confirmation (fenêtre UAC).",
                      style="Muted.TLabel", justify="left").pack(anchor="w", pady=(2, 0))
            ttk.Button(adm, text="🛡 Relancer en administrateur", command=ctx.ask_admin).pack(anchor="w", pady=(8, 0))

        ttk.Label(f, text="Conditions d'utilisation", style="Sub.TLabel").pack(anchor="w", pady=(0, 4))
        if serene:
            # Ton adouci par défaut, texte intégral juste en dessous : le fond du
            # message est identique, seule la formulation change.
            Collapsible(f, "Ce que TidyDeck te promet, dit simplement", CONDITIONS_CALM).pack(
                anchor="w", fill="x", pady=(0, 6))
            Collapsible(f, "Le même texte, dans sa formulation juridique complète", CONDITIONS_FULL).pack(
                anchor="w", fill="x", pady=(0, 16))
        else:
            Collapsible(f, "Ce que le logiciel promet — et ce qu'il ne promet pas", CONDITIONS_FULL).pack(
                anchor="w", fill="x", pady=(0, 16))

        # Canal de don UNIQUE. Rien d'autre n'est affiche si DONATION_URL est vide,
        # et ce bloc ne doit jamais etre duplique ailleurs dans l'application.
        if DONATION_URL:
            don = ttk.Frame(f)
            don.pack(anchor="w", pady=(0, 12))
            ttk.Label(don, text="Soutenir TidyDeck", style="Sub.TLabel").pack(anchor="w")
            ttk.Label(don, style="Muted.TLabel", justify="left",
                      text="Aucun don n'est requis, aucun n'est rappelé, aucun ne débloque quoi que ce soit."
                      ).pack(anchor="w", pady=(2, 6))
            ttk.Button(don, text="❤️ Faire un don",
                       command=lambda: webbrowser.open(DONATION_URL)).pack(anchor="w")

        ttk.Label(f, text=f"TidyDeck {APP_VERSION} — Le ménage de ton PC, tout en douceur 🌿",
                  style="Muted.TLabel").pack(anchor="w", pady=(20, 20))
