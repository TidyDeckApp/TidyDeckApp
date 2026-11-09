import copy
import json
from Shared.Utils.common import data_dir

DEFAULTS = {"first_run": True, "theme": "clair", "text_size": "normale",
            "lang": "fr",
            "colorblind": False, "advanced": False, "quarantine_days": 7,
            "serenity": False, "close_action": "quit", "tray": False, "durations": {}, "last_calm": None,
            "sound": False, "reminder": False, "stream_mode": False, "installed": None,
            "last_reminder": None, "toasts_prev": None, "game_mode_on": False,
            "meals_done": [],
            "express_mode": False,
            "custom_sound": "",
            "sound_volume": 70,
            "rdv_volume": 70,
            "toast_position": "bottom-right",
            "reminders": {"hydration": {"on": False, "every": 60},
                          "meals": {"on": False, "lunch": "12:30", "dinner": "19:30",
                                     "snack_am_on": False, "snack_am": "10:30",
                                     "snack_pm_on": False, "snack_pm": "16:00",
                                     "extra_slots": []},
                          "eyes": {"on": False, "every": 20},
                          "stretch": {"on": False, "every": 90},
                          "defer": "wait", "auto_detect": False, "dnd_enabled": False, "sound": False}}


def migrate(cfg):
    """Ancienne version : la case « tray » se combinait avec close_action.
    Elle est devenue la troisieme valeur exclusive de close_action."""
    if cfg.get("tray") and cfg.get("close_action") != "tray":
        cfg["close_action"] = "tray"
    return cfg


def load():
    cfg = copy.deepcopy(DEFAULTS)
    try:
        cfg.update(json.loads((data_dir() / "config.json").read_text(encoding="utf-8")))
    except Exception:
        from Shared.Utils import depannage
        depannage.noter("Shared/Utils/config.py:39")
    for k, v in DEFAULTS["reminders"].items():          # nouvelles clés ajoutées après coup
        if isinstance(v, dict):
            cfg["reminders"].setdefault(k, {})
            for kk, vv in v.items():
                cfg["reminders"][k].setdefault(kk, vv)
        else:
            cfg["reminders"].setdefault(k, v)
    # « Très grande » (1.5x) n'existe plus : on le ramene a « Grande ».
    if cfg.get("text_size") == "tres_grande":
        cfg["text_size"] = "grande"
    return migrate(cfg)


def save(cfg):
    (data_dir() / "config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
