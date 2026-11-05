"""Lecture/écriture du registre — uniquement les valeurs que l'on cite à l'écran."""
try:
    import winreg
except ImportError:  # pas sous Windows
    winreg = None

HIVE_LONG = {"HKCU": "HKEY_CURRENT_USER", "HKLM": "HKEY_LOCAL_MACHINE"}


def _hive(name):
    return {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}[name]


def full_path(hive, key):
    return f"{HIVE_LONG[hive]}\\{key}"


def read(hive, key, name):
    if not winreg:
        return None
    try:
        with winreg.OpenKey(_hive(hive), key, 0, winreg.KEY_READ) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def write(hive, key, name, value, kind=None):
    if not winreg:
        raise OSError("Registre indisponible (Windows uniquement)")
    kind = kind if kind is not None else winreg.REG_DWORD
    with winreg.CreateKeyEx(_hive(hive), key, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, kind, value)


def delete(hive, key, name):
    if not winreg:
        return
    try:
        with winreg.OpenKey(_hive(hive), key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
    except OSError:
        pass


def list_values(hive, key):
    out = []
    if not winreg:
        return out
    try:
        with winreg.OpenKey(_hive(hive), key, 0, winreg.KEY_READ) as k:
            i = 0
            while True:
                try:
                    n, v, _ = winreg.EnumValue(k, i)
                    out.append((n, v))
                    i += 1
                except OSError:
                    break
    except OSError:
        pass
    return out


def list_subkeys(hive, key):
    out = []
    if not winreg:
        return out
    try:
        with winreg.OpenKey(_hive(hive), key, 0, winreg.KEY_READ) as k:
            i = 0
            while True:
                try:
                    out.append(winreg.EnumKey(k, i))
                    i += 1
                except OSError:
                    break
    except OSError:
        pass
    return out
