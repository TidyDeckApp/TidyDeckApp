"""Lecture NVIDIA via nvidia-smi (fourni avec le pilote) : VRAM exacte, température."""
from Shared.Utils.common import run_cmd

CANDIDATES = ["nvidia-smi", r"C:\Windows\System32\nvidia-smi.exe",
              r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"]


def query(fields):
    for exe in CANDIDATES:
        rc, out = run_cmd([exe, f"--query-gpu={fields}", "--format=csv,noheader,nounits"], 8)
        if rc == 0 and out.strip():
            return [[c.strip() for c in line.split(",")] for line in out.strip().splitlines()]
    return []
