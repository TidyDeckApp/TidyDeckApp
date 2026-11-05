"""Le burn du mesureur turbo ne doit JAMAIS relancer le programme lui-même.
Dans un .exe, `sys.executable` = TidyDeck.exe : lancer `-c` avec, ouvre une
fenetre TidyDeck par coeur. D'ou le launch PowerShell."""
import os
import subprocess
import unittest

from tests import ROOT  # noqa: F401


def _sources(dossier):
    for racine, dirs, fichiers in os.walk(os.path.join(ROOT, dossier)):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in fichiers:
            if f.endswith(".py"):
                p = os.path.join(racine, f)
                yield p, open(p, encoding="utf-8").read()


class BurnSansSysExecutableTest(unittest.TestCase):
    def test_burn_utilise_powershell(self):
        from Core.SystemInfo.sensors import _burn
        src = open(_burn.__code__.co_filename, encoding="utf-8").read()
        debut = src.index("def _burn")
        corps = src[debut:src.index("\n\n", debut)]
        self.assertIn('"powershell"', corps)
        self.assertNotIn("sys.executable", corps)

    def test_rien_ne_relance_sys_executable_dans_le_projet(self):
        for chemin, src in _sources("Core"):
            for i, ligne in enumerate(src.splitlines(), 1):
                if "sys.executable" in ligne and '"-c"' in ligne:
                    self.fail(f"{chemin}:{i} relance le programme lui-meme : {ligne.strip()}")


@unittest.skipUnless(os.name == "nt", "mesure specifique Windows")
class BurnVivantTest(unittest.TestCase):
    def test_burn_lance_des_powershell_et_rien_dautre(self):
        from Core.SystemInfo import sensors
        procs = sensors._burn(2, 1)
        try:
            self.assertEqual(len(procs), 2)
            self.assertTrue(all(p.poll() is None for p in procs), "les burn doivent tourner")
            # Seuls les DESCENDANTS du test sont coupables : une instance TidyDeck
            # deja ouverte par l'utilisateur n'est pas un fils du burn.
            csv = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name"
                 " | ConvertTo-Csv -NoTypeInformation"],
                capture_output=True, text=True, errors="replace").stdout
            parent_de, nom_de = {}, {}
            for ligne in csv.splitlines()[1:]:
                morceaux = [m.strip('"') for m in ligne.strip().strip('"').split('","')]
                if len(morceaux) == 3 and morceaux[0].isdigit():
                    pid, ppid, nom = int(morceaux[0]), int(morceaux[1]), morceaux[2]
                    parent_de[pid], nom_de[pid] = ppid, nom
            descendants, file = set(), [os.getpid()]
            while file:
                actuelle = file.pop()
                for fils, pere in parent_de.items():
                    if pere == actuelle and fils not in descendants:
                        descendants.add(fils)
                        file.append(fils)
            noms = {nom_de[p] for p in descendants}
            self.assertNotIn("TidyDeck.exe", noms,
                            "le burn ne doit pas ouvrir de fenetre TidyDeck")
            self.assertIn("powershell.exe", noms)
        finally:
            for p in procs:
                p.kill()
            for p in procs:
                p.wait(timeout=10)

    def test_apres_kill_plus_rien_ne_survit(self):
        from Core.SystemInfo import sensors
        procs = sensors._burn(2, 1)
        for p in procs:
            p.kill()
            p.wait(timeout=10)
        self.assertTrue(all(p.poll() is not None for p in procs))


if __name__ == "__main__":
    unittest.main()
