"""Rapport « Santé du PC » : chaque ligne dit ce qu'on a vu ET quoi faire."""
import os
import shutil
from Shared.Models.models import Check
from Shared.Utils.common import IS_WINDOWS, human_size, is_admin
from Shared.Utils import winapi, registry, quarantine
from Core.Startup import startup
from Shared.Utils.lang import T

RECYCLE_SHELL = "::{645FF040-5081-101B-9F08-00AA002F9451}"


def run_checks(serenity=False):
    out = []
    drive = (os.environ.get("SystemDrive", "C:") + "\\") if IS_WINDOWS else "/"
    du = shutil.disk_usage(drive)
    pct = du.free / du.total * 100
    st = "ok" if pct >= 20 else ("info" if pct >= 10 else "warn")
    out.append(Check(T("Espace libre sur le disque système"), st,
                     (T("Il te reste de la place.") if st == "ok" else T("L'espace commence à manquer."))
                     if serenity else T("{v0} libres ({v1:.0f} %).").format(v0=human_size(du.free), v1=pct),
                     "" if st == "ok" else T("Passe par l'onglet Nettoyage, puis Rangement. "
                     "Sous 10 %, Windows ralentit et les mises à jour peuvent échouer."),
                     path=drive, location=T("le disque {v0}").format(v0=drive)))
    gb = du.free / (1 << 30)
    aaa = int(gb // 90)
    out.append(Check("Place pour un nouveau jeu", "ok" if gb >= 100 else ("info" if gb >= 50 else "warn"),
                     (T("Largement de quoi installer un gros jeu.") if gb >= 100 else T("Un gros jeu pourrait être serré."))
                     if serenity else
                     (T("{v0:.0f} Go libres — environ {v1} jeu AAA de 90 Go.") if aaa <= 1
                      else T("{v0:.0f} Go libres — environ {v1} jeux AAA de 90 Go.")).format(v0=gb, v1=aaa),
                     "" if gb >= 100 else T("Onglets Nettoyage et Rangement pour récupérer de la place, ou installe tes jeux sur un autre disque."),
                     path=drive, location=T("le disque {v0}").format(v0=drive)))
    days = winapi.uptime_days()
    if IS_WINDOWS:
        st = "ok" if days < 7 else ("info" if days < 14 else "warn")
        out.append(Check(T("Dernier redémarrage"), st, (T("Ton PC tourne depuis un moment.") if days >= 7 else T("Tout est frais.")) if serenity else T("Allumé depuis {v0:.1f} jour(s).").format(v0=days),
                         "" if st == "ok" else T("Redémarre complètement (Démarrer > Redémarrer) : "
                         "cela libère la mémoire et finalise des mises à jour. "
                         "L'arrêt « rapide » ne suffit pas.")))
        pending = (registry.read("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired", "") is not None
                   or registry.read("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending", "") is not None)
        out.append(Check(T("Redémarrage en attente"), "warn" if pending else "ok",
                         (T("Une mise à jour attend un redémarrage, quand tu veux.") if pending else T("Rien en attente."))
                         if serenity else (T("Windows attend un redémarrage.") if pending else T("Rien en attente.")),
                         T("Redémarre dès que possible pour terminer l'installation.") if pending else "",
                         settings="windowsupdate", location=T("Paramètres > Windows Update")))
    n = sum(1 for e in startup.list_entries() if e["enabled"]) if IS_WINDOWS else 0
    total = len(startup.list_entries()) if IS_WINDOWS else 0
    if IS_WINDOWS:
        st = "ok" if n <= 8 else ("info" if n <= 15 else "warn")
        out.append(Check(T("Programmes au démarrage"), st, (T("Tout est fluide au démarrage.") if st == "ok" else T("Le démarrage pourrait être allégé.")) if serenity else T("{v0} trouvés, dont {v1} actifs.").format(v0=total, v1=n),
                         "" if st == "ok" else T("Va dans l'onglet Démarrage et désactive ce dont tu n'as pas besoin tout de suite."),
                         settings="startupapps", location=T("Paramètres > Applications > Démarrage")))
    size, cnt = winapi.recycle_bin_info()
    out.append(Check("Corbeille", "info" if size > 1 << 30 else "ok", T("Rien d'urgent.") if serenity else (T("{v0} ({v1} élément).") if cnt == 1 else T("{v0} ({v1} éléments).")).format(v0=human_size(size), v1=cnt),
                     T("Vide-la depuis l'onglet Nettoyage si tu n'as plus besoin de ces fichiers.") if size > 1 << 30 else "",
                     shell=RECYCLE_SHELL, location=T("la Corbeille")))
    q = quarantine.total_size()
    out.append(Check("Quarantaine TidyDeck", "info" if q else "ok",
                     T("Des fichiers attendent d'être libérés (annulable).") if serenity and q else (T("Rien en attente.") if serenity else T("{v0} mis de côté (annulable).").format(v0=human_size(q))),
                     T("Onglet Nettoyage > « Libérer l'espace maintenant » pour les supprimer définitivement.") if q else "",
                     path=str(quarantine.root()), location=T("le dossier de quarantaine TidyDeck")))
    out.append(Check("Droits de TidyDeck", "info",
                     T("Administrateur.") if is_admin() else T("Utilisateur normal."),
                     T("Le mode normal suffit pour presque tout. Admin : seulement pour les temporaires de Windows et les points de restauration.")))
    return out
