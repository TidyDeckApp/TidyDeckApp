"""Lecture du matériel (Windows : CIM/PowerShell, lecture seule). Hors Windows : données de démo.

Le relevé complet coute ~4,5 s (PowerShell + WMI). Il est donc cache **sur disque** :
le materiel ne change pas d'un jour au lendemain, et un lancement sur deux ne doit
pas faire attendre l'utilisateur. Le rechargement se fait en une seule fois, sous
verrou, pour que deux appelants ne lancent pas deux relevés en parallele."""
import json
import os
import platform
import re
import shutil
import threading
import time
from Shared.Utils.common import IS_WINDOWS, human_size, run_ps, data_dir
from Shared.Utils import nvidia
from Shared.Utils import lang as _lang

APPAREILS_EN = (("Périphérique High Definition Audio", "High Definition Audio Device"),
                ("Périphérique audio USB", "USB Audio Device"),
                ("Périphérique audio haute définition", "High Definition Audio Device"),
                ("Haut-parleurs", "Speakers"),
                ("Casque", "Headphone"),
                ("Édition", "Edition"))

EDITIONS_EN = (("Famille N", "Home N"), ("Famille", "Home"), ("Professionnelle", "Pro"),
               ("Éducation", "Education"), ("Entreprises", "Enterprise"),
               ("Intégrée à une seule langue", "Single Language"))


def nom_systeme(n):
    """Édition Windows fournie par l'OS (« Windows 11 Famille ») : casse et
    nom anglais quand l'interface est en anglais."""
    if _lang.get_lang() == "en":
        for fr, en in EDITIONS_EN:
            if fr in n:
                return n.replace(fr, en)
    return n


def nom_appareil(n):
    """Noms d'appareils fournis par Windows en français : les dire en anglais
    quand l'interface est en anglais (le nom brut vient de l'OS, pas de TidyDeck)."""
    if _lang.get_lang() == "en":
        for fr, en in APPAREILS_EN:
            if fr.lower() in n.lower():
                n = re.sub(re.escape(fr), en, n, flags=re.IGNORECASE)
    return n

from Shared.Utils.lang import T

CACHE_FICHIER = "hardware.json"
CACHE_DUREE = 12 * 3600          # 12 h : au-dela on relit, sinon on garde
_verrou = threading.Lock()

PS = r'''
$ErrorActionPreference='SilentlyContinue'
$os=Get-CimInstance Win32_OperatingSystem
$cv=Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$vram=Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11cd-bfc1-08002be10318}' | % { $p=Get-ItemProperty $_.PSPath; $q=$p.'HardwareInformation.qwMemorySize'; if($q -is [byte[]]){ $q=[BitConverter]::ToUInt64($q,0) }; if($q){ [pscustomobject]@{Name=$p.DriverDesc;VRAM=[uint64]$q} } }
[pscustomobject]@{
 Os=[pscustomobject]@{Caption=$os.Caption;Build=$cv.CurrentBuildNumber;UBR=$cv.UBR;Display=$cv.DisplayVersion}
 Board=@(Get-CimInstance Win32_BaseBoard | select Manufacturer,Product)
 Cpu=@(Get-CimInstance Win32_Processor | select Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed)
 Ram=@(Get-CimInstance Win32_PhysicalMemory | select Capacity,Speed,ConfiguredClockSpeed,SMBIOSMemoryType)
 Gpu=@(Get-CimInstance Win32_VideoController | select Name,DriverVersion,@{n='DriverDate';e={if($_.DriverDate){$_.DriverDate.ToString('yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)}}},AdapterRAM)
 Vram=@($vram)
 Sound=@(Get-CimInstance Win32_SoundDevice | select Name)
 Pnp=@(Get-PnpDevice -Class MEDIA -PresentOnly | select FriendlyName)
 Endpoints=@(Get-PnpDevice -Class AudioEndpoint -PresentOnly | select FriendlyName)
 Disks=@(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | select DeviceID,Size,FreeSpace,VolumeName)
 Phys=@(Get-PhysicalDisk | select DeviceId,FriendlyName,MediaType,BusType,HealthStatus,Size)
 DiskMap=@(Get-Partition -ErrorAction SilentlyContinue | ? {$_.DriveLetter} | % { [pscustomobject]@{Drive="$($_.DriveLetter):"; Num="$($_.DiskNumber)"} })
} | ConvertTo-Json -Depth 5 -Compress
'''
RAM_TYPES = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5", 35: "LPDDR5"}

