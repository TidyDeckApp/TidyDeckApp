import tkinter as tk
from tkinter import messagebox, ttk
from Core.Games import games, power
from Shared.Utils.common import IS_WINDOWS, run_cmd
from UI.components import Checklist, preview_dialog, run_bg, info_note
from UI.Pages.base import Page
from UI.Pages.check_page import check_rows


class GamesPage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Pour les joueurs",
                         "Des conseils, pas de modifications automatiques : tu gardes la main.")
        self.button("↻ Actualiser", lambda: self.refresh(True), accent=True)
        self.mode_btn = self.button("", self.toggle_mode)
        self._mode_text()
        self.button("⚡ Plan « Performances maximales »…", self.ultimate)
        self.button("🔍 Détecteur jeux inactifs", self.detect_idle_games)

        info_frame = tk.Frame(self, bg=ctx.theme["card"], highlightbackground=ctx.theme["line"], highlightthickness=1)
        info_frame.pack(fill="x", pady=(0, 8))
        info_note(info_frame, ctx.theme, ctx.status_colors["info"], "Ce que font ces boutons :",
                 bold=True, bg=ctx.theme["card"]).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(info_frame, wraplength=850, justify="left", font=("Segoe UI", 9),
                 bg=ctx.theme["card"], fg=ctx.theme["muted"], text=(
            "• Mode Jeu : Coupe les rappels pendant que tu joues. Tes notifications attendent la fin de session.\n"
            "• Plan Performances : Force le CPU à rester à pleine vitesse (moins de latence, un peu plus de chaleur).\n"
            "• Détecteur jeux inactifs : Repère les jeux/launchers ouverts depuis trop longtemps sans activité.")).pack(anchor="w", padx=12, pady=(0, 8))

        self.checks = Checklist(self, ctx, ("Contrôle", "Constat"), checkable=False)
        self.checks.pack(fill="both", expand=True)

    def _mode_text(self):
        on = self.ctx.cfg["game_mode_on"]
        self.mode_btn.configure(text=f"🎮 Mode Jeu TidyDeck : {'ON ✔' if on else 'OFF'}")

    def toggle_mode(self):
        c = self.ctx.cfg
        c["game_mode_on"] = not c["game_mode_on"]
        self.ctx.save()
        self._mode_text()
        # La banniere est partagee : le Mode Discret reste tel quel, on ne rafraichit
        # que l'affichage, on ne touche a rien d'autre.
        try:
            self.ctx.app.banner.refresh()
        except Exception:
            pass
        self.say("🎮 Mode Jeu actif : tes rappels attendent la fin de la session." if c["game_mode_on"]
                 else "Mode Jeu désactivé : les rappels reviennent normalement.")

    def on_show(self):
        self.refresh()

    def refresh(self, force=False):
        self.load("games_checks", lambda: games.run_checks(self.ctx.cfg.get("serenity")),
                  lambda r: self.checks.set_rows(check_rows(self.ctx, r)), ttl=90, force=force)

    def ultimate(self):
        if not IS_WINDOWS:
            messagebox.showinfo("TidyDeck", "Le plan d'alimentation ne concerne que Windows.")
            return
        if not preview_dialog(self.ctx, "Plan « Performances maximales »",
                              "TidyDeck va exécuter la commande officielle de Windows :",
                              ["powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61",
                               "powercfg /setactive <le nouveau plan>", "",
                               "Effet : le processeur reste à pleine vitesse (moins de latence, un peu plus de chaleur et de bruit).",
                               "Sur portable : la batterie se vide plus vite. Pense à brancher le secteur.",
                               "Annulable : l'ancien plan est mémorisé (Journaux > Annuler)."],
                              "Si le plan existe déjà sur ton PC, TidyDeck le réutilise au lieu d'en créer un autre.", "Oui, activer"):
            return
        self.busy("Activation du plan", "power")
        run_bg(self.ctx.root, lambda: power.enable_ultimate(self.ctx.journal), self._ultimate_done)

    def _ultimate_done(self, r, e):
        self.idle()
        ok, msg = r if r else (False, str(e))
        self.say(("⚡ " if ok else "⚠ ") + msg)
        self.ctx.cache.pop("games_checks", None)
        self.refresh(True)

    def detect_idle_games(self):
        if not IS_WINDOWS:
            messagebox.showinfo("TidyDeck", "Le détecteur de jeux ne fonctionne que sous Windows.")
            return
        self.busy("Recherche des jeux inactifs…", "idle_detect")
        run_bg(self.ctx.root, self._find_idle_games, self._idle_done)

    def _find_idle_games(self):
        game_procs = ["steam.exe", "EpicGamesLauncher.exe", "XboxApp.exe", "Battle.net.exe",
                     "GOG Galaxy.exe", "riotclient.exe", "valorant.exe", "fortnite.exe"]
        _, out = run_cmd(["tasklist", "/FO", "CSV", "/NH"], 15)
        found = []
        for line in out.splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                exe = parts[0].lower()
                pid = parts[1]
                if any(g in exe for g in game_procs):
                    found.append({"exe": parts[0], "pid": pid})
        return found

    def _idle_done(self, found, err):
        self.idle()
        if err:
            self.say(f"Erreur : {err}")
            return
        if not found:
            self.say("✅ Aucun jeu ou launcher gourmand détecté. Bon jeu ! 🎮")
            return
        names = ", ".join(f["exe"] for f in found)
        if messagebox.askyesno("Jeux/launchers détectés",
                               f"J'ai trouvé ces programmes ouverts : {names}\n\n"
                               "Tu as fini ta session ? Je peux te proposer de les fermer poliment.\n\n"
                               "Oui = je te liste les options\nNon = je ne touche à rien"):
            for f in found:
                if messagebox.askyesno(f"Fermer {f['exe']} ?",
                                      f"Demander la fermeture de {f['exe']} (PID {f['pid']}) ?\n"
                                      "Enregistre ton travail avant : rien n'est forcé."):
                    run_cmd(["taskkill", "/PID", f["pid"], "/f"], 10)
            self.say("✨ Session terminée. Ton PC peut se reposer. 🌿")
        else:
            self.say("D'accord, je ne touche à rien. Bon jeu ! 🎮")
