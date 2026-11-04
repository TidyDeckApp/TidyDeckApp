import os
import platform
import shutil
from Shared.Utils.common import IS_WINDOWS, human_size
from Shared.Utils import winapi
from Shared.Utils.lang import T


def _drive():
    return (os.environ.get("SystemDrive", "C:") + "\\") if IS_WINDOWS else "/"


def simple_info():
    total, free = winapi.memory_status()
    du = shutil.disk_usage(_drive())
    rows = [(T("Système"), f"{platform.system()} {platform.release()}"),
            (T("Disque système libre"), f"{human_size(du.free)} sur {human_size(du.total)}")]
    if total:
        rows.append((T("Mémoire (RAM)"), f"{human_size(total)} (libre : {human_size(free)})"))
    return rows


def advanced_info():
    rows = simple_info()
    rows += [(T("Version détaillée"), platform.version()), ("Architecture", platform.machine()),
             ("Processeur", platform.processor() or "inconnu"), ("Nom du PC", platform.node()),
             ("Python", platform.python_version())]
    return rows