_AUDIO_PS = r"""
try {
  $id = [Windows.Media.Devices.MediaDevice,Windows.Media.Devices,ContentType=WindowsRuntime]::GetDefaultAudioRenderId([Windows.Media.Devices.AudioDeviceRole]::Default)
  $g = [regex]::Match($id,'\{0\.0\.0\.00000000\}\.\{[0-9a-fA-F-]+\}').Value
  if ($g) { 'DEFAULT=' + (Get-PnpDevice -InstanceId ('SWD\MMDEVAPI\' + $g) -ErrorAction Stop).FriendlyName }
} catch {}
try {
  Get-PnpDevice -Class AudioEndpoint -Status OK -ErrorAction Stop |
    Where-Object { $_.InstanceId -like '*{0.0.0.*' } |
    ForEach-Object { 'OUT=' + $_.FriendlyName }
} catch {}
"""


def audio_summary():
    """Sortie audio par défaut + d'autres sorties actives. '' si rien de lisible.

    Deux niveaux de repli : le type WinRT (le seul qui désigne vraiment le
    « par défaut »), puis la simple liste des points de terminaison de sortie.
    Casques USB, DAC et Bluetooth sont des AudioEndpoint : Win32_SoundDevice ne
    les voit pas, d'ou ce choix. Aucun code compilé, aucune dépendance : des
    cmdlets deja presentes dans Windows PowerShell 5.1."""
    _, out = run_ps(_AUDIO_PS, 25)
    default, outs = "", []
    for line in (out or "").splitlines():
        line = line.strip()
        if line.startswith("DEFAULT="):
            default = line[8:].strip()
        elif line.startswith("OUT="):
            name = line[4:].strip()
            if name and name not in outs:
                outs.append(name)
    if default:
        autres = [n for n in outs if n != default]
        return default + (f"  (+{len(autres)} autre(s))" if autres else "")
    return ", ".join(outs)


HEALTH = {"healthy": "✔ Bon état", "warning": "⚠ À surveiller", "unhealthy": "⚠ Défaillant — sauvegarde tes fichiers"}
_cache = {}


def _list(x):
    return [] if x is None else (x if isinstance(x, list) else [x])


def _demo():
    du = shutil.disk_usage("/")
    return {"demo": True, "Audio": T("Haut-parleurs (démo)"), "Os": {"Caption": f"{platform.system()} {platform.release()} (démo)", "Build": "", "UBR": "", "Display": ""},
            "Board": [{"Manufacturer": "—", "Product": T("non lu (démo)")}],
            "Cpu": [{"Name": platform.processor() or T("Processeur (démo)"), "NumberOfCores": 8, "NumberOfLogicalProcessors": 16, "MaxClockSpeed": 3800}],
            "Ram": [{"Capacity": 8 << 30, "Speed": 3200, "ConfiguredClockSpeed": 3200, "SMBIOSMemoryType": 26}] * 2,
            "Gpu": [{"Name": T("Carte graphique (démo)"), "DriverVersion": "31.0.0.0", "DriverDate": "2024-03-12", "AdapterRAM": 0}],
            "Vram": [{"Name": T("Carte graphique (démo)"), "VRAM": 8 << 30}], "Sound": [{"Name": T("Audio (démo)")}], "Pnp": [{"FriendlyName": T("USB Audio Device (démo)")}], "Endpoints": [{"FriendlyName": T("Haut-parleurs (démo)")}],
            "Disks": [{"DeviceID": "C:", "Size": du.total, "FreeSpace": du.free, "VolumeName": ""}],
            "Phys": [{"FriendlyName": T("SSD (démo)"), "MediaType": "SSD", "HealthStatus": "Healthy", "Size": du.total}]}


def _fichier_cache():
    return data_dir() / CACHE_FICHIER


def _lis_disque():
    """Relevé gardé en mémoire durable ; None s'il est absent, abîmé ou trop vieux."""
    try:
        with open(_fichier_cache(), encoding="utf-8") as fh:
            o = json.load(fh)
        if time.time() - float(o.get("ts", 0)) > CACHE_DUREE:
            return None
        d = o.get("d")
        if not isinstance(d, dict) or d.get("demo"):
            return None
        return d
    except Exception:  # absent, illisible, coup de jus en plein écriture…
        return None


def _ecris_disque(d):
    try:
        p = _fichier_cache()
        tmp = p.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"ts": time.time(), "d": d}, fh, ensure_ascii=False)
        tmp.replace(p)            # atomic : pas de fichier à moitié écrit
    except Exception:
        pass                     # un cache raté ne doit jamais casser l'affichage


def est_chaud():
    """Le relevé est-il déjà disponible (mémoire ou disque) ?"""
    if _cache and time.time() - _cache.get("ts", 0) < CACHE_DUREE:
        return True
    return _lis_disque() is not None


