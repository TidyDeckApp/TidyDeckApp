"""Mode Discret : fail-closed, aucun alias persiste."""
import glob
import os
import unittest

from tests import ROOT  # noqa: F401
from Shared.Utils import privacy


class MaskTest(unittest.TestCase):
    def test_disabled_returns_text_untouched(self):
        s = "C:\\Users\\Quelquun\\x"
        self.assertEqual(privacy.mask(s, False), s)

    def test_empty_and_none_safe(self):
        self.assertEqual(privacy.mask("", True), "")
        self.assertIsNone(privacy.mask(None, True))

    def test_home_becomes_tilde(self):
        from pathlib import Path
        home = str(Path.home())
        out = privacy.mask(home + os.sep + "Downloads", True)
        self.assertTrue(out.startswith("~"), out)
        self.assertNotIn(home, out)

    def test_username_masked(self):
        u = os.environ.get("USERNAME") or ""
        if len(u) <= 2:
            self.skipTest("USERNAME trop court pour etre masque par convention")
        self.assertNotIn(u, privacy.mask("bonjour " + u + " !", True))

    def test_computername_masked(self):
        c = os.environ.get("COMPUTERNAME") or ""
        if len(c) <= 2:
            self.skipTest("COMPUTERNAME trop court")
        self.assertNotIn(c, privacy.mask("poste " + c, True))


class FailClosedTest(unittest.TestCase):
    def test_exception_in_text_yields_mask_not_plaintext(self):
        class Boom(str):
            def __str__(self):
                raise RuntimeError("exploser")

        self.assertEqual(privacy.mask(Boom("secret"), True), privacy.MASK)

    def test_exception_in_patterns_yields_mask(self):
        orig = privacy._patterns
        privacy._patterns = lambda: (_ for _ in ()).throw(RuntimeError("panne"))
        try:
            self.assertEqual(privacy.mask("C:\\Users\\Quelquun", True), privacy.MASK)
        finally:
            privacy._patterns = orig
            privacy._cache = None

    def test_mask_symbol_is_not_a_real_value(self):
        self.assertEqual(privacy.MASK, "•••")


class NoAliasPersistenceTest(unittest.TestCase):
    def test_module_declares_no_persistence(self):
        path = os.path.join(ROOT, "Shared", "Utils", "privacy.py")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        for forbidden in ("json.dump", "open(", "write"):
            self.assertNotIn(forbidden, src,
                            f"privacy.py ne doit rien ecrire sur le disque ({forbidden})")

    def test_no_alias_file_in_data_dir(self):
        local = os.environ.get("LOCALAPPDATA", "")
        hits = [p for p in glob.glob(os.path.join(local, "TidyDeck", "**", "*"), recursive=True)
                if "alias" in os.path.basename(p).lower()]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
