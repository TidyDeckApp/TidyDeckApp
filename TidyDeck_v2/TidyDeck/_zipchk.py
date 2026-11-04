# -*- coding: utf-8 -*-
import io, sys, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
zf = zipfile.ZipFile(r"C:\Users\Florius\Downloads\AI\Test\TidyDeck-0.6.0.zip")
name = [n for n in zf.namelist() if n.endswith("translations.py")][0]
s = zf.read(name).decode("utf-8")
for bad in ("vour", "onlv", "rirechts", "Loas", "reajstry", "look its name up"):
    print(bad, "DANS LE ZIP" if bad in s else "absent du zip (OK)")
