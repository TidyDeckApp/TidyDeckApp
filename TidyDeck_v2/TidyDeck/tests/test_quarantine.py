"""Restauration de la quarantaine : le coeur du « tout est annulable »."""
import os
import shutil
import tempfile
import unittest

from tests import ROOT  # noqa: F401  (place le projet sur sys.path)


class QuarantineRestoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="td_test_")
        self._saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp
        from Shared.Utils import quarantine
        self.q = quarantine

    def tearDown(self):
        if self._saved is not None:
            os.environ["LOCALAPPDATA"] = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _touch(self, path, content="x"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_move_in_then_restore_round_trip(self):
        src = self._touch(os.path.join(self.tmp, "src", "a.txt"), "bonjour")
        dest = self.q.move_in(src, "run1", 0)
        self.assertTrue(os.path.exists(dest))
        self.assertFalse(os.path.exists(src))

        ok, missing, conflict = self.q.restore([(src, dest)])
        self.assertEqual((ok, missing, conflict), (1, 0, 0))
        self.assertTrue(os.path.exists(src))
        with open(src, encoding="utf-8") as f:
            self.assertEqual(f.read(), "bonjour")
        self.assertFalse(os.path.exists(dest))

    def test_restore_missing_source_is_counted_not_fatal(self):
        ok, missing, conflict = self.q.restore([
            (os.path.join(self.tmp, "nope.txt"), os.path.join(self.tmp, "absent", "nope.txt"))
        ])
        self.assertEqual((ok, missing, conflict), (0, 1, 0))

    def test_restore_does_not_overwrite_existing_file(self):
        """Conflit : si un fichier existe deja a l'emplace d'origine, on ecrase PAS."""
        orig = self._touch(os.path.join(self.tmp, "out", "b.txt"), "NOUVEAU")
        dest = self._touch(os.path.join(self.tmp, "q", "b.txt"), "ANCIEN")

        ok, missing, conflict = self.q.restore([(orig, dest)])
        self.assertEqual((ok, missing, conflict), (0, 0, 1))
        with open(orig, encoding="utf-8") as f:
            self.assertEqual(f.read(), "NOUVEAU", "le fichier en place doit rester intact")
        self.assertTrue(os.path.exists(dest))

    def test_restore_batch_mixes_all_three_cases(self):
        a = self._touch(os.path.join(self.tmp, "a", "a.txt"), "a")
        dest_a = self.q.move_in(a, "run2", 0)
        dest_ghost = os.path.join(self.tmp, "q2", "ghost.txt")
        clash = self._touch(os.path.join(self.tmp, "c", "c.txt"), "en place")
        dest_clash = self._touch(os.path.join(self.tmp, "q2", "c.txt"), "a remplacer")

        ok, missing, conflict = self.q.restore([
            (a, dest_a),
            (os.path.join(self.tmp, "ghost.txt"), dest_ghost),
            (clash, dest_clash),
        ])
        self.assertEqual((ok, missing, conflict), (1, 1, 1))

    def test_purge_zero_removes_everything(self):
        a = self._touch(os.path.join(self.tmp, "z", "z.txt"), "z")
        self.q.move_in(a, "run3", 0)
        self.assertGreater(self.q.total_size(), 0)
        self.q.purge(0)
        self.assertEqual(self.q.total_size(), 0)

    def test_purge_respects_age(self):
        a = self._touch(os.path.join(self.tmp, "w", "w.txt"), "w")
        self.q.move_in(a, "run4", 0)
        self.q.purge(30)  # plus vieux que 30 jours seulement : rien ne part
        self.assertGreater(self.q.total_size(), 0)


if __name__ == "__main__":
    unittest.main()
