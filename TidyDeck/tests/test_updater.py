# -*- coding: utf-8 -*-
"""#40 : le bouton « Mises à jour » est le seul accès réseau, sur clic uniquement.

Le zip est téléchargé depuis la release GitHub du dépôt SEULEMENT (URL contrôlée),
avec son .sha256 obligatoire : hash bon = fichier gardé, hash faux = fichier
supprimé, annulation = rien ne reste, et aucun appel réseau ne part tout seul."""
import ast
import hashlib
import io
import json
import os
import unittest
import urllib.request
from unittest import mock

from Services.UpdateChecker import checker

ZIP = b"PK\x03\x04" + b"TidyDeck-faux-contenu" * 1000
SHA = hashlib.sha256(ZIP).hexdigest()
TAG = "9.9.9"
BASE_DL = f"https://github.com/{checker.REPO}/releases/download/v{TAG}"
URL_ZIP = f"{BASE_DL}/TidyDeck-{TAG}-win64.zip"
URL_SHA = f"{BASE_DL}/TidyDeck-{TAG}-win64.zip.sha256"
URL_API = checker.API_URL


def release(assets):
    return json.dumps({"tag_name": f"v{TAG}", "assets": assets}).encode()


def bon_zip():
    return [{"name": f"TidyDeck-{TAG}-win64.zip", "browser_download_url": URL_ZIP, "size": len(ZIP)}]


def bon_sha():
    return [{"name": f"TidyDeck-{TAG}-win64.zip.sha256", "browser_download_url": URL_SHA, "size": 80}]


class _Resp:
    def __init__(self, data=b"", chunks=None, headers=None, on_read=None):
        self._buf = io.BytesIO(data)
        self._chunks = list(chunks) if chunks is not None else None
        self.headers = headers or {}
        self.on_read = on_read

    def read(self, n=-1):
        if self.on_read:
            self.on_read()
        if self._chunks is not None:
            return self._chunks.pop(0) if self._chunks else b""
        return self._buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Urlopen:
    """Faux urllib : enregistre chaque URL demandée, renvoie ce qu'on lui donne."""

    def __init__(self, routes):
        self.routes = routes
        self.asked = []

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        self.asked.append(url)
        r = self.routes[url] if url in self.routes else (_ for _ in ()).throw(OSError("hors/routes"))
        if callable(r):
            return r()
        return _Resp(data=r)


class VerifTest(unittest.TestCase):
    def test_nouvelle_version_detectee(self):
        fake = _Urlopen({URL_API: release(bon_zip() + bon_sha())})
        with mock.patch.object(urllib.request, "urlopen", fake):
            r = checker.verifier()
        self.assertEqual(r["statut"], "maj")
        self.assertEqual(r["tag"], TAG)
        self.assertEqual(fake.asked, [URL_API])

    def test_url_hors_repo_refusee(self):
        assets = [{"name": f"TidyDeck-{TAG}-win64.zip", "browser_download_url":
                   "https://evil.example.com/TidyDeck.zip", "size": 1}] + bon_sha()
        fake = _Urlopen({URL_API: release(assets)})
        with mock.patch.object(urllib.request, "urlopen", fake):
            r = checker.verifier()
        self.assertEqual(r["statut"], "inverifiable")
        self.assertEqual(fake.asked, [URL_API], "rien ne doit être téléchargé d'une URL hors dépôt")

    def test_sha256_absent_on_ne_telecharge_pas(self):
        fake = _Urlopen({URL_API: release(bon_zip())})
        with mock.patch.object(urllib.request, "urlopen", fake):
            r = checker.verifier()
        self.assertEqual(r["statut"], "inverifiable")
        self.assertEqual(fake.asked, [URL_API])


