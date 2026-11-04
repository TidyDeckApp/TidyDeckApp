"""Services Windows NON essentiels (liste courte, conservatrice). Les services vitaux ne figurent PAS ici.
Désactivation réversible : l'ancien mode de démarrage est mémorisé."""
import json
from Shared.Utils.common import IS_WINDOWS, data_dir, is_admin, run_cmd, run_ps
from Services.Logger.journal import register_undo
from Shared.Utils.lang import T

SERVICES = [
    dict(id="DiagTrack", name="Télémétrie (expériences utilisateur connectées)", level="safe",
         what="Envoie des données de diagnostic à Microsoft.", risk="Aucun pour l'usage courant."),
    dict(id="MapsBroker", name="Cartes téléchargées", level="safe",
         what="Met à jour les cartes hors-ligne de l'appli Cartes.", risk="Aucun si tu n'utilises pas l'appli Cartes."),
    dict(id="RetailDemo", name="Démonstration en magasin", level="safe",
         what="Mode vitrine pour PC exposés en boutique.", risk="Aucun."),
    dict(id="Fax", name="Télécopie (fax)", level="safe", what="Envoi/réception de fax.", risk="Aucun, sauf si tu as encore un modem fax."),
    dict(id="RemoteRegistry", name="Registre à distance", level="safe",
         what="Permet de modifier le registre depuis un autre ordinateur du réseau.",
         risk="Aucun, et c'est même plus sûr désactivé."),
    dict(id="WpcMonSvc", name="Contrôle parental", level="maybe",
         what="Applique les règles Microsoft Family.", risk="À garder si tu utilises le contrôle parental Microsoft."),
    dict(id="PhoneSvc", name="Service téléphonique", level="safe", what="Liaison téléphonie (rarement utilisée).", risk="Aucun."),
    dict(id="lfsvc", name="Géolocalisation", level="maybe",
         what="Donne ta position aux applications.", risk="Météo, cartes… ne verront plus ta position."),
    dict(id="wisvc", name="Programme Windows Insider", level="safe", what="Versions de test de Windows.",
         risk="Aucun, sauf si tu es inscrit au programme Insider."),
    dict(id="bthserv", name="Prise en charge Bluetooth", level="maybe",
         what="Gère les appareils Bluetooth.", risk="Plus de souris/casque/manette Bluetooth tant qu'il est désactivé."),
    dict(id="Spooler", name="Spouleur d'impression", level="maybe",
         what="Gère les imprimantes.", risk="Plus d'impression tant qu'il est désactivé."),
    dict(id="XblGameSave", name="Xbox — sauvegardes de jeux cloud", level="maybe",
         what="Synchronise les sauvegardes des jeux Xbox / Microsoft Store.",
         risk="⚠ À garder si tu joues à des jeux Xbox ou du Microsoft Store."),
]
BY_ID = {s["id"]: s for s in SERVICES}
STATE = data_dir() / "services_state.json"
MODE = {"auto": "auto", "manual": "demand", "disabled": "disabled"}


def _state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_states():
    """{id: {"mode": auto|delayed-auto|demand|disabled, "state": Running|Stopped}} ou {} hors Windows / service absent."""
    if not IS_WINDOWS:
        return {}
    names = ",".join(f"'{s['id']}'" for s in SERVICES)
    _, out = run_ps(f"@(Get-CimInstance Win32_Service | ? {{ $_.Name -in @({names}) }} | "
                    "select Name,StartMode,DelayedAutoStart,State) | ConvertTo-Json -Compress", 30)
    try:
        data = json.loads(out[out.index("["):out.rindex("]") + 1]) if "[" in out else [json.loads(out[out.index("{"):])]
    except Exception:
        return {}
    res = {}
    for d in data:
        m = MODE.get(str(d.get("StartMode", "")).lower(), "demand")
        if m == "auto" and d.get("DelayedAutoStart"):
            m = "delayed-auto"
        res[d["Name"]] = {"mode": m, "state": d.get("State", "")}
    return res


def _sc(name, mode):
    """`sc.exe config`. Renvoie (ok, code, sortie).

    Le CODE de retour du processus est la source fiable : sc.exe y recopie le
    numero d'erreur Windows (5, 1058, 1060...). La sortie ecrite ne sert que de
    repli, et pour cause : elle est traduite. Sur un Windows francais l'echec
    s'ecrit « [SC] OpenService Échec(s) 1060 » — chercher « FAILED » ne rapporte
    donc rien hors d'un Windows anglais, et un blocage d'entreprise serait passe
    pour un mystere."""
    code, sortie = run_cmd(["sc.exe", "config", name, "start=", mode], 20)
    return code == 0, code, sortie


def _motif(nom_id, action, code=None, sortie=""):
    from Shared.Utils import refus
    return refus.motif_refus(f"{action} « {BY_ID[nom_id]['name']} »", code=code, sortie=sortie)


def _sc_start(name):
    run_cmd(["sc.exe", "start", name], 20)


def disable(ids, states, journal):
    """Désactive (arrête + mode « disabled »). Renvoie (ok, échecs)."""
    if not is_admin():
        return [], [(i, _motif(i, T("désactiver"))) for i in ids]
    st, done, failed, prev = _state(), [], [], []
    for i in ids:
        cur = states.get(i, {}).get("mode", "demand")
        ok, code, sortie = _sc(i, "disabled")
        if ok:
            run_cmd(["sc.exe", "stop", i], 20)
            st.setdefault(i, cur if cur != "disabled" else "demand")
            prev.append({"id": i, "mode": cur})
            done.append(i)
        else:
            failed.append((i, _motif(i, T("désactiver"), code, sortie)))
    STATE.write_text(json.dumps(st), encoding="utf-8")
    if done:
        journal.add("services", T("{v0} service(s) Windows désactivé(s)").format(v0=len(done)),
                    ", ".join(BY_ID[i]["name"] for i in done),
                    {"items": prev})
    return done, failed


def restore(ids, journal):
    if not is_admin():
        return [], [(i, _motif(i, "remettre comme avant")) for i in ids]
    st, done, failed, items = _state(), [], [], []
    for i in ids:
        mode = st.get(i, "demand")
        ok, code, sortie = _sc(i, mode)
        if ok:
            if mode != "disabled":
                _sc_start(i)
            st.pop(i, None)
            items.append({"id": i, "mode": "disabled"})
            done.append(i)
        else:
            failed.append((i, _motif(i, "remettre comme avant", code, sortie)))
    STATE.write_text(json.dumps(st), encoding="utf-8")
    if done:
        journal.add("services", T("{v0} service(s) Windows remis comme avant").format(v0=len(done)),
                    ", ".join(BY_ID[i]["name"] for i in done),
                    {"items": items})
    return done, failed


@register_undo("services")
def _undo(d):
    n = 0
    for it in d["items"]:
        if _sc(it["id"], it["mode"])[0]:
            if it["mode"] != "disabled":
                _sc_start(it["id"])
            n += 1
    return T("{v0} service(s) remis à leur mode précédent (droits administrateur requis).").format(v0=n)
