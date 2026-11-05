"""Catalogue du nettoyage : chaque entrée dit CE QUE c'est, OÙ c'est, et le RISQUE.
Rien n'est caché : tout ce que TidyDeck peut toucher est dans ce fichier."""
import os
from Shared.Models.models import CleanItem
from Shared.Utils.lang import T


def _e(p):
    return os.path.expandvars(p)


def _browser(id_, name, base, subs, process):
    return CleanItem(
        id=id_, name=f"{name} — cache",
        what=T("Copies temporaires de pages, images et scripts déjà visités avec {v0}, "
               "gardées pour accélérer l'affichage.").format(v0=name),
        why_safe=T("Le navigateur les retélécharge au besoin. Mots de passe, favoris, historique "
                 "et connexions ne sont pas touchés (ils sont dans d'autres fichiers)."),
        paths=[_e(base + "\\" + s) for s in subs], process=process,
        risk=T("Aucun (les premières pages se chargent un peu plus lentement ensuite)"), icon="🌐")


def _opera_paths(la):
    subs = ["Cache", "Code Cache", "GPUCache", "Default\\Cache", "Default\\Code Cache", "Default\\GPUCache"]
    bases = [la + "\\Opera Software\\Opera Stable", la + "\\Opera Software\\Opera GX Stable"]
    return [_e(b + "\\" + sub) for b in bases for sub in subs]


def build_catalog():
    la = r"%LOCALAPPDATA%"
    return [
        CleanItem(
            id="temp_user", name="Fichiers temporaires (utilisateur)",
            what="Fichiers de travail laissés par les programmes (installateurs, documents "
                 "ouverts, archives dézippées...).",
            why_safe=T("Les programmes les recréent si besoin. Ceux utilisés en ce moment sont "
                     "ignorés automatiquement."),
            paths=[_e(r"%TEMP%")]),
        CleanItem(
            id="temp_win", name="Fichiers temporaires (Windows)",
            what="Dossier temporaire partagé par Windows et les installateurs.",
            why_safe=T("Même principe que ci-dessus. Les fichiers en cours d'usage sont ignorés."),
            paths=[_e(r"%SystemRoot%\Temp")], needs_admin=True,
            preselect=False, risk=T("Aucun (nécessite le mode administrateur)")),
        CleanItem(
            id="dx", name="Cache des shaders (DirectX)",
            what="Effets graphiques précompilés par ta carte graphique pour les jeux.",
            why_safe="Les jeux les reconstruisent automatiquement.",
            paths=[_e(la + r"\D3DSCache")], preselect=False,
            risk="Faible : le 1er lancement de certains jeux peut saccader un moment.", icon="🎮"),
        CleanItem(
            id="nvidia", name="Cache NVIDIA (shaders & compilateur)",
            what="Cache de compilation des shaders NVIDIA (GLCache, DXCache, etc.).",
            why_safe="NVIDIA et les jeux les reconstruisent automatiquement au prochain lancement.",
            paths=[_e(la + r"\NVIDIA\GLCache"), _e(la + r"\NVIDIA\DXCache"),
                   _e(la + r"\NVIDIA Corporation\NV_Cache"),
                   _e(r"%ProgramData%\NVIDIA Corporation\NV_Cache")],
            preselect=False, icon="🎮",
            risk=T("Faible : le 1er lancement d'un jeu peut être un peu plus long")),
        _browser("chrome", "Google Chrome", la + r"\Google\Chrome\User Data\*",
                 ["Cache", "Code Cache", "GPUCache"], "chrome.exe"),
        _browser("edge", "Microsoft Edge", la + r"\Microsoft\Edge\User Data\*",
                 ["Cache", "Code Cache", "GPUCache"], "msedge.exe"),
        _browser("brave", "Brave", la + r"\BraveSoftware\Brave-Browser\User Data\*",
                 ["Cache", "Code Cache", "GPUCache"], "brave.exe"),
        CleanItem(
            id="opera", name="Opera / Opera GX — cache",
            what="Copies temporaires de pages, images et scripts déjà visités avec Opera ou Opera GX.",
            why_safe=T("Le navigateur les retélécharge au besoin. Mots de passe, favoris, historique et connexions "
                     "ne sont pas touchés."),
            paths=_opera_paths(la), process="opera.exe", icon="🌐",
            risk=T("Aucun (les premières pages se chargent un peu plus lentement ensuite)")),
        _browser("firefox", "Mozilla Firefox", la + r"\Mozilla\Firefox\Profiles\*",
                 ["cache2"], "firefox.exe"),
        CleanItem(
            id="recycle", name="Corbeille",
            what="Fichiers que tu as déjà supprimés mais qui occupent encore de la place.",
            why_safe=T("Tu les as supprimés toi-même. ATTENTION : seule action NON annulable de TidyDeck."),
            paths=[], special="recycle_bin", preselect=False, icon="🗑",
            risk=T("Définitif : une Corbeille vidée ne se récupère pas.")),
    ]
