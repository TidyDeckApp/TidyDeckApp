"""Redirections : tout ce sur quoi on clique pour « aller verifier ailleurs » doit
partir vers une cible qui existe (page Parametres reelle, cle de registre reelle,
dossier reel) et ne jamais rester muet.

Ce fichier verrouille les corrections trouvees a l'audit complet du code :
  - la valeur par defaut de open_windows_settings() etait « startup », page qui
    n'existe pas sous Windows (la bonne est « startupapps ») ;
  - os.startfile() reussit MEME sur une URI ms-settings inconnue : sans table de
    pages retirees, le repli « candidate suivante » ne se declenchait jamais ;
  - open_reg_key ouvrait regedit a la racine sans jamais indiquer la cle concernee.
"""
import ast
import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest

from tests import HAS_DISPLAY, ROOT

# Pages « Parametres » dont l'existence est verifiee dans la documentation
# Microsoft Learn (URI ms-settings:<page>).
KNOWN_PAGES = {
    "startupapps", "nightlight", "windowsupdate", "appsfeatures",
    "gaming-gamemode", "gaming-gamedvr", "display-advancedgraphics",
    "privacy-backgroundapps",
}

SKIP_DIRS = {"__pycache__", "packaging", "vendor", ".git", "tests"}


def _py_sources():
    for r, d, fs in os.walk(ROOT):
        d[:] = [x for x in d if x not in SKIP_DIRS]
        for f in sorted(fs):
            if f.endswith(".py") and not f.startswith("_"):
                yield os.path.join(r, f)


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _kw_values(name):
    """Toutes les valeurs litterales passees au mot-cle `name` dans le projet,
    en (chemin relatif, ligne, valeur). Les listes donnent une entree par element."""
    out = []
    for path in _py_sources():
        try:
            tree = ast.parse(_read(path), path)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == name:
                vals = (node.value.elts if isinstance(node.value, ast.List) else [node.value])
                for v in vals:
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        out.append((os.path.relpath(path, ROOT).replace("\\", "/"),
                                   node.lineno, v.value))
    return out


class CiblesDeclareesTest(unittest.TestCase):
    def test_pages_parametres_connues(self):
        for f, ln, v in _kw_values("settings"):
            if v.startswith("ms-settings:"):
                v = v.split(":", 1)[1]
            if v.startswith("control:"):
                continue
            self.assertIn(v, KNOWN_PAGES,
                          f"{f}:{ln} page Parametres inconnue : {v!r}")

    def test_pas_de_page_startup_sans_apps(self):
        for f, ln, v in _kw_values("settings"):
            self.assertNotEqual(v.rstrip(), "startup",
                               f"{f}:{ln} « ms-settings:startup » n'existe pas, "
                               "c'est « startupapps »")

    def test_cles_de_registre_declarees_en_hive_valide(self):
        from Core.Tweaks import tweaks
        for t in tweaks.TWEAKS:
            self.assertIn(t.hive, ("HKCU", "HKLM"),
                          f"{t.id} : hive inconnue {t.hive!r}")
            for v in t.values:
                self.assertTrue(str(v.key).strip(), f"{t.id} : cle vide")

    def test_alias_de_pages_retirees(self):
        from Shared.Utils import common
        for page in common.MS_SETTINGS_REMOVED:
            self.assertIn(page, common.MS_SETTINGS_ALIASES,
                          f"{page} est retiree mais n'a aucun equivalent de repli")
            alias = common.MS_SETTINGS_ALIASES[page]
            self.assertNotIn(alias, common.MS_SETTINGS_REMOVED,
                            f"l'alias {alias} est lui aussi retire")
            self.assertIn(alias, KNOWN_PAGES, f"l'alias {alias} n'est pas une page connue")


