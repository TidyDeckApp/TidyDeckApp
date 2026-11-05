"""Import de profil : une valeur invalide doit etre ignoree, jamais appliquee."""
import unittest

from tests import ROOT  # noqa: F401
from UI.Profile.profile import sanitize, _valid_tweaks, BOOL_KEYS, CHOICES, RANGES


class SanitizeTest(unittest.TestCase):
    def test_clean_profile_passes_through(self):
        raw = {"theme": "sombre", "text_size": "grande", "colorblind": True,
               "advanced": False, "serenity": True, "close_action": "minimize",
               "sound": True, "reminder": False, "quarantine_days": 14}
        ok, skipped = sanitize(raw)
        self.assertEqual(skipped, [])
        self.assertEqual(ok, raw)

    def test_bad_enum_is_rejected(self):
        ok, skipped = sanitize({"theme": "hot_pink"})
        self.assertNotIn("theme", ok)
        self.assertEqual(len(skipped), 1)
        self.assertIn("Thème", skipped[0])

    def test_bad_bool_is_rejected(self):
        for k in BOOL_KEYS:
            ok, skipped = sanitize({k: "oui"})
            self.assertNotIn(k, ok, f"{k} aurait du etre rejete")
            self.assertEqual(len(skipped), 1)

    def test_zero_and_one_are_not_bools(self):
        ok, _ = sanitize({"serenity": 1})
        self.assertNotIn("serenity", ok, "1 n'est pas un booleen JSON strict")

    def test_quarantine_days_range(self):
        self.assertEqual(sanitize({"quarantine_days": 7})[0]["quarantine_days"], 7)
        for bad in (0, -1, 366, 100000):
            ok, skipped = sanitize({"quarantine_days": bad})
            self.assertNotIn("quarantine_days", ok, f"{bad} hors plage accepte")
            self.assertEqual(len(skipped), 1)

    def test_quarantine_days_bool_is_rejected(self):
        ok, _ = sanitize({"quarantine_days": True})
        self.assertNotIn("quarantine_days", ok, "True n'est pas un entier")

    def test_legacy_theme_names_are_mapped(self):
        self.assertEqual(sanitize({"theme": "tdah_calm"})[0]["theme"], "tdah")
        self.assertEqual(sanitize({"theme": "gamer"})[0]["theme"], "sombre")

    def test_all_declared_choices_accepted(self):
        for key, values in CHOICES.items():
            for v in values:
                ok, skipped = sanitize({key: v})
                self.assertEqual(skipped, [], f"{key}={v} refuse a tort")
                self.assertEqual(ok[key], v)

    def test_missing_config_block(self):
        ok, skipped = sanitize(None)
        self.assertEqual(ok, {})
        self.assertEqual(len(skipped), 1)

    def test_unknown_keys_are_ignored_not_applied(self):
        ok, _ = sanitize({"evil_key": "boom", "theme": "clair"})
        self.assertNotIn("evil_key", ok)
        self.assertEqual(ok["theme"], "clair")

    def test_partial_validity_keeps_the_valid_part(self):
        ok, skipped = sanitize({"theme": "tdah", "text_size": "huge", "serenity": True})
        self.assertEqual(ok, {"theme": "tdah", "serenity": True})
        self.assertEqual(len(skipped), 1)


class TweaksValidationTest(unittest.TestCase):
    def test_non_list_returns_empty(self):
        self.assertEqual(_valid_tweaks(None), [])
        self.assertEqual(_valid_tweaks("nope"), [])
        self.assertEqual(_valid_tweaks(42), [])

    def test_unknown_ids_dropped(self):
        self.assertEqual(_valid_tweaks(["does_not_exist"]), [])

    def test_known_ids_kept(self):
        from Core.Tweaks import tweaks
        known = list(tweaks.BY_ID.keys())[:3]
        self.assertTrue(known, "aucun regle declare : test a revoir")
        self.assertEqual(_valid_tweaks(known), known)

    def test_mixed_list_keeps_only_known(self):
        from Core.Tweaks import tweaks
        known = list(tweaks.BY_ID.keys())[:2]
        out = _valid_tweaks(known + ["fake", 12, None])
        self.assertEqual(out, known)


if __name__ == "__main__":
    unittest.main()
