"""Températures et fréquence turbo — sans pilote noyau.

Pourquoi pas comme MSI Center / HWiNFO / CPU-Z ? Ces outils lisent les registres internes du processeur (MSR)
et les puces de capteurs grâce à un PILOTE NOYAU qu'ils installent. TidyDeck s'interdit d'en embarquer un
(risque de sécurité, compatibilité anti-triche). À la place :
  1. si LibreHardwareMonitor (gratuit, open source) est lancé, on lit ses capteurs via WMI ;
  2. sinon zones thermiques ACPI exposées par Windows (pas toujours le cœur du processeur) ;
  3. turbo : on le MESURE (charge brève du processeur + compteur Windows de fréquence)."""
import json
import os
import subprocess
import sys
from Shared.Utils.common import IS_WINDOWS, NO_WINDOW, run_ps
from Shared.Utils.lang import T

LHM_PS = r'''
$ErrorActionPreference='SilentlyContinue'; $found=$null
foreach($n in 'root/LibreHardwareMonitor','root/OpenHardwareMonitor'){
  $s = Get-CimInstance -Namespace $n -ClassName Sensor
  if($s){ $found=$s; break } }
if($found){ @($found | ? { $_.Identifier -match 'cpu' -and $_.SensorType -in 'Temperature','Clock' } | select Name,SensorType,Value) | ConvertTo-Json -Compress }
'''
ZONE_PS = r'''
$ErrorActionPreference='SilentlyContinue'
@(Get-CimInstance Win32_PerfFormattedData_Counters_ThermalZoneInformation | select Name,Temperature) | ConvertTo-Json -Compress
'''


def _json(out):
    try:
        i = min(x for x in (out.find("["), out.find("{")) if x >= 0)
        d = json.loads(out[i:])
        return d if isinstance(d, list) else [d]
    except Exception:
        return []


def lhm():
    """{"temp": (°C, nom), "clock_max": MHz} si LibreHardwareMonitor tourne, sinon None."""
    if not IS_WINDOWS:
        return None
    rows = _json(run_ps(LHM_PS, 25)[1])
    if not rows:
        return None
    temps = [(r["Name"], float(r["Value"])) for r in rows if r.get("SensorType") == "Temperature" and r.get("Value") is not None]
    clocks = [float(r["Value"]) for r in rows if r.get("SensorType") == "Clock" and "Core" in r.get("Name", "") and r.get("Value")]
    temp = None
    for pref in ("CPU Package", "Core (Tctl/Tdie)", "CPU CCD", "CPU Core"):
        hit = next(((n, v) for n, v in temps if n.startswith(pref)), None)
        if hit:
            temp = (hit[1], hit[0])
            break
    if not temp and temps:
        temp = max(((v, n) for n, v in temps))
    return {"temp": temp, "clock_max": max(clocks) if clocks else None}


def zone_temp():
    if not IS_WINDOWS:
        return None
    vals = []
    for r in _json(run_ps(ZONE_PS, 20)[1]):
        try:
            c = float(r.get("Temperature")) - 273.15
            if 15 < c < 110:
                vals.append(c)
        except (TypeError, ValueError):
            pass
    return round(max(vals)) if vals else None


def cpu_temperature():
    """(valeur °C, source lisible) ou None."""
    d = lhm()
    if d and d.get("temp"):
        return round(d["temp"][0]), f"LibreHardwareMonitor ({d['temp'][1]})"
    z = zone_temp()
    if z:
        return z, T("zone thermique ACPI de Windows (selon le PC : carte mère/boîtier, pas toujours le cœur)")
    return None


def _sample(seconds):
    script = (f"$m=0; for($i=0;$i -lt {seconds};$i++){{ Start-Sleep -Milliseconds 900; "
              "$v=(Get-CimInstance Win32_PerfFormattedData_Counters_ProcessorInformation | ? { $_.Name -notmatch '_Total' } | "
              "measure ProcessorFrequency -Maximum).Maximum; if($v -gt $m){$m=$v} }; $m")
    try:
        return int(float(run_ps(script, seconds * 3 + 20)[1].strip().splitlines()[-1]))
    except Exception:
        return None


def _burn(n, seconds):
    ps = ("$t=[Diagnostics.Stopwatch]::StartNew(); "
          f"while($t.Elapsed.TotalSeconds -lt {seconds + 6}){{}}")
    kw = {"creationflags": NO_WINDOW} if IS_WINDOWS else {}
    return [subprocess.Popen(["powershell", "-NoProfile", "-Command", ps],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
            for _ in range(n)]


def measure_turbo(seconds=4):
    """Fréquence MAX observée (MHz) : 1 cœur chargé, puis tous les cœurs. Environ 10 s au total."""
    if not IS_WINDOWS:
        return None
    res = {}
    for label, n in (("single", 1), ("all", os.cpu_count() or 4)):
        procs = _burn(n, seconds)
        try:
            res[label] = _sample(seconds)
        finally:
            for p in procs:
                try:
                    p.kill()
                except Exception:
                    pass
    return res