class MsSettingsTest(unittest.TestCase):
    def setUp(self):
        from Shared.Utils import common
        self.common = common
        self.calls = []
        self._startfile = common.os.startfile
        common.os.startfile = lambda p: self.calls.append(p)

    def tearDown(self):
        self.common.os.startfile = self._startfile

    def _build(self, b):
        return mock_build(self.common, b)

    def test_defaut_souriage_valide(self):
        default = inspect.signature(self.common.open_windows_settings).parameters["page"].default
        self.assertEqual(default, "startupapps",
                         "la valeur par defaut doit etre une page qui existe")

    def test_page_retiree_basculle_sur_l_alias(self):
        """Mécanisme de repli testé avec une page synthétique : le dictionnaire
        réel est vide tant qu'aucune page utilisée n'a été retirée par Windows."""
        from unittest import mock
        with mock.patch.dict(self.common.MS_SETTINGS_REMOVED, {"pagetest-synth": 22000}), \
             mock.patch.dict(self.common.MS_SETTINGS_ALIASES, {"pagetest-synth": "appsfeatures"}):
            with self._build(26200):
                self.assertFalse(self.common.ms_page_available("pagetest-synth"))
                self.calls.clear()
                self.assertTrue(self.common.open_windows_settings("pagetest-synth"))
                self.assertEqual(self.calls, ["ms-settings:appsfeatures"])

    def test_page_presente_selon_le_build(self):
        from unittest import mock
        with mock.patch.dict(self.common.MS_SETTINGS_REMOVED, {"pagetest-synth": 22000}):
            with self._build(19045):
                self.assertTrue(self.common.ms_page_available("pagetest-synth"))
                self.calls.clear()
                self.assertTrue(self.common.open_windows_settings("pagetest-synth"))
                self.assertEqual(self.calls, ["ms-settings:pagetest-synth"])

    def test_page_inconnue_passee_telle_quelle(self):
        with self._build(26200):
            self.assertTrue(self.common.ms_page_available("startupapps"))
            self.calls.clear()
            self.assertTrue(self.common.open_windows_settings("startupapps"))
            self.assertEqual(self.calls, ["ms-settings:startupapps"])

    def test_uri_complete_acceptee(self):
        with self._build(26200):
            self.assertTrue(self.common.ms_page_available("ms-settings:nightlight"))

    def test_vide_rejete(self):
        self.assertFalse(self.common.open_windows_settings(""))


class _BuildMock:
    def __init__(self, common, build):
        self.common = common
        self.build = build
        self.saved = None

    def __enter__(self):
        import sys as _s
        self.saved = getattr(_s, "getwindowsversion")
        _s.getwindowsversion = lambda: type("V", (), {"build": self.build})
        return self

    def __exit__(self, *a):
        import sys as _s
        _s.getwindowsversion = self.saved


def mock_build(common, build):
    return _BuildMock(common, build)


class CheminRegistreTest(unittest.TestCase):
    def test_reg_path(self):
        from Shared.Utils.common import reg_path
        self.assertEqual(reg_path("HKCU", r"Software\Foo"),
                          r"HKEY_CURRENT_USER\Software\Foo")
        self.assertEqual(reg_path("HKLM", r"\Software\Foo\\"),
                          r"HKEY_LOCAL_MACHINE\Software\Foo")

    @unittest.skipUnless(sys.platform == "win32", "Windows uniquement")
    def test_cles_tweaks_reelles(self):
        import winreg
        from Core.Tweaks import tweaks
        hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
        for t in tweaks.TWEAKS:
            key = t.values[0].key
            try:
                h = winreg.OpenKey(hives[t.hive.upper()], key)
                winreg.CloseKey(h)
            except OSError:
                self.fail(f"{t.id} : cle de registre absente -> {t.hive}\\{key} ; "
                        "le bouton « Ouvrir l'emplacement » menerait dans le vide")


