"""Réglages Windows « anti-distraction » : valeurs utilisateur (HKCU), réversibles,
avec détection de dérive après une mise à jour Windows."""
import json
from Shared.Models.models import Tweak, RegValue
from Shared.Utils import registry
from Shared.Utils.common import data_dir
from Services.Logger.journal import register_undo
from Shared.Utils.lang import T

CDM = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
ADV = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
ADS = r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"


def _v(key, name, value=0):
    return RegValue(key, name, value)


TWEAKS = [
    Tweak("start_ads", "Masquer les pubs et suggestions du menu Démarrer", "Anti-distraction",
          "Windows y affiche des applications « suggérées » (souvent sponsorisées).",
          "Menu Démarrer plus propre, moins de sollicitations.",
          "Aucun. Même réglage que Paramètres > Personnalisation > Démarrer.",
          [_v(CDM, "SystemPaneSuggestionsEnabled"), _v(CDM, "SubscribedContent-338388Enabled")]),
    Tweak("tips", "Masquer les astuces et notifications « découvrez Windows »", "Anti-distraction",
          "Notifications qui te proposent des fonctions ou des services Microsoft.",
          "Moins d'interruptions pendant que tu travailles ou joues.",
          "Aucun.",
          [_v(CDM, "SubscribedContent-338389Enabled"), _v(CDM, "SoftLandingEnabled")]),
    Tweak("lock_ads", "Masquer les pubs de l'écran de verrouillage", "Anti-distraction",
          "Images et textes promotionnels sur l'écran de verrouillage.",
          "Écran de verrouillage calme.", "Aucun.",
          [_v(CDM, "RotatingLockScreenOverlayEnabled"), _v(CDM, "SubscribedContent-338387Enabled")]),
    Tweak("settings_ads", "Masquer les suggestions dans Paramètres", "Anti-distraction",
          "Bandeaux de suggestions dans Paramètres.", "Paramètres plus lisible.", "Aucun.",
          [_v(CDM, "SubscribedContent-338393Enabled"), _v(CDM, "SubscribedContent-353694Enabled"),
           _v(CDM, "SubscribedContent-353696Enabled")]),
    Tweak("silent_apps", "Empêcher l'installation automatique d'applis sponsorisées", "Anti-distraction",
          "Windows peut installer des applis « promues » sans te demander.",
          "Évite que de nouvelles applis inutiles apparaissent.",
          "Aucun. Ne désinstalle PAS celles déjà présentes.",
          [_v(CDM, "SilentInstalledAppsEnabled"), _v(CDM, "PreInstalledAppsEnabled"),
           _v(CDM, "OemPreInstalledAppsEnabled"), _v(CDM, "ContentDeliveryAllowed")]),
    Tweak("explorer_ads", "Masquer les annonces de l'Explorateur", "Anti-distraction",
          "Messages promotionnels (ex. OneDrive, Microsoft 365) dans l'Explorateur.",
          "Explorateur sans messages parasites.", "Aucun.",
          [_v(ADV, "ShowSyncProviderNotifications")]),
    Tweak("ad_id", "Désactiver l'identifiant publicitaire", "Anti-distraction",
          "Numéro qui permet aux applis de te proposer des pubs ciblées.",
          "Moins de suivi publicitaire.", "Aucun : les pubs seront simplement moins ciblées.",
          [_v(ADS, "Enabled")]),
    Tweak("file_ext", "Afficher les extensions de fichiers (.pdf, .exe...)", "Confort et sécurité",
          "Windows cache par défaut la fin des noms de fichiers.",
          "Plus clair, et plus sûr : on repère un faux « facture.pdf.exe ».",
          "Aucun.", [_v(ADV, "HideFileExt", 0)]),
]
BY_ID = {t.id: t for t in TWEAKS}
STATE = data_dir() / "tweaks_state.json"


def _state():
    """{id_du_réglage: {"previous": {clé|valeur: ancienne valeur}}}"""
    try:
        d = json.loads(STATE.read_text(encoding="utf-8"))
        return {i: {} for i in d} if isinstance(d, list) else d
    except Exception:
        return {}


def _save_state(d):
    STATE.write_text(json.dumps(d), encoding="utf-8")


def _applied():
    return list(_state())


def is_active(t):
    return all(registry.read(t.hive, v.key, v.name) == v.value for v in t.values)


def status(t):
    """'active' | 'drift' (appliqué un jour puis défait, ex. par une mise à jour) | 'inactive'"""
    if is_active(t):
        return "active"
    return "drift" if t.id in _applied() else "inactive"


