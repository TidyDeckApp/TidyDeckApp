"""Journal de TOUTES les modifications + moteur d'annulation."""
import json
import time
import uuid
from Shared.Utils.common import data_dir
from Shared.Utils.lang import T

UNDO_HANDLERS = {}


def register_undo(kind):
    def deco(fn):
        UNDO_HANDLERS[kind] = fn
        return fn
    return deco


class Journal:
    def __init__(self):
        self.path = data_dir() / "journal.json"
        self.entries = []
        try:
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            pass

    def _save(self):
        self.path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=1), encoding="utf-8")

    def add(self, kind, title, details="", undo_data=None, meta=None):
        e = {"id": uuid.uuid4().hex[:8], "ts": time.strftime(T("%Y-%m-%d %H:%M:%S")),
             "kind": kind, "title": title, "details": details,
             "undo": undo_data, "undone": False, "meta": meta or {}}
        self.entries.append(e)
        self._save()
        return e

    def undo(self, entry_id) -> str:
        for e in self.entries:
            if e["id"] == entry_id:
                if e["undone"] or not e["undo"]:
                    return "Cette action n'est plus annulable."
                fn = UNDO_HANDLERS.get(e["kind"])
                if not fn:
                    return "Annulation indisponible pour ce type d'action."
                msg = fn(e["undo"])
                e["undone"] = True
                self._save()
                return msg
        return T("Entrée introuvable.")
