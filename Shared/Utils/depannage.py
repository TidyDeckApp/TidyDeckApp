"""Journal de diagnostic pour les erreurs muettes : jamais d'alarme, juste une trace.

Module autonome (aucun import interne) : il ne peut pas casser à cause du
reste de l'application, et il ne remonte JAMAIS d'exception lui-même.
Le fichier reste sur le PC (aucun envoi), et sa taille est plafonnée.
"""
import os
import sys
import time
import traceback

TAILLE_MAX = 512_000


def chemin_log():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    dossier = os.path.join(base, "TidyDeck")
    try:
        os.makedirs(dossier, exist_ok=True)
    except OSError:
        return None
    return os.path.join(dossier, "debug.log")


def _tronquer(chemin):
    try:
        if os.path.getsize(chemin) <= TAILLE_MAX:
            return
        with open(chemin, "rb") as fh:
            fh.seek(-(TAILLE_MAX // 2), os.SEEK_END)
            reste = fh.read()
        with open(chemin, "wb") as fh:
            fh.write(b"[...] " + reste)
    except OSError:
        pass


def _masque(texte, aguiche):
    """Remplace chaque occurrence (insensible à la casse) de aguiche par
    %USERPROFILE%."""
    sortie = ""
    bas = texte.lower()
    cle = aguiche.lower()
    i = 0
    while True:
        j = bas.find(cle, i)
        if j < 0:
            return sortie + texte[i:]
        sortie += texte[i:j] + "%USERPROFILE%"
        i = j + len(aguiche)


def _anonymise(texte):
    """Remplace le chemin du profil (C:\\Users\\<pseudo> ou /home/<pseudo>) par
    %USERPROFILE%, sous sa forme brute et sous sa forme échappée telle que
    repr() et les tracebacks l'écrivent (C:\\\\Users\\\\<pseudo>). Le journal ne
    doit jamais porter le nom d'utilisateur, même s'il reste local."""
    try:
        maison = os.path.expanduser("~")
        if not maison or maison in ("~", "/", "\\") or len(maison) < 4:
            return texte
        sortie = _masque(texte, maison)
        echappe = maison.replace("\\", "\\\\")
        if echappe != maison:
            sortie = _masque(sortie, echappe)
        return sortie
    except Exception:
        return texte


def noter(etape, exc=None):
    """Note l'exception en cours (ou celle donnée) sans jamais lever d'erreur."""
    try:
        chemin = chemin_log()
        if not chemin:
            return
        if exc is None:
            exc = sys.exc_info()[1]
        bloc = "%s | %s | %r\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), etape, exc)
        if exc is not None:
            bloc += "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        bloc = _anonymise(bloc)
        with open(chemin, "a", encoding="utf-8", errors="replace") as fh:
            fh.write(bloc)
        _tronquer(chemin)
    except Exception:
        pass