def drift():
    return [t for t in TWEAKS if status(t) == "drift"]


def _default(v):
    return 1 if v.value == 0 else 0           # valeur « par défaut Windows » (interrupteurs 0/1)


def revert_target(t, v):
    """Valeur de remise : l'ancienne valeur mémorisée par TidyDeck, sinon le réglage par défaut de Windows."""
    saved = _state().get(t.id, {}).get("previous", {})
    key = f"{v.key}|{v.name}"
    if key in saved:
        return saved[key], T("valeur d'origine mémorisée")
    return _default(v), T("réglage par défaut de Windows")


def current_text(t):
    lines = []
    for v in t.values:
        cur = registry.read(t.hive, v.key, v.name)
        lines.append(f"{registry.full_path(t.hive, v.key)}\n    " + T("valeur « {v0} » : actuellement {v1}  →  {v2}")
                     .format(v0=v.name, v1=T("absente") if cur is None else cur, v2=v.value))
    return lines


def revert_text(t):
    lines = []
    for v in t.values:
        cur = registry.read(t.hive, v.key, v.name)
        tgt, why = revert_target(t, v)
        lines.append(f"{registry.full_path(t.hive, v.key)}\n    " + T("valeur « {v0} » : actuellement {v1}  →  {v2}  ({v3})")
                     .format(v0=v.name, v1=cur, v2=T("suppression (retour au défaut Windows)") if tgt is None else tgt, v3=why))
    return lines


def apply(ids, journal):
    """Applique, puis RELIT le registre pour vérifier. Renvoie la liste des réglages non pris en compte."""
    previous, st = [], _state()
    for tid in ids:
        t = BY_ID[tid]
        prev = {}
        for v in t.values:
            cur = registry.read(t.hive, v.key, v.name)
            prev[f"{v.key}|{v.name}"] = cur
            previous.append([t.hive, v.key, v.name, cur])
            registry.write(t.hive, v.key, v.name, v.value)
        st[tid] = {"previous": prev}
    _save_state(st)
    journal.add("tweaks", ("{v0} réglage Windows appliqué" if len(ids) == 1
                           else "{v0} réglages Windows appliqués").format(v0=len(ids)),
                ", ".join(BY_ID[i].name for i in ids),
                {"previous": previous, "ids": list(ids)})
    return [i for i in ids if not is_active(BY_ID[i])]


def revert(ids, journal):
    """Remet les réglages comme avant (décocher). Renvoie ceux qui sont restés actifs malgré tout."""
    before, st = [], _state()
    for tid in ids:
        t = BY_ID[tid]
        for v in t.values:
            before.append([t.hive, v.key, v.name, registry.read(t.hive, v.key, v.name)])
            tgt, _ = revert_target(t, v)
            if tgt is None:
                registry.delete(t.hive, v.key, v.name)
            else:
                registry.write(t.hive, v.key, v.name, tgt)
        if is_active(t):                       # l'ancienne valeur était déjà « active » : on force le défaut Windows
            for v in t.values:
                registry.write(t.hive, v.key, v.name, _default(v))
        st.pop(tid, None)
    _save_state(st)
    journal.add("tweaks_off", ("{v0} réglage remis comme avant" if len(ids) == 1
                               else "{v0} réglages remis comme avant").format(v0=len(ids)),
                ", ".join(BY_ID[i].name for i in ids),
                {"before": before, "ids": list(ids)})
    return [i for i in ids if is_active(BY_ID[i])]


def forget(ids):
    st = _state()
    for i in ids:
        st.pop(i, None)
    _save_state(st)


@register_undo("tweaks")
def _undo(d):
    for hive, key, name, prev in reversed(d["previous"]):
        if prev is None:
            registry.delete(hive, key, name)
        else:
            registry.write(hive, key, name, prev)
    forget(d["ids"])
    return f"{len(d['ids'])} {'réglage' if len(d['ids']) == 1 else 'réglages'} remis comme avant."


@register_undo("tweaks_off")
def _undo_off(d):
    st = _state()
    for hive, key, name, prev in reversed(d["before"]):
        if prev is None:
            registry.delete(hive, key, name)
        else:
            registry.write(hive, key, name, prev)
    for i in d["ids"]:
        st.setdefault(i, {})
    _save_state(st)
    n = len(d["ids"])
    return (T("{v0} réglage réappliqué.").format(v0=n) if n == 1
            else T("{v0} réglages réappliqués.").format(v0=n))
