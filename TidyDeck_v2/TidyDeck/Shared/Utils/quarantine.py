"""Quarantaine : on déplace au lieu de supprimer -> tout reste annulable.

Les fichiers mis de côté restent sur le disque jusqu'à la purge
(automatique après N jours, ou bouton « Libérer l'espace maintenant »).
"""
import os
import shutil
import time
from Shared.Utils.common import data_dir, entry_size
from Shared.Utils.lang import T
from Shared.Utils import cloud
from Services.Logger.journal import register_undo


def root():
    p = data_dir() / "quarantine"
    p.mkdir(parents=True, exist_ok=True)
    return p


class FichierDansLeNuage(OSError):
    """Placeholder OneDrive/Dropbox : pas de données sur le disque. Le déplacer
    le téléchargerait, et ferait croire à une suppression côté nuage."""


def move_in(src, run_id, index) -> str:
    if cloud.est_hors_ligne(src):
        raise FichierDansLeNuage(
            T("« {v0} » n'est pas vraiment sur ton disque : il est "
              "dans un dossier synchronisé et n'occupe presque aucune place. Le déplacer "
              "le téléchargerait en entier.").format(v0=os.path.basename(src)))
    d = root() / run_id
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{index:06d}_{os.path.basename(src)}"
    shutil.move(src, str(dest))
    return str(dest)


def restore(pairs):
    ok = missing = conflict = 0
    for orig, dest in pairs:
        if not os.path.exists(dest):
            missing += 1
        elif os.path.exists(orig):
            conflict += 1
        else:
            try:
                os.makedirs(os.path.dirname(orig), exist_ok=True)
                shutil.move(dest, orig)
                ok += 1
            except OSError:
                missing += 1
    return ok, missing, conflict


def purge(older_than_days=0) -> int:
    """Supprime pour de bon les lots plus vieux que N jours. Renvoie les octets libérés."""
    freed, now = 0, time.time()
    for d in root().iterdir():
        if d.is_dir() and (older_than_days == 0 or now - d.stat().st_mtime > older_than_days * 86400):
            freed += entry_size(d)[0]
            shutil.rmtree(d, ignore_errors=True)
    return freed


def total_size() -> int:
    return entry_size(root())[0]


@register_undo("pairs")
def _undo_pairs(data):
    ok, missing, conflict = restore(data["pairs"])
    msg = T("{v0} élément(s) remis à leur place.").format(v0=ok)
    if missing:
        msg += T(" {v0} introuvable(s) (quarantaine déjà purgée ?).").format(v0=missing)
    if conflict:
        msg += T(" {v0} ignoré(s) : un fichier existe déjà à l'emplacement d'origine.").format(v0=conflict)
    return msg
