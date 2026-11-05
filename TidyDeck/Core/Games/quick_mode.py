"""Mode Jeu rapide : repère des applis gourmandes ouvertes et les ferme POLIMENT
(comme un clic sur la croix : rien n'est forcé, tes documents ne sont pas perdus)."""
import csv
import io
import re
from Shared.Utils.common import IS_WINDOWS, run_cmd

KNOWN = {  # exe : (nom, remarque)
    "chrome.exe": ("Google Chrome", "Beaucoup de mémoire. Tes onglets peuvent être restaurés à la réouverture."),
    "msedge.exe": ("Microsoft Edge", "Beaucoup de mémoire."),
    "firefox.exe": ("Firefox", "Beaucoup de mémoire."),
    "brave.exe": ("Brave", "Beaucoup de mémoire."),
    "discord.exe": ("Discord", "Garde-le si tu joues en vocal avec des amis."),
    "spotify.exe": ("Spotify", "Garde-le si tu joues avec de la musique."),
    "ms-teams.exe": ("Microsoft Teams", "Utile à fermer pendant une session de jeu."),
    "teams.exe": ("Microsoft Teams (ancien)", "Utile à fermer pendant une session de jeu."),
    "onedrive.exe": ("OneDrive", "La synchronisation reprendra à la réouverture."),
    "wallpaper64.exe": ("Wallpaper Engine", "Fond animé : consomme du processeur et du GPU."),
    "adobeupdateservice.exe": ("Mises à jour Adobe", "Sans danger à fermer."),
}


def list_running():
    if not IS_WINDOWS:
        return []
    _, out = run_cmd(["tasklist", "/FO", "CSV", "/NH"], 20)
    agg = {}
    for row in csv.reader(io.StringIO(out)):
        if len(row) >= 5 and row[0].lower() in KNOWN:
            mem = int(re.sub(r"\D", "", row[4]) or 0) * 1024   # tasklist donne des Ko
            a = agg.setdefault(row[0].lower(), {"exe": row[0].lower(), "count": 0, "mem": 0})
            a["count"] += 1
            a["mem"] += mem
    res = []
    for exe, a in agg.items():
        a["label"], a["note"] = KNOWN[exe]
        res.append(a)
    return sorted(res, key=lambda x: -x["mem"])


def close_politely(exe):
    """Demande la fermeture (sans /F : aucune fermeture forcée)."""
    rc, _ = run_cmd(["taskkill", "/IM", exe], 15)
    return rc == 0