class ResolutionBoutonOuvrirTest(unittest.TestCase):
    """Le bouton « Ouvrir l'emplacement » doit resoudre la cible dans le bon ordre
    et ne jamais rester muet quand il n'y a rien a ouvrir."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="td_redir_")
        self.dossier = os.path.join(self.tmp, "un dossier")
        os.makedirs(self.dossier)
        self.calls = []

        class Rec:
            def __init__(self, name, owner, ret=True):
                self.name, self.ret, self.owner = name, ret, owner

            def __call__(self, *a):
                self.owner.calls.append((self.name,) + tuple(str(x) for x in a))
                return self.ret(*a) if callable(self.ret) else self.ret

        import UI.components as comp
        self.comp = comp
        self.saved = {}
        for fn in ("open_windows_settings", "open_in_explorer", "open_reg_key"):
            self.saved[fn] = getattr(comp, fn)
            setattr(comp, fn, Rec(fn, self))
        self.saved["copy_text"] = comp.copy_text
        comp.copy_text = Rec("copy_text", self)
        self.Rec = Rec

    def tearDown(self):
        for fn, v in self.saved.items():
            setattr(self.comp, fn, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
    def _list(self, rows, serenity=False):
        import tkinter as tk
        from UI.components import Checklist

        class Ctx:
            status_colors = {"ok": "#000000"}
            theme = {"card": "#fff", "line": "#ddd", "fg": "#000", "bg": "#fff"}
            cfg = {"serenity": serenity}

            @staticmethod
            def mask(t):
                return t
        root = getattr(self, "_root", None)
        if root is None:
            root = self._root = tk.Tk()
            root.withdraw()
        lst = Checklist(root, Ctx(), ("A", "B"), checkable=False)
        lst.pack()
        lst.set_rows(rows)
        return lst

    def _open_row(self, lst, iid):
        lst.tree.selection_set(iid)
        lst._open()
        return self.calls[-1] if self.calls else None

    def test_page_parametres_prioritaire(self):
        lst = self._list([dict(id="a", name="x", info="", status="ok",
                              settings=["appsfeatures"], folders=[self.dossier],
                              detail="d")])
        self._open_row(lst, "a")
        self.assertEqual(self.calls[0][0], "open_windows_settings")
        self.assertEqual(self.calls[0][1], "appsfeatures")

    def test_tous_les_candidats_essaies_dans_l_ordre(self):
        self.comp.open_windows_settings = self.Rec(
            "open_windows_settings", self, lambda p: p != "privacy-backgroundapps")
        lst = self._list([dict(id="a", name="x", info="", status="ok",
                              settings=["privacy-backgroundapps", "appsfeatures"],
                              detail="d")])
        self._open_row(lst, "a")
        self.assertEqual(self.calls[0], ("open_windows_settings", "privacy-backgroundapps"))
        self.assertEqual(self.calls[1], ("open_windows_settings", "appsfeatures"))
        self.assertEqual(len(self.calls), 2,
                         "on doit s'arreter des qu une page s ouvre")

    def test_repli_sur_dossier_si_page_impossible(self):
        self.comp.open_windows_settings = self.Rec("open_windows_settings", self, lambda p: False)
        lst = self._list([dict(id="a", name="x", info="", status="ok",
                              settings=["startupapps"], folders=[self.dossier], detail="d")])
        self._open_row(lst, "a")
        self.assertEqual(self.calls[-1], ("open_in_explorer", self.dossier))

    def test_dossier_reel_utilise(self):
        lst = self._list([dict(id="a", name="x", info="", status="ok",
                              folders=[self.dossier], detail="d")])
        self.assertTrue(lst._can_open(lst.rows["a"]))
        self._open_row(lst, "a")
        self.assertEqual(self.calls[0][0], "open_in_explorer")
        self.assertEqual(self.calls[0][1], self.dossier)

    def test_shell_puis_reg(self):
        lst = self._list([
            dict(id="s", name="x", info="", status="ok", shell="services.msc", detail="d"),
            dict(id="r", name="y", info="", status="ok", reg=("HKCU", r"Software\Foo"), detail="d"),
        ])
        self._open_row(lst, "s")
        self.assertIn(("open_in_explorer", "services.msc"), self.calls)
        self._open_row(lst, "r")
        self.assertIn(("copy_text", r"HKEY_CURRENT_USER\Software\Foo"), self.calls)
        self.assertEqual(self.calls[-1], ("open_reg_key", "HKCU", r"Software\Foo"))
        txt = lst.detail.get("1.0", "end").strip()
        self.assertIn("presse-papiers", txt)
        self.assertIn("Rien n'a été modifié", txt)

    def test_dossier_inexistant_non_cliquable(self):
        lst = self._list([dict(id="a", name="x", info="", status="ok",
                              folders=[os.path.join(self.tmp, "pas la")], detail="d")])
        self.assertFalse(lst._can_open(lst.rows["a"]),
                        "un dossier absent ne doit pas rendre le bouton cliquable")

    def test_toujours_une_sortie(self):
        lst = self._list([
            dict(id="a", name="avec", info="", status="ok", settings=["startupapps"], detail="d"),
            dict(id="b", name="sans", info="", status="ok", detail="d"),
        ])
        self.assertTrue(lst._can_open(lst.rows["a"]))
        self.assertFalse(lst._can_open(lst.rows["b"]))


class PrefixeUriTest(unittest.TestCase):
    """Dans le code les adresses sont ecrites sans prefixe (« gaming-gamemode ») :
    ce test verifie que ce qui part realmente vers Windows porte bien
    « ms-settings: », sinon l'URI est ignoree par le systeme."""

    def setUp(self):
        from Shared.Utils import common
        self.common = common
        self.probe = []
        self.saved = (common.os.startfile, common.subprocess.Popen)
        common.os.startfile = lambda p: self.probe.append(str(p))
        common.subprocess.Popen = lambda a, *x, **k: self.probe.append(
            " ".join(str(i) for i in (a if isinstance(a, (list, tuple)) else [a])))

    def tearDown(self):
        self.common.os.startfile, self.common.subprocess.Popen = self.saved

    def _cible(self, v):
        self.probe.clear()
        self.common.open_windows_settings(v)
        return self.probe[0] if self.probe else ""

    def test_toute_page_part_prefixee(self):
        for f, ln, v in _kw_values("settings"):
            cible = self._cible(v)
            self.assertTrue(cible.startswith("ms-settings:") or cible.startswith("control.exe"),
                            f"{f}:{ln} : « {v} » part vers Windows sans prefixe "
                            f"ms-settings: (transmis : {cible!r})")

    def test_une_seule_cible_transmise(self):
        for f, ln, v in _kw_values("settings"):
            self.probe.clear()
            self.common.open_windows_settings(v)
            self.assertEqual(len(self.probe), 1,
                             f"{f}:{ln} : {len(self.probe)} ouvertures pour une seule adresse")

    def test_gaming_gamemode_prefixe(self):
        self.assertEqual(self._cible("gaming-gamemode"), "ms-settings:gaming-gamemode")

    def test_gaming_gamedvr_prefixe(self):
        self.assertEqual(self._cible("gaming-gamedvr"), "ms-settings:gaming-gamedvr")

    def test_control_ne_pas_en_ms_settings(self):
        self.assertEqual(self._cible("control:Microsoft.PowerOptions"),
                          "control.exe /name Microsoft.PowerOptions")


