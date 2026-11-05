"""Version minimale annoncee = Python 3.10. Ce test verifie reellement que la
source se compile avec le parseur 3.10 (pas seulement « ca marche chez moi »)."""
import ast
import io
import os
import unittest

from tests import ROOT

IGNORER = {"__pycache__", ".git", "_shots"}


def _fichiers_py():
    for racine, dirs, fichiers in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in IGNORER)
        for f in sorted(fichiers):
            if f.endswith(".py"):
                yield os.path.join(racine, f)


class CompileEnPython310Test(unittest.TestCase):
    def test_source_propre_en_310(self):
        problemes = []
        n = 0
        for p in _fichiers_py():
            if os.sep + "vendor" + os.sep in p:
                continue
            n += 1
            src = io.open(p, encoding="utf-8").read()
            try:
                ast.parse(src, filename=p, feature_version=(3, 10))
            except SyntaxError as e:
                problemes.append(f"{os.path.relpath(p, ROOT)}:{e.lineno} {e.msg}")
        self.assertGreater(n, 50, "le test n'a rien trouve a verifier")
        self.assertFalse(problemes, "syntaxe trop recente pour 3.10 :\n" + "\n".join(problemes))

    def test_vendor_compatible_aussi(self):
        problemes = []
        for p in _fichiers_py():
            if os.sep + "vendor" + os.sep not in p:
                continue
            src = io.open(p, encoding="utf-8", errors="replace").read()
            try:
                ast.parse(src, filename=p, feature_version=(3, 10))
            except SyntaxError as e:
                problemes.append(f"{os.path.relpath(p, ROOT)}:{e.lineno} {e.msg}")
        self.assertFalse(problemes, "qrcode embarque trop recent pour 3.10 :\n" + "\n".join(problemes))


if __name__ == "__main__":
    unittest.main()
