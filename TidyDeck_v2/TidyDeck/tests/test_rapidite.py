# -*- coding: utf-8 -*-
"""Rapidite : ce qui doit etre cache, et ce qui ne doit plus faire attendre.

Le relevé materiel coute ~4,5 s (PowerShell + WMI). Il doit etre cache sur disque
12 h et recharge en avance (prefetch) pour ne jamais tomber sur un clic.
"""
import json
import os
import shutil
import tempfile
import threading
import time
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from Shared.Utils import lang

RELEVE = {
    "Os": {"Caption": "Microsoft Windows 11 Famille", "Build": "22631", "UBR": 3007, "Display": "23H2"},
    "Board": [{"Manufacturer": "Micro-Star International Co., Ltd.", "Product": "MPG B550 GAMING PLUS"}],
    "Cpu": [{"Name": "AMD Ryzen 7 5800X", "NumberOfCores": 8, "NumberOfLogicalProcessors": 16,
             "MaxClockSpeed": 3800}],
    "Ram": [{"Capacity": 16 << 30, "Speed": 3200, "ConfiguredClockSpeed": 3200, "SMBIOSMemoryType": 26}],
    "Gpu": [{"Name": "NVIDIA GeForce RTX 3070", "DriverVersion": "551.86",
             "DriverDate": "2024-03-12", "AdapterRAM": 0}],
    "Vram": [], "Sound": [], "Pnp": [], "Endpoints": [],
    "Disks": [{"DeviceID": "C:", "Size": 500 << 30, "FreeSpace": 120 << 30, "VolumeName": ""}],
    "Phys": [], "DiskMap": [], "Audio": "Casque Nano",
}


class _HwCase(unittest.TestCase):
    def setUp(self):
        from Core.SystemInfo import hardware
        self.hw = hardware
        self.tmp = tempfile.mkdtemp(prefix="td_hw_")
        self._saved = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = self.tmp
        hardware._cache.clear()
        self.appels = []

        def faux_run_ps(script, timeout=45):
            self.appels.append(script)
            time.sleep(0.05)            # comme un vrai releve, mais court
            return 0, json.dumps(RELEVE)
        self._run_ps = hardware.run_ps
        hardware.run_ps = faux_run_ps
        self._nv = hardware.nvidia.query
        hardware.nvidia.query = lambda q: []

    def tearDown(self):
        self.hw.run_ps = self._run_ps
        self.hw.nvidia.query = self._nv
        if self._saved is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.hw._cache.clear()

    def _touche_cache(self):
        return os.path.exists(os.path.join(self.tmp, "TidyDeck", "hardware.json"))


class CacheDisqueTest(_HwCase):
    def test_premier_releve_ecrit_le_cache(self):
        self.assertFalse(self._touche_cache())
        d = self.hw.load()
        self.assertEqual(d["Cpu"][0]["Name"], "AMD Ryzen 7 5800X")
        self.assertTrue(self._touche_cache(), "le releve doit etre garde sur disque")

    def test_releve_suivant_ne_relance_pas_powerhell(self):
        self.hw.load()
        self.hw._cache.clear()          # on simule un nouveau lancement du logiciel
        self.appels.clear()
        t0 = time.perf_counter()
        d = self.hw.load()
        ms = (time.perf_counter() - t0) * 1000
        self.assertEqual(self.appels, [], "un cache disque doit eviter tout appel PowerShell")
        self.assertLess(ms, 200, "lecture du cache : %.0f ms, ca doit etre instantane" % ms)
        self.assertEqual(d["Cpu"][0]["Name"], "AMD Ryzen 7 5800X")

    def test_cache_trop_vieux_est_rejete(self):
        self.hw.load()
        p = os.path.join(self.tmp, "TidyDeck", "hardware.json")
        with open(p, encoding="utf-8") as fh:
            o = json.load(fh)
        o["ts"] = time.time() - (self.hw.CACHE_DUREE + 600)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(o, fh)
        self.hw._cache.clear()
        self.appels.clear()
        self.hw.load()
        self.assertEqual(len(self.appels), 1, "un cache perime doit declencher une nouvelle lecture")

    def test_cache_abime_ne_casse_rien(self):
        os.makedirs(os.path.join(self.tmp, "TidyDeck"), exist_ok=True)
        with open(os.path.join(self.tmp, "TidyDeck", "hardware.json"), "w", encoding="utf-8") as fh:
            fh.write("{ moitie de fichier, coup")
        self.hw._cache.clear()
        d = self.hw.load()               # doit relire, pas planter
        self.assertEqual(d["Cpu"][0]["Name"], "AMD Ryzen 7 5800X")

    def test_releve_demo_n_est_pas_garde(self):
        def faux(_s, timeout=45):
            return 1, ""                 # PowerShell echoue -> demo
        self.hw.run_ps = faux
        d = self.hw.load()
        self.assertTrue(d.get("demo"))
        self.assertFalse(self._touche_cache(),
                        "un relevé de démo ne doit pas se faire passer pour du réel en cache")

    def test_est_chaud_reflete_le_cache(self):
        self.assertFalse(self.hw.est_chaud())
        self.hw.load()
        self.assertTrue(self.hw.est_chaud())
        self.hw._cache.clear()
        self.assertTrue(self.hw.est_chaud(), "chaud doit aussi voir le cache disque")

    def test_force_relit_malgre_le_cache(self):
        self.hw.load()
        self.appels.clear()
        self.hw.load(force=True)
        self.assertEqual(len(self.appels), 1)

    def test_deux_threads_une_seule_lecture(self):
        """Sans verrou, deux pages ouvertes en meme temps paieraient 2 x 4,5 s."""
        vus = []
        ths = [threading.Thread(target=lambda: vus.append(self.hw.load())) for _ in range(4)]
        [t.start() for t in ths]
        [t.join() for t in ths]
        self.assertEqual(len(vus), 4)
        self.assertLessEqual(len(self.appels), 1,
                             "%d lectures PowerShell pour 4 demandeurs : le verrou ne joue pas"
                             % len(self.appels))


