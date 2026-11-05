"""Modèles de données partagés."""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class CleanItem:
    id: str
    name: str
    what: str                      # ce que c'est
    why_safe: str                  # pourquoi on peut le retirer
    paths: List[str]               # chemins réels (jokers * autorisés)
    risk: str = "Aucun"
    process: Optional[str] = None  # programme qui doit être fermé (ex. chrome.exe)
    simple: bool = True            # visible en mode simple
    preselect: bool = True         # coché par défaut
    needs_admin: bool = False
    special: Optional[str] = None  # "recycle_bin"
    icon: str = "🧹"


@dataclass
class Check:
    name: str
    status: str                    # ok | warn | info
    detail: str
    advice: str = ""               # le « que faire »
    # Emplacement verifiable : la ligne reste muette (bouton grise) si aucun n'est fourni.
    path: str = ""                 # dossier/fichier -> explorateur
    settings: str = ""             # "startupapps" | "ms-settings:..." | "control:Microsoft.PowerOptions"
    shell: str = ""                # chemin namespace Windows (Corbeille ::{...})
    reg: tuple = ()                # (hive, cle) -> regedit, consultation seule
    location: str = ""             # libelle humain : « Ouvrir : <libelle> »


@dataclass
class RegValue:
    key: str
    name: str
    value: int


@dataclass
class Tweak:
    id: str
    name: str
    group: str
    what: str
    benefit: str
    risk: str
    values: List[RegValue]
    hive: str = "HKCU"
