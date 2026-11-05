"""Indicateur de chaleur minimaliste. Honnête : sans capteur lisible, on le dit."""
from Core.SystemInfo import sensors
from Shared.Utils import nvidia
from Shared.Utils.lang import T


def gpu_temp():
    r = nvidia.query("temperature.gpu")
    try:
        return int(r[0][0]) if r else None
    except (ValueError, IndexError):
        return None


def status():
    """None si aucun capteur lisible, sinon (texte, niveau, détail, astuce)."""
    cpu = sensors.cpu_temperature()
    gpu = gpu_temp()
    known = ([cpu[0]] if cpu else []) + ([gpu] if gpu else [])
    hint = ""
    if not cpu:
        hint = (T("Température du processeur : Windows ne la partage pas seul. Lance LibreHardwareMonitor (gratuit, open source) "
                "et TidyDeck la lira automatiquement — sans installer de pilote supplémentaire dans TidyDeck."))
    if not known:
        return None if not hint else (T("Aucun capteur lisible"), "info", "", hint)
    worst = max(known)
    detail = " · ".join(([T("processeur {v0} °C — source : {v1}").format(v0=cpu[0], v1=cpu[1])] if cpu else []) + ([T("carte graphique {v0} °C").format(v0=gpu)] if gpu else []))
    if worst < 75:
        return T("Température idéale"), "ok", detail, hint
    if worst < 85:
        return T("Ça chauffe un peu — rien d'inquiétant"), "info", detail, hint
    return T("Attention, le PC souffle fort : vérifie la ventilation et la poussière"), "warn", detail, hint
