"""Applications qui ne répondent plus — fermeture propre d'abord, forcée seulement si tu confirmes."""
import csv
import io
from Shared.Utils.common import IS_WINDOWS, run_cmd


def not_responding():
    if not IS_WINDOWS:
        return []
    _, out = run_cmd(["tasklist", "/FI", "STATUS eq NOT RESPONDING", "/FO", "CSV", "/NH"], 20)
    res = []
    for row in csv.reader(io.StringIO(out)):
        if len(row) >= 2 and row[1].strip().isdigit():
            res.append({"name": row[0], "pid": int(row[1])})
    return res


def close(pid, force=False):
    args = ["taskkill", "/PID", str(pid)] + (["/F"] if force else [])
    return run_cmd(args, 15)[0] == 0