class TelechargementTest(unittest.TestCase):
    def _go(self, routes, stop_at=None, tmp=None):
        etat = {"n": 0}
        stop = {"v": False}
        routes = dict(routes)

        def zip_maker():
            def lire():
                etat["n"] += 1
                if stop_at and etat["n"] >= stop_at:
                    stop["v"] = True
            chunks = [ZIP[i:i + 997] for i in range(0, len(ZIP), 997)]
            return _Resp(chunks=chunks, headers={"Content-Length": str(len(ZIP))}, on_read=lire)

        if stop_at:
            routes[URL_ZIP] = zip_maker
        fake = _Urlopen(routes)
        with mock.patch.object(urllib.request, "urlopen", fake):
            r = checker.telecharger(tmp, {"name": f"TidyDeck-{TAG}-win64.zip", "url": URL_ZIP, "size": len(ZIP)},
                                    {"name": "x.sha256", "url": URL_SHA, "size": 80},
                                    annule=lambda: stop["v"])
        return r, fake

    def test_hash_ok_fichier_garde(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            routes = {URL_SHA: f"{SHA}  TidyDeck-{TAG}-win64.zip".encode(), URL_ZIP: ZIP}
            r, fake = self._go(routes, tmp=tmp)
            self.assertEqual(r["statut"], "ok")
            cible = os.path.join(tmp, f"TidyDeck-{TAG}-win64.zip")
            with open(cible, "rb") as fh:
                self.assertEqual(fh.read(), ZIP)
            self.assertFalse(any(f.endswith(".part") for f in os.listdir(tmp)))

    def test_hash_faux_fichier_supprime(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            routes = {URL_SHA: b"0" * 64 + b"  TidyDeck.zip", URL_ZIP: ZIP}
            r, fake = self._go(routes, tmp=tmp)
            self.assertEqual(r["statut"], "abime")
            self.assertEqual(os.listdir(tmp), [], "le fichier abîmé ne doit rien laisser sur le disque")

    def test_annulation_rien_ne_reste(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            routes = {URL_SHA: f"{SHA}  x".encode(), URL_ZIP: ZIP}
            r, fake = self._go(routes, stop_at=3, tmp=tmp)
            self.assertEqual(r["statut"], "annule")
            self.assertEqual(os.listdir(tmp), [], "aucun .part ne doit survivre à l'annulation")

    def test_jamais_ecrase_suffixe(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            nom = f"TidyDeck-{TAG}-win64.zip"
            open(os.path.join(tmp, nom), "wb").write(b"ancien")
            routes = {URL_SHA: f"{SHA}  x".encode(), URL_ZIP: ZIP}
            r, fake = self._go(routes, tmp=tmp)
            self.assertEqual(r["statut"], "ok")
            self.assertEqual(r["chemin"], os.path.join(tmp, "TidyDeck-9.9.9-win64 (2).zip"))
            with open(os.path.join(tmp, nom), "rb") as fh:
                self.assertEqual(fh.read(), b"ancien")


class ZeroReseauSansClicTest(unittest.TestCase):
    def test_import_du_checker_ne_appelle_personne(self):
        src = open(checker.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    fn = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
                    self.assertNotIn(fn, ("urlopen", "Request"),
                                     "un appel réseau ne peut vivre qu'à l'intérieur d'une fonction")

    def test_seule_la_page_apropos_declenche(self):
        racine = os.path.dirname(os.path.dirname(os.path.abspath(checker.__file__)))
        racine = os.path.dirname(os.path.dirname(racine))
        for d, dirs, fs in os.walk(os.path.join(racine, "UI")):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in fs:
                if f.endswith(".py"):
                    src = open(os.path.join(d, f), encoding="utf-8").read()
                    if "UpdateChecker" in src:
                        self.assertEqual(f, "about_page.py",
                                         "seul le bouton « Mises à jour » peut toucher le réseau")


class ClicMajTest(unittest.TestCase):
    """Clic du bouton « Mises à jour » : vérification AU CLIC, proposition d'ouvrir
    la page officielle si une version plus récente existe, jamais de téléchargement
    automatique. Les trois messages attendus sont vérifiés ici sans fenêtre Tk."""

    def _page(self):
        from UI.Pages import about_page as ap

        p = ap.AboutPage.__new__(ap.AboutPage)
        p.maj_btn = mock.Mock()
        p.maj_lbl = mock.Mock()
        p.ctx = mock.Mock()
        p.ctx.root.after = lambda ms, f: f()
        return p, ap

    def _clic(self, p, ap, statut_retour):
        with mock.patch.object(ap, "run_bg", lambda root, fn, fini: fini(fn(), None)), \
             mock.patch.object(ap.checker, "verifier", lambda: dict(statut_retour)), \
             mock.patch.object(ap, "webbrowser") as wb, \
             mock.patch.object(ap.messagebox, "showinfo") as info:
            p._maj()
        return wb, info

    def test_a_jour_le_message(self):
        p, ap = self._page()
        wb, info = self._clic(p, ap, {"statut": "jour", "tag": "0.6.1"})
        p.maj_lbl.configure.assert_called_with(text="Tu as la dernière version (0.6.1).")
        info.assert_not_called()
        wb.open.assert_not_called()

    def test_nouvelle_version_ouvre_la_page_si_ok(self):
        p, ap = self._page()
        p._propose_page = mock.Mock(return_value=True)
        with mock.patch.object(ap, "run_bg", lambda root, fn, fini: fini(fn(), None)), \
             mock.patch.object(ap.checker, "verifier", lambda: {"statut": "maj", "tag": "9.9.9"}), \
             mock.patch.object(ap, "webbrowser") as wb:
            p._maj()
        p._propose_page.assert_called_once_with("9.9.9")
        wb.open.assert_called_once_with(ap.SITE_TELECHARGEMENT)
        p.maj_lbl.configure.assert_called_with(text="Page ouverte dans ton navigateur.")

    def test_plus_tard_ne_telecharge_rien(self):
        p, ap = self._page()
        p._propose_page = mock.Mock(return_value=False)
        with mock.patch.object(ap, "run_bg", lambda root, fn, fini: fini(fn(), None)), \
             mock.patch.object(ap.checker, "verifier", lambda: {"statut": "maj", "tag": "9.9.9"}), \
             mock.patch.object(ap, "webbrowser") as wb:
            p._maj()
        wb.open.assert_not_called()

    def test_hors_ligne_le_message(self):
        p, ap = self._page()
        wb, info = self._clic(p, ap, {"statut": "hors_ligne"})
        info.assert_called_once_with("TidyDeck", "Impossible de joindre la page des versions.")
        wb.open.assert_not_called()

    def test_linterface_ne_telecharge_plus_rien(self):
        import inspect
        from UI.Pages import about_page as ap
        src = inspect.getsource(ap)
        self.assertNotIn("checker.telecharger", src,
                         "plus aucun téléchargement ne doit partir de l'interface")

    def test_fenetre_propose_ouvrir_la_page(self):
        import inspect
        from UI.Pages import about_page as ap
        src = inspect.getsource(ap.AboutPage._propose_page)
        self.assertIn("preview_dialog", src)
        self.assertIn("Ouvrir la page", src)
        self.assertIn("Plus tard", src)

    def test_appel_reseau_uniquement_dans_le_clic(self):
        import inspect
        from UI.Pages import about_page as ap
        tree = ast.parse(inspect.getsource(ap))
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef) and fn.name not in ("_maj", "fini"):
                for n in ast.walk(fn):
                    if isinstance(n, ast.Attribute) and n.attr == "verifier":
                        self.fail("checker.verifier ne doit être appelé que par le clic (_maj)")


if __name__ == "__main__":
    unittest.main()
