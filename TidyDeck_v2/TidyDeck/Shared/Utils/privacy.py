"""Mode « Discret » (stream) : masque le nom d'utilisateur, du PC et les chemins
personnels a l'ecran.

Regles (voir V1-mode-discret.md) :
  - masquage a l'AFFICHAGE uniquement, jamais dans la donnee ;
  - aucune table reel <-> alias sur le disque : tout est recalcule depuis
    l'environnement a chaque fois, rien n'est persiste ;
  - FAIL-CLOSED : si le masquage echoue, on affiche « ••• » et jamais le texte brut.
    Un doute = masque.
  - le verrou est ici, dans la fonction basse, pas dans les boutons : toute chaine
    venant du systeme doit passer par mask() avant d'arriver a l'ecran."""
import os
import re
from pathlib import Path

MASK = "•••"
VARS = ("USERNAME", "USER", "COMPUTERNAME")
_cache = None


def _patterns():
    global _cache
    if _cache is not None:
        return _cache
    pats = []
    try:
        home = str(Path.home())
    except Exception:
        home = ""
    if home:
        pats.append((re.compile(re.escape(home), re.I), "~"))
    for var in VARS:
        try:
            v = os.environ.get(var)
        except Exception:
            v = None
        if v and len(v) > 2:
            pats.append((re.compile(re.escape(v), re.I), MASK))
    _cache = pats
    return pats


def mask(text, enabled):
    if not enabled or not text:
        return text
    try:
        out = str(text)
        for pat, rep in _patterns():
            out = pat.sub(rep, out)
        return out
    except Exception:
        return MASK