def load(force=False):
    with _verrou:
        # Un relevé récent évite 4,5 s d'attente a l'utilisateur.
        if not force:
            if _cache and time.time() - _cache.get("ts", 0) < CACHE_DUREE:
                return _cache["d"]
            disque = _lis_disque()
            if disque:
                _cache["d"], _cache["ts"] = disque, time.time()
                return disque
        data = None
        if IS_WINDOWS:
            _, out = run_ps(PS, 60)
            try:
                data = json.loads(out[out.index("{"):])
            except Exception:
                data = None
        data = data or _demo()
        if IS_WINDOWS and not data.get("demo"):
            data["Nvidia"] = nvidia.query("name,memory.total")
            if not data.get("Audio"):
                data["Audio"] = audio_summary()
            _ecris_disque(data)
        _cache["d"], _cache["ts"] = data, time.time()
        return data


def live_disk(dev, fallback=(0, 0)):
    """Espace réellement libre MAINTENANT sur ce lecteur.

    Le relevé matériel est garde 12 h sur disque : ses chiffres `FreeSpace` sont
    donc peims. Rien ne sert d'attendre une nouvelle lecture PowerShell, `shutil`
    donne la valeur reelle en une milliseconde."""
    try:
        cible = dev if os.sep == "/" else f"{dev}\\"
        u = shutil.disk_usage(cible)
        return int(u.free), int(u.total)
    except OSError:
        return fallback


def gb_text(b):
    from Shared.Utils.lang import get_lang
    en = get_lang() == "en"
    v = b / (1 << 30)
    if en:
        return f"{round(v)} GB" if abs(v - round(v)) < 0.15 else f"{v:.1f} GB"
    return f"{round(v)} Go" if abs(v - round(v)) < 0.15 else f"{v:.1f} Go".replace(".", ",")


