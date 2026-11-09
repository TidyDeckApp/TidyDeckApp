import ast
import os
import tempfile
import unittest

from Shared.Utils import depannage


class DepannageTest(unittest.TestCase):
    def setUp(self):
        self._ancien = os.environ.get("LOCALAPPDATA")

    def tearDown(self):
        if self._ancien is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self._ancien

    def test_noter_ecrit_dans_debug_log(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["LOCALAPPDATA"] = d
            depannage.noter("test-etape")
            p = os.path.join(d, "TidyDeck", "debug.log")
            self.assertTrue(os.path.exists(p))
            with open(p, encoding="utf-8") as fh:
                self.assertIn("test-etape", fh.read())

    def test_noter_capte_exception_en_cours(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["LOCALAPPDATA"] = d
            try:
                1 / 0
            except ZeroDivisionError:
                depannage.noter("zero")
            with open(os.path.join(d, "TidyDeck", "debug.log"), encoding="utf-8") as fh:
                self.assertIn("ZeroDivisionError", fh.read())

    def test_jamais_de_lever_une_erreur(self):
        with tempfile.TemporaryDirectory() as d:
            bloqueur = os.path.join(d, "bloc")
            with open(bloqueur, "w") as fh:
                fh.write("x")
            os.environ["LOCALAPPDATA"] = bloqueur
            depannage.noter("silence")

    def test_taille_plafonnee(self):
        with tempfile.TemporaryDirectory() as d:
            dossier = os.path.join(d, "TidyDeck")
            os.makedirs(dossier)
            p = os.path.join(dossier, "debug.log")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("x" * (depannage.TAILLE_MAX + 100))
            depannage._tronquer(p)
            self.assertLessEqual(os.path.getsize(p), depannage.TAILLE_MAX)


class AnonymisationTest(unittest.TestCase):
    def setUp(self):
        self._ancien = os.environ.get("LOCALAPPDATA")
        self.maison = os.path.expanduser("~")

    def tearDown(self):
        if self._ancien is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self._ancien

    def _journal(self, d):
        with open(os.path.join(d, "TidyDeck", "debug.log"), encoding="utf-8") as fh:
            return fh.read()

    @unittest.skipIf(len(os.path.expanduser("~")) < 4, "chemin home trop court")
    def test_anonymisation_forme_brute(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["LOCALAPPDATA"] = d
            etape = "lecture " + os.path.join(self.maison, "Documents", "x.txt")
            depannage.noter(etape)
            journal = self._journal(d)
            self.assertIn("%USERPROFILE%", journal)
            self.assertNotIn(self.maison, journal)

    @unittest.skipIf(len(os.path.expanduser("~")) < 4, "chemin home trop court")
    def test_anonymisation_forme_echappee(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["LOCALAPPDATA"] = d
            exc = FileNotFoundError(2, "échec sur "
                                    + os.path.join(self.maison, "secret", "slot1.sav"))
            depannage.noter("anonymie", exc)
            journal = self._journal(d)
            self.assertIn("%USERPROFILE%", journal)
            self.assertIn("slot1.sav", journal)
            self.assertNotIn(self.maison, journal)
            self.assertNotIn(self.maison.replace("\\", "\\\\"), journal)


class CablageSilencieuxTest(unittest.TestCase):
    def test_sites_muets_cables(self):
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        restes = []
        for dirpath, dirs, files in os.walk(racine):
            dirs[:] = [x for x in dirs if x not in ("vendor", "__pycache__", "tests", ".git")]
            for f in files:
                if not f.endswith(".py"):
                    continue
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, racine).replace("\\", "/")
                if rel == "Shared/Utils/depannage.py":
                    continue
                with open(p, encoding="utf-8") as fh:
                    arbre = ast.parse(fh.read())
                for n in ast.walk(arbre):
                    if isinstance(n, ast.ExceptHandler) and len(n.body) == 1 \
                            and isinstance(n.body[0], ast.Pass) \
                            and (n.type is None or (isinstance(n.type, ast.Name)
                                                    and n.type.id == "Exception")):
                        restes.append(rel + ":" + str(n.lineno))
        self.assertEqual([], restes)


if __name__ == "__main__":
    unittest.main()