class SelectDansExplorateurTest(unittest.TestCase):
    """« Ouvrir l'emplacement » doit selectionner l'element, pas l'ouvrir dans son
    application associee (un .pdf ne doit pas se lancer dans l'acrobateur)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="td_sel_")
        self.dossier = os.path.join(self.tmp, "dossier")
        os.makedirs(self.dossier)
        self.fichier = os.path.join(self.dossier, "fichier.txt")
        with open(self.fichier, "w", encoding="utf-8") as fh:
            fh.write("x")
        self.calls = []
        from Shared.Utils import common
        self.common = common
        self.saved = (common.os.startfile, common.subprocess.Popen)
        common.os.startfile = lambda p: self.calls.append(("startfile", str(p)))
        common.subprocess.Popen = lambda a, *x, **k: self.calls.append(
            ("Popen", tuple(str(i) for i in (a if isinstance(a, (list, tuple)) else [a]))))

    def tearDown(self):
        self.common.os.startfile, self.common.subprocess.Popen = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dossier_ouvert_normalement(self):
        self.assertTrue(self.common.select_in_explorer(self.dossier))
        self.assertEqual(self.calls[0][0], "startfile")

    def test_fichier_selectionne_pas_ouvert(self):
        self.assertTrue(self.common.select_in_explorer(self.fichier))
        self.assertEqual(self.calls[0][0], "Popen")
        self.assertEqual(self.calls[0][1][0], "explorer.exe")
        self.assertEqual(self.calls[0][1][1], "/select,")
        self.assertEqual(self.calls[0][1][2], self.fichier)

    def test_chemin_vide_rejete(self):
        self.assertFalse(self.common.select_in_explorer(""))

    def test_vide_ne_ouvre_rien(self):
        self.calls.clear()
        self.common.select_in_explorer("")
        self.assertEqual(self.calls, [])


class PlusGrosFichiersTest(unittest.TestCase):
    def test_le_bouton_emplacement_existe(self):
        src = _read(os.path.join(ROOT, "UI", "Pages", "largest_view.py"))
        self.assertIn("def open_loc(self, path):", src)
        self.assertIn("select_in_explorer(path)", src)
        self.assertIn('Rien n\'a été modifié', src)

    def test_mode_discret_demande_avant_ouvrir(self):
        src = _read(os.path.join(ROOT, "UI", "Pages", "largest_view.py"))
        i = src.index("def open_loc")
        bloc = src[i:i + 700]
        self.assertIn("stream_mode", bloc)
        self.assertIn("askyesno", bloc)


class OutilDeVerificationTest(unittest.TestCase):
    """`verif_pages_windows.py` lit les adresses dans le code : ce test empeche la
    doc de l'outil de derivter par rapport au produit."""

    def setUp(self):
        import verif_pages_windows as v
        self.v = v

    def test_toute_adresse_du_code_est_documentee(self):
        non_doc = [a for a, _ in self.v.adresses_du_code() if a not in self.v.DOC]
        self.assertEqual(non_doc, [],
                         "adresses utilisees dans le code mais absentes de la doc de "
                         "verif_pages_windows.py : " + ", ".join(non_doc))

    def test_l_outil_capte_l_appel_direct(self):
        adresses = dict(self.v.adresses_du_code())
        self.assertIn("nightlight", adresses,
                       "le bouton « Anti-lumiere bleue » (appel direct) doit etre capte")
        self.assertTrue(any("tweaks_page" in s for s in adresses["nightlight"]))

    def test_l_outil_capte_les_deux_adresses_citees(self):
        adresses = dict(self.v.adresses_du_code())
        for a in ("gaming-gamemode", "gaming-gamedvr"):
            self.assertIn(a, adresses)

    @unittest.skipUnless(sys.platform == "win32", "Windows uniquement")
    def test_sonde_renvoie_l_prefixe(self):
        from Shared.Utils import common
        for a in ("gaming-gamemode", "gaming-gamedvr", "startupapps"):
            ok, cible, exc = self.v.sonde(common.open_windows_settings, a)
            self.assertIsNone(exc)
            self.assertTrue(ok and cible == "ms-settings:" + a, "%s -> %r" % (a, cible))

    @unittest.skipUnless(sys.platform == "win32", "Windows uniquement")
    def test_le_watchdog_mord_reellement(self):
        """Une adresse nouvelle et non documentee doit etre signalee ( sinon le controle
        est vide )."""
        from Shared.Utils import common
        lignes, soucis = self.v.phase_auto(common, [("page_qui_n_existe_pas_dans_la_doc",
                                                   {"Core/X.py:1"})])
        self.assertEqual(len(lignes), 1)
        self.assertTrue(lignes[0]["souci"])
        self.assertGreaterEqual(soucis, 1)

    def test_pages_de_la_doc_toujours_utilisees(self):
        mortes = self.v.adresses_doc_inutilisees(self.v.adresses_du_code())
        self.assertEqual(mortes, [],
                         "pages decrites mais plus utilisees : " + ", ".join(mortes))

    def test_machine_ignore_le_major(self):
        # sys.getwindowsversion().major vaut 10 meme sous 11 : le nom doit venir du build.
        import sys as _s
        saved = _s.getwindowsversion
        try:
            _s.getwindowsversion = lambda: type("V", (), {"build": 22631})
            self.assertEqual(self.v.machine()[0], "Windows 11")
            _s.getwindowsversion = lambda: type("V", (), {"build": 19045})
            self.assertEqual(self.v.machine()[0], "Windows 10")
        finally:
            _s.getwindowsversion = saved


class PageDemarrageTest(unittest.TestCase):
    def test_startup_page_vers_startupapps(self):
        src = _read(os.path.join(ROOT, "UI", "Pages", "startup_page.py"))
        self.assertIn('row["settings"] = "startupapps"', src)


if __name__ == "__main__":
    unittest.main()
