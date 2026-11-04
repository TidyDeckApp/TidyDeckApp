# -*- coding: utf-8 -*-
"""Traduire un refus de Windows en français qui dit quoi faire.

Sur un PC géré par une entreprise, une écriture dans le registre ou sur un
service peut être refusée MÊME en étant administrateur : c'est une règle de
groupe (GPO). Répondre « droits insuffisants » dans ce cas-là n'aide personne :
l'utilisateur relance en administrateur, prend le même refus, et croit que le
logiciel est cassé. On nomme la vraie cause et la seule issue."""
import re
from Shared.Utils.lang import T

SANS_DROITS = ("il faut les droits administrateur. Clique « Relancer en "
               "administrateur », ou demande à la personne qui s'occupe du PC.")
GPO = ("une règle de groupe (GPO) de ton organisation le refuse : tu es "
       "administrateur et Windows dit quand même non. Ce n'est pas une question de "
       "droits à toi — relancer en administrateur ne changerait rien. Seul le "
       "gestionnaire du poste peut lever ce blocage.")
CODES = {
    5: "accès refusé par Windows",
    1312: "emplacement protégé",
    1314: "privilège insuffisant pour écrire à cet endroit",
    1058: "le service est désactivé et ne peut pas démarrer",
    1060: "ce service n'existe pas sur cette machine",
    1075: "un autre service en dépend : on ne peut pas le toucher isolément",
    1076: "le service a déjà été arrêté à cause d'une dépendance",
}
REFUS_DROITS = (5, 1312, 1314)


def _dans_sortie_sc(sortie):
    """Le numero Windows dans une ligne `[SC] ...` de sc.exe, une fois par trait.

    Le texte est traduit (« FAILED 1060 » en anglais, « Échec(s) 1060 » en
    francais, « FEHLER 1060 » en allemand) : ce qui ne change jamais, c'est le
    debut de ligne et le fait que le code numerique soit le dernier nombre de
    cette ligne. S'y référer évite de rester aveugle sur un Windows non anglais."""
    for ligne in (sortie or "").splitlines():
        ligne = ligne.strip()
        if not ligne.upper().startswith("[SC]"):
            continue
        nombres = re.findall(r"\d+", ligne)
        if nombres:
            return int(nombres[-1])
    return None


def numero(code=None, erreur=None, sortie=""):
    """Le code Windows, d'où qu'il vienne : code de retour, exception, sortie de sc.exe.

    Le code de retour du processus passe avant tout le reste : sc.exe y recopie le
    numero d'erreur Windows, et lui ne dépend d'aucune langue."""
    if code:
        return int(code)
    c = getattr(erreur, "winerror", None)
    if c is not None:
        return int(c)
    m = re.search(r"FAILED\s+(\d+)", sortie or "")
    if m:
        return int(m.group(1))
    return _dans_sortie_sc(sortie)


def motif_refus(action, code=None, erreur=None, sortie=""):
    """Phrase complète, en français, qui se termine par la conduite à tenir.

    `action` se dit à l'infinitif (« désactiver le service X », « modifier cette
    entrée de démarrage ») : le message doit rester compréhensible sans ouvrir le
    Gestionnaire des tâches."""
    n = numero(code, erreur, sortie)
    est_refus = n in REFUS_DROITS or isinstance(erreur, PermissionError)
    if est_refus:
        from Shared.Utils.common import is_admin
        if is_admin():
            return T("Impossible de {v0} : {v1}").format(v0=action, v1=T(GPO))
        return T("Impossible de {v0} : {v1}").format(v0=action, v1=T(SANS_DROITS))
    if n in CODES:
        return T("Impossible de {v0} : {v1} (code Windows {v2})").format(v0=action, v1=T(CODES[n]), v2=n)
    if n is not None:
        return T("Impossible de {v0} : Windows a refusé (code {v1}).").format(v0=action, v1=n)
    détail = str(erreur).strip() if erreur is not None else T("raison inconnue")
    return T("Impossible de {v0} : {v1}.").format(v0=action, v1=détail)
