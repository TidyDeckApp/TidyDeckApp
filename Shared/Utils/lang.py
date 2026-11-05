"""Traduction FR/EN — zéro dépendance.

Le français est la langue-source du programme : les chaînes du code restent
en français et `T()` ne fait que remplacer par l'anglais quand la langue est
« en ». Une chaîne absente du dictionnaire reste donc en français — jamais
de clé brute ni de plantage. Les chaînes dynamiques passent par des gabarits :
`T("{n} fichier ignoré").format(n=1)`.

La diction FR→EN vit dans `translations.py` (dictionnaire `EN`), ce qui permet
de la compléter sans toucher au code et de la valider par les tests : accord
des gabarits {…}, apostrophes droites, zéro doublon.
"""

LANGS = [("fr", "Français"), ("en", "English")]

NOMS_LANGUES = {
    "fr": {"fr": "Français", "en": "Anglais"},
    "en": {"fr": "French", "en": "English"},
}

try:                                     # diction livrée avec le code
    from Shared.Utils.translations import EN as _EN_MAP
except Exception:                        # jamais bloquant si le fichier manque
    _EN_MAP = {}

_lang = "fr"


def set_lang(code):
    global _lang
    _lang = code if code in {c for c, _ in LANGS} else "fr"


def get_lang():
    return _lang


def nom_langue(code=None):
    code = code or _lang
    return NOMS_LANGUES.get(_lang, NOMS_LANGUES["fr"]).get(code, code)


def T(text):
    """Traduit si la langue est l'anglais ; retourne le français sinon (passe-partout)."""
    if _lang == "fr" or not isinstance(text, str) or not text:
        return text
    return _EN_MAP.get(text, text)
