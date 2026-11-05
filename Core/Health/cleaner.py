"""Analyse -> aperçu -> nettoyage (par mise en quarantaine, donc annulable)."""
import glob
import os
import time
from dataclasses import dataclass, field
from Shared.Utils.common import entry_size, is_admin, is_process_running
from Shared.Utils import quarantine, winapi
from Shared.Utils.lang import T


@dataclass
class ScanResult:
    item: object
    entries: list = field(default_factory=list)
    size: int = 0
    count: int = 0
    blocked: str = None
    found: list = field(default_factory=list)   # (chemin, nb trouvés, octets)


def scan_item(item) -> ScanResult:
    r = ScanResult(item)
    if item.special == "recycle_bin":
        r.size, r.count = winapi.recycle_bin_info()
        r.found.append((T("Corbeille Windows (dossier système $Recycle.Bin de chaque lecteur)"),
                        1 if r.count else 0, r.size))
    else:
        for pattern in item.paths:
            nm = psize = 0
            for m in glob.glob(pattern):
                nm += 1
                targets = [m]
                if os.path.isdir(m) and not os.path.islink(m):
                    try:
                        targets = [e.path for e in os.scandir(m)]
                    except OSError:
                        targets = []
                for t in targets:
                    s, c = entry_size(t)
                    r.entries.append(t)
                    psize += s
                    r.count += c
            r.found.append((pattern, nm, psize))
            r.size += psize
    if item.process and is_process_running(item.process):
        r.blocked = f"Programme ouvert ({item.process}) — ferme-le pour le nettoyer."
    elif item.needs_admin and not is_admin():
        r.blocked = T("Nécessite de lancer TidyDeck en administrateur.")
    return r


def scan_all(items):
    return {i.id: scan_item(i) for i in items}


def clean(results, journal, days_kept=7):
    run_id = time.strftime("%Y%m%d-%H%M%S")
    pairs, moved, skipped, irreversible = [], 0, 0, 0
    n = 0
    for r in results:
        if r.blocked:
            continue
        if r.item.special == "recycle_bin":
            if winapi.empty_recycle_bin():
                irreversible += r.size
            continue
        for e in r.entries:
            try:
                s, _ = entry_size(e)
                n += 1
                pairs.append([e, quarantine.move_in(e, run_id, n)])
                moved += s
            except OSError:
                skipped += 1      # fichier en cours d'utilisation : on le laisse
    names = ", ".join(r.item.name for r in results if not r.blocked)
    details = ((T("Mis en quarantaine : {v0} élément. Ignorés (utilisés) : {v1}. "
                  "Corbeille vidée (définitif) : {v2} o. Éléments : {v3}") if len(pairs) == 1
                else T("Mis en quarantaine : {v0} éléments. Ignorés (utilisés) : {v1}. "
                       "Corbeille vidée (définitif) : {v2} o. Éléments : {v3}"))
               .format(v0=len(pairs), v1=skipped, v2=irreversible, v3=names))
    if pairs or irreversible:
        journal.add("pairs", "Nettoyage", details, {"pairs": pairs} if pairs else None,
                    meta={"bytes": moved + irreversible})
    return {"moved": moved, "skipped": skipped, "irreversible": irreversible, "n": len(pairs), "pairs": pairs}
