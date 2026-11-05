# -*- coding: utf-8 -*-
"""Fichiers « dans le nuage » : OneDrive, Dropbox, Google Drive…

Un fichier placeholder (matérialisé à la demande) n'existe pas vraiment sur le
disque : ses octets sont chez le fournisseur, il n'occupe que quelques Ko.
Le moindre accès en lecture le **télécharge en entier**. Deux dangers directs :

  * la recherche de doublons qui calcule une empreinte sur un fichier de 40 Go
    et rapatrie les 40 Go ;
  * « Gros éléments » qui annonce un fichier du nuage comme s'il encombrait le
    disque, alors qu'il n'y a presque rien.

On reconnaît ces fichiers à leurs attributs Windows (GetFileAttributes) :

  0x400000  FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS   données pas sur le disque
  0x40000   FILE_ATTRIBUTE_RECALL_ON_OPEN          téléchargé à l'ouverture
  0x1000    FILE_ATTRIBUTE_OFFLINE                 données hors de portée

Les règles appliquées : jamais ouverts, jamais hachés, jamais comptés dans une
taille, jamais mis en quarantaine (déplacer un placeholder le fait passer pour un
vrai fichier et peut déclencher une suppression côté nuage).
"""
import os

from Shared.Utils import dossiers
from Shared.Utils.lang import T

NUAGE = 0x400000 | 0x40000 | 0x1000

# Variables d'environnement posées par les clients de synchronisation.
_ENV_SYNC = ("OneDrive", "OneDriveConsumer", "OneDriveCommercial",
            "Dropbox", "GOOGLE_DRIVE_PATH", "GDRIVE_ROOT")


def racines_synchronisees():
    """Racines des dossiers synchronisés connues (OneDrive, Dropbox, Drive).

    Les variables d'environnement ne suffisent pas : elles absentes quand le client
    tourne en session service, et OneDrive pour l'entreprise ne pose pas toujours
    la bonne. Le dossier connu « OneDrive » rendu par Windows complète la liste.
    """
    vus, out = set(), []

    def _ajoute(brut):
        if not brut:
            return
        try:
            r = os.path.realpath(os.path.expanduser(brut))
        except OSError:
            return
        cle = os.path.normcase(r)
        if cle not in vus and os.path.isdir(r):
            vus.add(cle)
            out.append(r)

    for nom in _ENV_SYNC:
        _ajoute(os.environ.get(nom))
    _ajoute(dossiers.connu("onedrive"))
    return out


def est_hors_ligne(chemin) -> bool:
    """Vrai si les données du fichier ne sont pas réellement sur le disque.

    Ne lève jamais : un fichier qui n'existe plus ou dont l'attribut est
    illisible n'est pas un placeholder, on le traite comme un fichier normal
    (les appelants gèrent déjà l'erreur de leur côté).
    """
    try:
        # st_file_attributes est fourni par Python sur Windows ; absent ailleurs.
        attrs = getattr(os.stat(chemin), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attrs & NUAGE)


def racine_synchronisee(chemin):
    """La racine de synchronisation qui contient `chemin`, sinon None."""
    c = os.path.normcase(os.path.realpath(chemin))
    for r in racines_synchronisees():
        rc = os.path.normcase(r)
        if c == rc or c.startswith(rc + os.sep):
            return r
    return None


def est_synchronise(chemin) -> bool:
    return racine_synchronisee(chemin) is not None


def avertissement(chemins) -> str:
    """Phrase à montrer AVANT de déplacer/copier ces fichiers. Vide si rien à dire.

    On ne liste que les fichiers réellement concernés : une liste qui fait peur
    pour rien n'avertit plus personne."""
    concernes = [c for c in chemins if est_synchronise(c)]
    if not concernes:
        return ""
    noms = ", ".join(os.path.basename(c) for c in concernes[:4])
    n_autres = len(concernes) - 4
    plus = ((T(" et {v0} autre") if n_autres == 1 else T(" et {v0} autres")).format(v0=n_autres)
            if n_autres > 0 else "")
    if len(concernes) == 1:
        return (T("⚠ {v0} fichier est dans un dossier synchronisé "
                  "({v1}). Sa copie reste peut-être dans le nuage : le déplacer "
                  "ici ne libère pas la place, et le supprimer là-bas demandera un "
                  "gestionnaire du compte. Ouvre plutôt le dossier dans l'explorateur "
                  "pour décider là-bas.").format(v0=len(concernes), v1=noms + plus))
    return (T("⚠ {v0} fichiers sont dans un dossier synchronisé "
              "({v1}). Leur copie reste peut-être dans le nuage : les déplacer "
              "ici ne libère pas la place, et les supprimer là-bas demandera un "
              "gestionnaire du compte. Ouvre plutôt le dossier dans l'explorateur "
              "pour décider là-bas.").format(v0=len(concernes), v1=noms + plus))
