import os
import time
import tkinter as tk
from tkinter import messagebox
from Core.Storage import storage
from Shared.Utils.common import human_size, run_cmd
from UI.components import Checklist, run_bg, preview_dialog
from UI.Pages.base import Page
from Shared.Utils.lang import T


def _p(n, sing, plur):
    """« 1 fichier » / « 4 fichiers » : le pluriel honest, sans « (s) »."""
    return f"{n} {sing}" if n == 1 else f"{n} {plur}"


class StoragePage(Page):
    def __init__(self, master, ctx):
        super().__init__(master, ctx, "Fichiers et résidus",
                         "Trie tes Téléchargements, repère les gros fichiers oubliés et les traces "
                         "des applis désinstallées. "
                         "Rien n'est supprimé : les fichiers sont déplacés ou mis en quarantaine (annulable).")
        self.mode = None
        self.data = {}
        self.button("📥 Trier mes Téléchargements", lambda: self._depuis(self.plan_downloads), accent=True)
        self.button("🕸 Fichiers oubliés", lambda: self._depuis(self.find_old))
        self.button(T("🎬 Clips et captures de jeu"), lambda: self._depuis(self.find_clips))
        self.button("🔎 Les plus gros fichiers", self.show_largest)
        if ctx.advanced and not ctx.cfg.get("serenity"):
            # Les résidus restent un outil d'expert : invisible en Sérénité.
            self.button("🧹 Résidus d'applications", self.show_residus)
        self.button("✔ Appliquer la sélection…", lambda: self._depuis(self.apply))

        self.list = Checklist(self, ctx, ("Fichier", T("Détail")), box_only=True)
        self.list.pack(fill="both", expand=True)

    def _load_game_spaces(self):
        run_bg(self.ctx.root, self._scan_game_folders, self._show_game_spaces)

    def _scan_game_folders(self):
        folders = {
            "Steam": [r"C:\Program Files (x86)\Steam", r"D:\SteamLibrary", r"E:\SteamLibrary"],
            "Epic Games": [r"C:\Program Files\Epic Games", r"D:\Epic Games", r"E:\Epic Games"],
            "Xbox/Microsoft Store": [r"C:\Program Files\WindowsApps"],
        }
        results = []
        for name, paths in folders.items():
            total = 0
            found_paths = []
            for p in paths:
                if os.path.exists(p):
                    try:
                        s, _ = self._dir_size(p)
                        total += s
                        found_paths.append(p)
                    except Exception:
                        pass
            if total > 0:
                results.append((name, total, found_paths))
        return results

    def _dir_size(self, path):
        total = 0
        count = 0
        try:
            for entry in os.scandir(path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                        count += 1
                    elif entry.is_dir(follow_symlinks=False):
                        s, c = self._dir_size(entry.path)
                        total += s
                        count += c
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            pass
        return total, count

    def _show_game_spaces(self, results, err):
        if err or not results:
            self.game_space_lbl.configure(text=T("Aucun dossier de jeu détecté sur ce PC."))
            return
        lines = []
        for name, size, paths in results:
            lines.append(f"• {name} : {human_size(size)}")
            for p in paths:
                lines.append(f"  → {p}")
        self.game_space_lbl.configure(text=T("\n").join(lines))

    def _show_rows(self, rows, mode, msg):
        self.mode = mode
        self.list.checkable = mode != "old"
        self.list.set_rows(rows)
        self.say(msg)

    def plan_downloads(self):
        folder = storage.downloads_folder()
        moves = storage.plan_downloads(folder)
        self.data = {str(i): m for i, m in enumerate(moves)}
        rows = [dict(id=i, name=os.path.basename(m[0]), info=f"→ {m[2]}/", checked=True, status="info",
                     detail=T("De : {v0}\nVers : {v1}\n\nAnnulable : oui (Journal > Annuler).").format(v0=m[0], v1=m[1]), folders=[m[0]])
                for i, m in self.data.items()]
        self._show_rows(rows, "moves", T("{v0} dans {v1}. "
                        "Les fichiers de type inconnu "
                        "ou en cours de téléchargement sont laissés tranquilles.").format(v0=_p(len(rows), T('fichier à ranger'), T('fichiers à ranger')), v1=folder) if rows else T("Rien à ranger."))

    def _note_nuage(self, ignores):
        """Rappel honnête : des fichiers ne sont pas vraiment sur le disque."""
        if not ignores:
            return ""
        if len(ignores) == 1:
            return (T(" · 1 fichier dans un dossier synchronisé (OneDrive…) a été ignoré "
                    "pour éviter de déclencher son téléchargement."))
        return (T(" · {v0} fichiers dans des dossiers synchronisés (OneDrive…) "
                "ont été ignorés pour éviter de déclencher leurs téléchargements.").format(v0=len(ignores)))

    def find_old(self):
        self.busy(T("Recherche des fichiers oubliés"), "oublies")
        self._ig_old = []
        run_bg(self.ctx.root,
               lambda: storage.find_forgotten(storage.default_folders(), ignores=self._ig_old),
               self._old)

    def _old(self, res, err):
        self.idle()
        rows = [dict(id=str(i), name=p, info=human_size(s), status="info", folders=[p],
                     detail=T("Dernière modification : {v0}\n"
                            "TidyDeck ne touche pas à ces fichiers : à toi de décider (bouton « Ouvrir l'emplacement »).").format(v0=time.strftime(T('%d/%m/%Y'), time.localtime(m))))
                for i, (s, p, m) in enumerate(res or [])]
        self._show_rows(rows, "old",
                        (T("{v0} gros fichier oublié, à examiner toi-même.").format(v0=len(rows)) if len(rows) == 1
                         else T("{v0} gros fichiers oubliés, à examiner toi-même.").format(v0=len(rows)) if rows
                         else T("Rien trouvé."))
                        + self._note_nuage(getattr(self, "_ig_old", None)))

    def find_clips(self):
        self.busy(T("Search for game clips"), "clips")
        run_bg(self.ctx.root, storage.find_clips, self._clips)

    def _clips(self, res, err):
        self.idle()
        self.data, rows, total = {}, [], 0
        for i, (s, p, m, src) in enumerate(res or []):
            self.data[str(i)] = p
            total += s
            rows.append(dict(id=str(i), name=p, info=f"{human_size(s)} · {src}", checked=False, status="info", folders=[p],
                             detail=T("Source probable : {v0}\nDernière modification : {v1}\n\n"
                                    "Rien n'est coché : regarde d'abord (bouton « Ouvrir l'emplacement »). Si tu coches puis valides, "
                                    "le clip va en quarantaine (annulable).").format(v0=src, v1=time.strftime(T('%d/%m/%Y'), time.localtime(m)))))
        self._show_rows(rows, "dupes", T("{v0} de plus de 100 Mo, soit {v1}. Coche ceux dont tu n'as plus besoin.").format(v0=_p(len(rows), T('clip'), T('clips')), v1=human_size(total))
                        if rows else T("Aucun gros clip trouvé dans Vidéos. 🎬"))

    def _fermer_vues(self):
        """Ferme les vues plein-page (plus gros, résidus) et rend la liste.
        Une seule vue à la fois : cliquer sur un bouton du dessus bascule
        instantanément, sans passer par « Retour »."""
        for attr in ("largest", "residus"):
            v = getattr(self, attr, None)
            if v is None:
                continue
            try:
                v.cancel.set()
            except Exception:
                pass
            try:
                v.destroy()
            except tk.TclError:
                pass
            setattr(self, attr, None)
        self.list.pack(fill="both", expand=True)

    def _depuis(self, fn):
        """Point d'entrée commun : la vue ouverte disparaît, puis l'action."""
        self._fermer_vues()
        fn()

    def show_largest(self):
        """Ouvre la vue « plus gros fichiers / dossiers » A LA PLACE de la liste.
        Elle remplace self.list sans quitter la page : pas d'entree de menu en plus."""
        cur = getattr(self, "largest", None)
        if cur is not None:
            try:
                cur.tkraise()
                return
            except tk.TclError:
                self.largest = None
        self._fermer_vues()
        self.say("")
        self.list.pack_forget()
        from UI.Pages.largest_view import LargestView
        self.largest = LargestView(self, self.ctx, on_close=self.hide_largest)
        self.largest.pack(fill="both", expand=True)

    def hide_largest(self):
        cur = getattr(self, "largest", None)
        if cur is not None:
            try:
                cur.cancel.set()
            except Exception:
                pass
            cur.destroy()
        self.largest = None
        self.list.pack(fill="both", expand=True)

    def show_residus(self):
        """Vue « résidus d'applications » : la Phase 0 est en lecture seule,
        aucun fichier n'est déplacé. Remplace la liste, comme les plus gros."""
        cur = getattr(self, "residus", None)
        if cur is not None:
            try:
                cur.tkraise()
                return
            except tk.TclError:
                self.residus = None
        self._fermer_vues()
        self.say("")
        self.list.pack_forget()
        from UI.Pages.residus_view import ResidusView
        self.residus = ResidusView(self, self.ctx, on_close=self.hide_residus)
        self.residus.pack(fill="both", expand=True)

    def hide_residus(self):
        cur = getattr(self, "residus", None)
        if cur is not None:
            try:
                cur.cancel.set()
            except Exception:
                pass
            cur.destroy()
        self.residus = None
        self.list.pack(fill="both", expand=True)

    def apply(self):
        ids = self.list.checked_ids()
        if self.mode not in ("moves", "dupes") or not ids:
            messagebox.showinfo("TidyDeck", T("Lance d'abord une analyse et coche des lignes."))
            return
        if self.mode == "moves":
            moves = [self.data[i] for i in ids]
            lines = [f"{os.path.basename(a)}  →  {c}/" for a, b, c in moves]
            if preview_dialog(self.ctx, T("Aperçu du rangement"),
                              T("1 fichier va être déplacé :") if len(moves) == 1
                              else T("{v0} fichiers vont être déplacés :").format(v0=len(moves)), lines,
                              "Annulable depuis le Journal.", "Oui, ranger"):
                n = storage.apply_moves(moves, self.ctx.journal)
                self.say(_p(n, T("fichier rangé"), T("fichiers rangés")) + ".")
                self.plan_downloads()
        else:
            paths = [self.data[i] for i in ids]
            note = T("Annulable depuis le Journal. L'espace n'est libéré qu'à la purge.")
            avert = cloud.avertissement(paths)
            if avert:
                note = avert + "\n" + note
            if preview_dialog(self.ctx, T("Aperçu : mise de côté"),
                              "1 copie va en quarantaine :" if len(paths) == 1
                              else f"{len(paths)} copies vont en quarantaine :", paths,
                              note, T("Oui, mettre de côté")):
                n, refuses = storage.quarantine_files(paths, self.ctx.journal, "Fichiers mis en quarantaine")
                if refuses:
                    self.say(T("{v0} de côté. "
                            "{v1} : « {v2} » — {v3}").format(v0=_p(n, 'copie mise', 'copies mises'), v1=_p(len(refuses), T('copie refusée'), T('copies refusées')), v2=os.path.basename(refuses[0][0]), v3=refuses[0][1])
                            + (f" (et {_p(len(refuses) - 1, 'autre', 'autres')})" if len(refuses) > 1 else ""))
                else:
                    self.say(_p(n, T("copie mise de côté"), T("copies mises de côté")) + ".")
                self.find_clips()
