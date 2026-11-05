"""Les trois verrous du debloat, testes sans jamais rien desinstaller."""
import unittest

from tests import ROOT  # noqa: F401
from Core.Debloat.debloat import valid_name, _protected, PROTECTED


class NameValidationTest(unittest.TestCase):
    def test_normal_names_accepted(self):
        for n in ("Microsoft.Notepad", "Microsoft.Todos", "some.app-2", "A",
                 "Microsoft.WindowsStore", "x" * 128):
            self.assertTrue(valid_name(n), f"{n} aurait du etre accepte")

    def test_injection_rejected(self):
        bad = [
            "a'; Remove-AppxPackage *; '",
            "pkg|whoami",
            "pkg`x`",
            "pkg;calc",
            "pkg&calc",
            "pkg$(calc)",
            'pkg"name"',
            "pkg name",
            "pkg\\..\\..\\x",
            "pkg\nrm",
            "pkg\t",
            "",
            None,
            42,
            ["list"],
            "x" * 200,
            "-leading-dash",
            ".leading-dot",
        ]
        for n in bad:
            self.assertFalse(valid_name(n), f"{n!r} aurait du etre REJETE")

    def test_valid_name_never_reaches_a_shell(self):
        """Le garde-fou est la regex elle-meme : aucun caractere de commande ne passe."""
        for ch in ";|&`$()<>\"'\\\n\t ":
            self.assertFalse(valid_name("pkg" + ch + "x"), f"{ch!r} passe la regex")


class ProtectedListTest(unittest.TestCase):
    REQUIRED = [
        "Microsoft.Xbox", "Microsoft.Gaming", "Microsoft.XboxGamingOverlay",
        "Microsoft.SecHealthUI", "Microsoft.WindowsAppRuntime",
    ]

    def test_critical_packages_are_protected(self):
        for n in self.REQUIRED:
            self.assertTrue(_protected(n), f"{n} doit etre protege")

    def test_codecs_and_runtime_are_protected(self):
        for n in ("Microsoft.HEIFImageExtension", "Microsoft.WebpImageExtension",
                  "Microsoft.HEVCVideoExtension", "Microsoft.MPEG2VideoExtension",
                  "Microsoft.AV1VideoExtension", "Microsoft.AVCHelper",
                  "Microsoft.RawImageExtension", "Microsoft.LanguageExperiencePackfr-FR"):
            self.assertTrue(_protected(n), f"{n} doit etre protege")

    def test_protection_is_case_insensitive(self):
        for n in ("microsoft.xbox", "MICROSOFT.XBOX", "MiCrOsOfT.GaMiNg"):
            self.assertTrue(_protected(n), f"{n} doit etre protege (insensible a la casse)")

    def test_protected_list_is_non_empty_and_lowercase_fragments(self):
        self.assertGreater(len(PROTECTED), 10)
        for frag in PROTECTED:
            self.assertEqual(frag, frag.lower(), f"fragment {frag} devrait etre en minuscules")

    def test_ordinary_app_not_protected(self):
        self.assertFalse(_protected("Microsoft.SomeRandomApp"))


class SafetyFlagsFailClosedTest(unittest.TestCase):
    """Si la lecture des flags echoue, on doit REFUSER, pas laisser passer."""

    def _break_ps(self, debloat):
        def boom(*a, **k):
            raise RuntimeError("pwsh indisponible")
        orig = debloat.run_ps
        debloat.run_ps = boom
        return orig

    def test_failure_refuses(self):
        from Core.Debloat import debloat
        orig = self._break_ps(debloat)
        try:
            non_removable, framework = debloat.safety_flags("Microsoft.SomeApp")
            self.assertTrue(non_removable, "en cas d'echec il faut refuser (fail-closed)")
        finally:
            debloat.run_ps = orig

    def test_error_return_code_refuses(self):
        from Core.Debloat import debloat
        orig = debloat.run_ps
        debloat.run_ps = lambda *a, **k: (1, "")
        try:
            non_removable, framework = debloat.safety_flags("Microsoft.SomeApp")
            self.assertTrue(non_removable, "code de retour non nul = refus")
        finally:
            debloat.run_ps = orig

    def test_flags_parsed_when_available(self):
        from Core.Debloat import debloat
        orig = debloat.run_ps
        debloat.run_ps = lambda *a, **k: (0, "NR=1 FW=1")
        try:
            self.assertEqual(debloat.safety_flags("Microsoft.SomeApp"), (True, True))
        finally:
            debloat.run_ps = orig

    def test_removable_flags_parsed(self):
        from Core.Debloat import debloat
        orig = debloat.run_ps
        debloat.run_ps = lambda *a, **k: (0, "NR=0 FW=0")
        try:
            self.assertEqual(debloat.safety_flags("Microsoft.SomeApp"), (False, False))
        finally:
            debloat.run_ps = orig


class UninstallRefusalTest(unittest.TestCase):
    """uninstall() doit refuser avant meme d'appeler PowerShell."""

    def _never_run(self):
        from Core.Debloat import debloat

        def boom(*a, **k):
            raise AssertionError("PowerShell ne devait JAMAIS etre appele ici")
        orig = debloat.run_ps
        debloat.run_ps = boom
        return orig

    def test_injection_never_reaches_powershell(self):
        from Core.Debloat import debloat
        orig = self._never_run()
        try:
            for bad in ("a'; Remove-AppxPackage *; '", "pkg|whoami", "pkg`x`", "pkg;calc"):
                ok, msg = debloat.uninstall(bad)
                self.assertFalse(ok, f"{bad!r} aurait du etre refuse")
                self.assertIn("invalide", msg)
        finally:
            debloat.run_ps = orig

    def test_protected_never_reaches_powershell(self):
        from Core.Debloat import debloat
        orig = self._never_run()
        try:
            for p in ("Microsoft.Xbox", "Microsoft.SecHealthUI", "Microsoft.WindowsAppRuntime"):
                ok, msg = debloat.uninstall(p)
                self.assertFalse(ok, f"{p} aurait du etre refuse")
                self.assertIn("protégé", msg)
        finally:
            debloat.run_ps = orig

    def test_non_removable_never_reaches_powershell(self):
        from Core.Debloat import debloat
        orig = debloat.run_ps
        debloat.run_ps = lambda *a, **k: (0, "NR=1 FW=0")
        try:
            ok, msg = debloat.uninstall("Microsoft.SomeApp")
            self.assertFalse(ok)
            self.assertIn("NonRemovable", msg)
        finally:
            debloat.run_ps = orig

    def test_framework_never_reaches_powershell(self):
        from Core.Debloat import debloat
        orig = debloat.run_ps
        debloat.run_ps = lambda *a, **k: (0, "NR=0 FW=1")
        try:
            ok, msg = debloat.uninstall("Microsoft.SomeApp")
            self.assertFalse(ok)
            self.assertIn("framework", msg)
        finally:
            debloat.run_ps = orig


if __name__ == "__main__":
    unittest.main()