def _date(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else "date inconnue"


def _clean_board_name(manufacturer, product):
    """Simplifie le nom : 'Micro-Star International Co., Ltd. MPG B550M' → 'MSI MPG B550M'"""
    s = f"{manufacturer or ''} {product or ''}".strip()
    s = re.sub(r'\bASUSTeK\b', 'ASUS', s, flags=re.I)
    s = re.sub(r'\bMicro[- ]?Star\b', 'MSI', s, flags=re.I)
    s = re.sub(r'\b(International|Incorporation|Computer(s)?|Technolog(y|ies)|Co\.?|Ltd\.?|Inc\.?|Corp\.?|Gmbh|Kg|S\.?A\.?)\b[\s,\.]*',
               '', s, flags=re.I)
    s = re.sub(r'^[\s,\.]+', '', s)
    s = re.sub(r'[\s,\.]+$', '', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s if s else (product or T("non détectée"))


def disk_type_label(bus, media):
    bus = (bus or "").upper()
    media = (media or "").upper()
    if bus == "USB":
        if "SSD HDD" in media or media == "MIXED":
            return "Hybride externe (USB)"
        return "SSD externe (USB)" if media == "SSD" else "HDD externe (USB)" if media == "HDD" else "Disque externe (USB)"
    if "SSD HDD" in media or media == "MIXED":
        return "Hybride (SSHD)"
    if media == "SSD":
        return "SSD NVMe" if bus == "NVME" else "SSD (SATA)" if bus == "SATA" else "SSD"
    if media == "HDD":
        return "Disque dur (HDD)"
    return ""


def describe(d, advanced=False):
    """Liste de composants : {icon,label,summary,details[]}, + stockage."""
    out = []
    o = d.get("Os") or {}
    name = nom_systeme((o.get("Caption") or "Windows").replace("Microsoft ", "").strip())
    det = []
    if o.get("Build"):
        det.append(T("Version {v0} — build {v1}").format(v0=o.get('Display') or '?', v1=o['Build']) + (f".{o['UBR']}" if o.get("UBR") != "" else ""))
    out.append(dict(icon="🖥️", label=T("Système"), summary=name, details=det))
    b = (_list(d.get("Board")) or [{}])[0]
    board_summary = _clean_board_name(b.get('Manufacturer', ''), b.get('Product', '')) if not advanced else f"{b.get('Manufacturer', '')} {b.get('Product', T('non détectée'))}".strip()
    out.append(dict(icon="🧩", label=T("Carte mère"), summary=board_summary, details=[]))
    c = (_list(d.get("Cpu")) or [{}])[0]
    arch = {"AMD64": "64 bits (x64)", "ARM64": "64 bits (ARM)"}.get(platform.machine(), platform.machine())
    ghz = (c.get("MaxClockSpeed") or 0) / 1000
    out.append(dict(icon="🎛️", label=T("Processeur"), summary=(c.get("Name") or T("non détecté")).strip(),
                    details=[T("{v0} cœurs / {v1} threads").format(v0=c.get('NumberOfCores', '?'), v1=c.get('NumberOfLogicalProcessors', '?')),
                             T("Fréquence de base : {v0:.1f} GHz (le boost maximal n'est pas lisible de façon fiable)").format(v0=ghz).replace(".", ",") if ghz else T("Fréquence inconnue"),
                             T("Architecture : {v0}").format(v0=arch)]))
    sticks = _list(d.get("Ram"))
    total = sum(int(s.get("Capacity") or 0) for s in sticks)
    mhz = max([int(s.get("ConfiguredClockSpeed") or s.get("Speed") or 0) for s in sticks] or [0])
    typ = RAM_TYPES.get((sticks[0].get("SMBIOSMemoryType") if sticks else 0), "")
    out.append(dict(icon="📊", label=T("Mémoire (RAM)"), summary=gb_text(total) if total else T("non détectée"),
    details=[(T("{v0} barrette {v1}") if len(sticks) == 1 else T("{v0} barrettes {v1}")).format(v0=len(sticks), v1=typ).strip(), T("Fréquence : {v0} MHz").format(v0=mhz) if mhz else T("Fréquence inconnue")]))
    vr = {v.get("Name"): v.get("VRAM") for v in _list(d.get("Vram"))}
    nv = d.get("Nvidia") or []
    gpus = [g for g in _list(d.get("Gpu")) if not re.search(r"virtual|remote|basic", g.get("Name") or "", re.I)]
    det = []
    for g in gpus:
        name = g.get("Name") or "?"
        v, note = 0, ""
        if "nvidia" in name.lower() and nv:                      # API NVIDIA : valeur exacte
            m = next((x for x in nv if x[0].lower() in name.lower() or name.lower() in x[0].lower()), nv[0])
            try:
                v = int(float(m[1])) * (1 << 20)
            except (ValueError, IndexError):
                v = 0
        if not v:
            v = vr.get(name) or 0
        if not v:
            ar = int(g.get("AdapterRAM") or 0)
            if 0 < ar < 4_000_000_000:
                v, note = ar, T(" (valeur approximative)")
        vtxt = (gb_text(v) + T(" de VRAM") + note) if v else T("VRAM non lisible sur ce PC")
        det.append(T("{v0} : {v1} — pilote {v2} du {v3}").format(v0=name, v1=vtxt, v2=g.get('DriverVersion', '?'), v3=_date(g.get('DriverDate'))))
    out.append(dict(icon="🎮", label=T("Carte graphique"), summary=" + ".join(g.get("Name", "?") for g in gpus) or T("non détectée"), details=det))
    son = nom_appareil((d.get("Audio") or "").strip())
    if son:
        out.append(dict(icon="🎧", label=T("Sortie audio par défaut"), summary=son, details=[]))
    names = []
    for src, key in ((d.get("Sound"), "Name"), (d.get("Pnp"), "FriendlyName")):
        for x in _list(src):
            n = nom_appareil((x.get(key) or "").strip())
            if n and n.lower() not in [m.lower() for m in names]:
                names.append(n)
    eps = [nom_appareil(e.get("FriendlyName")) for e in _list(d.get("Endpoints")) if e.get("FriendlyName")]
    det = names[3:] + ([T("Sorties / entrées : {v0}").format(v0=', '.join(eps))] if eps else [])
    out.append(dict(icon="🔊", label=T("Cartes son (internes et USB)"), summary=" + ".join(names[:3]) or T("non détectée"), details=det))
    phys_list = _list(d.get("Phys"))
    by_num = {str(p.get("DeviceId")): p for p in phys_list}
    num_for = {m.get("Drive"): m.get("Num") for m in _list(d.get("DiskMap"))}
    disks = []
    for x in _list(d.get("Disks")):
        dev = x.get("DeviceID")
        p = by_num.get(num_for.get(dev) or "", {})
        disks.append(dict(dev=dev, free=int(x.get("FreeSpace") or 0), total=int(x.get("Size") or 0),
                         type=disk_type_label(p.get("BusType"), p.get("MediaType"))))
    phys = []
    for p in phys_list:
        h = T(HEALTH.get(str(p.get("HealthStatus", "")).lower(), T("ℹ État inconnu")))
        t = disk_type_label(p.get("BusType"), p.get("MediaType")) or str(p.get("MediaType", "?"))
        phys.append(f"{p.get('FriendlyName', '?')} ({t}, {human_size(int(p.get('Size') or 0)).replace(',0', '')}) — {h}")
    return out, disks, phys
