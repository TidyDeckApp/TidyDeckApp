# -*- coding: utf-8 -*-
"""#41 : la Corbeille doit etre sommee lecteur par lecteur.

L'appel historique SHQueryRecycleBinW(None) ne rapporte que le lecteur courant :
sur une machine a plusieurs disques les chiffres etaient faux. Giarde-fous verifies
ici : somme correcte, lecteur en echec ignore sans crash, plus jamais d'appel global."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from Shared.Utils import winapi


class _ShellFake:
    """Faux shell32 : repond pour les lecteurs connus, echoue proprement ailleurs."""

    def __init__(self, bins, refus=(), crash=()):
        self.bins = dict(bins)
        self.refus = set(refus)
        self.crash = set(crash)
        self.asked = []

    def SHQueryRecycleBinW(self, root, pi):
        self.asked.append(root)
        if root is None:
            raise AssertionError("interdit de questionner la Corbeille « globale » : faux chiffres")
        if root in self.refus:
            return 1
        if root in self.crash:
            raise OSError("lecteur illisible")
        size, n = self.bins[root]
        pi.contents.i64Size = size
        pi.contents.i64NumItems = n
        return 0


def _run(shell, drives, tmp=None):
    with mock.patch.object(winapi, "_fixed_drives", lambda: drives), \
            mock.patch.object(winapi, "_shell32", lambda: shell), \
            mock.patch("Shared.Utils.common.data_dir", lambda: Path(tmp) if tmp else Path(".")):
        return winapi.recycle_bin_info()


class CorbeilleParLecteurTest(unittest.TestCase):
    def test_somme_deux_lecteurs(self):
        shell = _ShellFake({"C:\\": (2 << 30, 300), "D:\\": (1 << 30, 40)})
        size, n = _run(shell, ["C:\\", "D:\\"])
        self.assertEqual(size, 3 << 30)
        self.assertEqual(n, 340)
        self.assertEqual(shell.asked, ["C:\\", "D:\\"])

    def test_un_lecteur_en_echec_est_ignore_sans_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            shell = _ShellFake({"C:\\": (1 << 30, 120)}, refus=["D:\\"])
            size, n = _run(shell, ["C:\\", "D:\\"], tmp)
            self.assertEqual((size, n), (1 << 30, 120))
            self.assertIn("D:\\", winapi.ECHECS_CORBEILLE)
            self.assertNotIn("C:\\", winapi.ECHECS_CORBEILLE)
            log = Path(tmp, "debug.log").read_text(encoding="utf-8")
            self.assertIn("corbeille", log)
            self.assertIn("D:\\", log)

    def test_un_lecteur_fait_planer_le_appel_est_ignore(self):
        shell = _ShellFake({"C:\\": (5, 1)}, crash=["E:\\"])
        size, n = _run(shell, ["C:\\", "E:\\"])
        self.assertEqual((size, n), (5, 1))
        self.assertEqual(winapi.ECHECS_CORBEILLE, ["E:\\"])

    def test_aucun_lecteur_fixe_ne_plante_pas(self):
        shell = _ShellFake({})
        shell_ref = mock.patch.object(winapi, "_query_global", lambda: (0, 0))
        with shell_ref:
            self.assertEqual(_run(shell, []), (0, 0))

    def test_jamais_d_appel_global_quand_des_lecteursexistent(self):
        shell = _ShellFake({"C:\\": (1, 1)})
        _run(shell, ["C:\\"])
        self.assertNotIn(None, shell.asked)


if __name__ == "__main__":
    unittest.main()