class PrefetchTest(unittest.TestCase):
    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_l_app_prefetch_le_materiel_des_l_ouverture(self):
        import UI.app as appmod
        appels = []
        from Core.SystemInfo import hardware
        saved = hardware.load

        def spy(force=False):
            appels.append(force)
            return saved(force=force)
        hardware.load = spy
        app = None
        try:
            app = appmod.App()
            lang.set_lang("fr")
            app.root.update()
            for _ in range(80):
                app.root.update()
                time.sleep(0.02)
                if appels:
                    break
            self.assertTrue(appels, "le materiel doit etre recharge en tache de fond "
                                   "sans attendre qu'on clique sur Info PC")
            self.assertNotIn(True, appels, "le prefetch ne doit pas forcer le cache")
        finally:
            hardware.load = saved
            if app is not None:
                app.root.destroy()


class VeilleFondTest(unittest.TestCase):
    def test_intervalle_de_polling_raccourci(self):
        import UI.components as c
        self.assertLessEqual(c.POLL_FOND, 50,
                            "l'attente de fin de tache doit etre imperceptible")

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_run_bg_ne_crie_pas_apres_fermeture(self):
        """Fenetre fermee pendant une tache de fond : le resultat est abandone en
        silence, il ne doit pas remonter une erreur Tk (celle qui pollue les logs)."""
        import tkinter as tk
        from UI.components import run_bg
        root = tk.Tk()
        root.withdraw()
        fini = []
        run_bg(root, lambda: (time.sleep(0.15), "ok")[1], lambda r, e: fini.append(r))
        root.update()
        root.destroy()                    # ferme pendant que la tache tourne
        time.sleep(0.3)                   # la tache a fini : plus personne pour la recevoir
        self.assertEqual(fini, [], "apres fermeture, rien ne doit etre livre")

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_run_bg_delivre_en_vive(self):
        import tkinter as tk
        from UI.components import run_bg
        root = tk.Tk()
        root.withdraw()
        fini = []
        run_bg(root, lambda: (time.sleep(0.08), "ok")[1], lambda r, e: fini.append(r))
        t0 = time.perf_counter()
        while not fini and time.perf_counter() - t0 < 3:
            root.update()
            time.sleep(0.005)
        root.destroy()
        self.assertEqual(fini, ["ok"])
        self.assertLess((time.perf_counter() - t0) * 1000, 600,
                        "la livraison arrive vite, pas 120 ms apres 120 ms")


class FeedbackScanTest(unittest.TestCase):
    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def test_doublons_et_oublies_affichent_une_attente(self):
        """Sans barre d'attente, un scan de plusieurs secondes parait bloque."""
        src = open(os.path.join(ROOT, "UI", "Pages", "storage_page.py"), encoding="utf-8").read()
        for meth in ("def find_old", "def find_clips"):
            i = src.index(meth)
            bloc = src[i:i + 400]
            self.assertIn("self.busy(", bloc, "%s : pas de mise en attente" % meth)
        for meth in ("def _old", "def _clips"):
            i = src.index(meth)
            bloc = src[i:i + 200]
            self.assertIn("self.idle()", bloc, "%s : la fin n'est pas signalee" % meth)


if __name__ == "__main__":
    unittest.main()
