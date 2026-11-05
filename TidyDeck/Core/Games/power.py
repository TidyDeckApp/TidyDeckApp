"""Plan d'alimentation « Performances maximales » (commande officielle powercfg -duplicatescheme)."""
import json
import re
from Shared.Utils.common import IS_WINDOWS, data_dir, run_cmd
from Services.Logger.journal import register_undo
from Shared.Utils.lang import T

ULTIMATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"
GUID = r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
STATE = data_dir() / "power_state.json"


def list_schemes():
    _, out = run_cmd(["powercfg", "/list"], 15)
    return [(m.group(1).lower(), m.group(2), bool(m.group(3)))
            for m in re.finditer(rf"({GUID})\s+\(([^)]*)\)(\s*\*)?", out)]


def active():
    _, out = run_cmd(["powercfg", "/getactivescheme"], 10)
    m = re.search(GUID, out or "")
    return m.group(0).lower() if m else None


def _tracked():
    try:
        return json.loads(STATE.read_text(encoding="utf-8")).get("ultimate")
    except Exception:
        return None


def find_ultimate():
    schemes = list_schemes()
    ids = {g for g, _, _ in schemes}
    t = _tracked()
    if t and t in ids:
        return t
    for g, name, _ in schemes:
        if re.search(r"ultimate|ultime|optimal|maxim", name, re.I):
            return g
    return None


def enable_ultimate(journal):
    """(ok, message). Crée le plan s'il n'existe pas, puis l'active. Annulable."""
    if not IS_WINDOWS:
        return False, T("Disponible uniquement sous Windows.")
    prev, sch, created = active(), find_ultimate(), None
    if not sch:
        rc, out = run_cmd(["powercfg", "-duplicatescheme", ULTIMATE], 20)
        m = re.search(GUID, out or "")
        if rc != 0 or not m:
            return False, T("Windows a refusé de créer le plan (certains PC, notamment portables "
                            "à « veille moderne », ne le proposent pas). Réponse : {v0}"
                            ).format(v0=(out or '').strip()[:160])
        sch = created = m.group(0).lower()
    run_cmd(["powercfg", "/setactive", sch], 15)
    if active() != sch:
        return False, T("Le plan a été créé mais Windows ne l'a pas activé.")
    # Le GUID est memorise meme si le plan existait deja : la prochaine fois, la
    # recherche ne dependra plus du nom affiche par Windows.
    STATE.write_text(json.dumps({"ultimate": sch}), encoding="utf-8")
    journal.add("powerplan", T("Plan d'alimentation « Performances maximales » activé"),
                T("Plan {v0} activé ; précédent : {v1}").format(v0=sch, v1=prev),
                {"prev": prev, "created": created})
    return True, T("Plan « Performances maximales » activé.")


@register_undo("powerplan")
def _undo(d):
    if d.get("prev"):
        run_cmd(["powercfg", "/setactive", d["prev"]], 15)
    if d.get("created"):
        run_cmd(["powercfg", "/delete", d["created"]], 15)
        try:
            STATE.unlink()
        except OSError:
            pass
    return T("Ancien plan d'alimentation rétabli.")
