"""Navigation : structure, sections repliables, clavier, mise a l'echelle."""
import unittest

from tests import HAS_DISPLAY, ROOT  # noqa: F401
from UI.app import NAV_ITEMS, ADVANCED_ONLY, SERENE_TOP, flatten_nav


class NavSpecTest(unittest.TestCase):
    def test_serene_top_has_exactly_six(self):
        self.assertEqual(len(SERENE_TOP), 6, "la Sérénité doit exposer exactement 6 entrées")

    def test_serene_top_entries_exist_in_nav(self):
        all_names = {n for n, _ in flatten_nav(NAV_ITEMS)}
        for n in SERENE_TOP:
            self.assertIn(n, all_names, f"{n} n'existe pas dans la nav")

    def test_advanced_only_item_is_in_nav(self):
        all_names = {n for n, _ in flatten_nav(NAV_ITEMS)}
        self.assertIn("Applications préinstallées", all_names)

    def test_flatten_keeps_badges(self):
        d = dict(flatten_nav(NAV_ITEMS))
        self.assertEqual(d.get("Applications préinstallées"), "Avancé")
        self.assertEqual(d.get("Services"), "Admin")

    def test_no_duplicate_entries(self):
        names = [n for n, _ in flatten_nav(NAV_ITEMS)]
        self.assertEqual(len(names), len(set(names)))


@unittest.skipUnless(HAS_DISPLAY, "pas d'affichage")
class SidebarBehaviourTest(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from UI import theme
        from UI.components import Sidebar
        self.root = tk.Tk()
        self.root.geometry("1200x750+0+0")
        self.root.update()
        cfg = {"theme": "sombre", "text_size": "normale", "colorblind": False}
        self.colors, _, _ = theme.apply(self.root, cfg)
        self.Sidebar = Sidebar

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def build(self, serenity=False, advanced=True, size="normale"):
        from UI import theme
        items = NAV_ITEMS if not serenity else (
            list(SERENE_TOP) + [("PLUS", [n if not b else (n, b)
                                        for n, b in flatten_nav(NAV_ITEMS)
                                        if n not in SERENE_TOP], False)])
        self.sel = []
        sb = self.Sidebar(self.root, items, lambda n: self.sel.append(n), self.colors,
                         disabled=set() if advanced else set(ADVANCED_ONLY),
                         scale=theme.SIZES[size])
        sb.pack(fill="both", expand=True)
        self.root.update()
        return sb

    def test_content_fits_750(self):
        for serenity in (False, True):
            sb = self.build(serenity)
            tot = 0
            for c in sb.pack_slaves():
                p = c.pack_info()["pady"]
                tot += c.winfo_reqheight() + (sum(p) if isinstance(p, (tuple, list)) else int(p) * 2)
            self.assertLessEqual(tot, 750, f"sidebar trop grande (serenity={serenity}) : {tot}")

    def test_advanced_off_disables_but_keeps_visible(self):
        sb = self.build(advanced=False)
        self.assertIn("Applications préinstallées", sb.nav_items)
        row, border, lbl, fs = sb.nav_items["Applications préinstallées"]
        self.assertEqual(lbl.cget("fg"), sb.colors["sidebar_muted"])
        self.assertEqual(str(row.cget("takefocus")), "0")
        self.assertNotIn("Applications préinstallées", sb._visible())

    def test_advanced_on_enables(self):
        sb = self.build(advanced=True)
        lbl = sb.nav_items["Applications préinstallées"][2]
        self.assertNotEqual(lbl.cget("fg"), sb.colors["sidebar_muted"])
        self.assertIn("Applications préinstallées", sb._visible())

    def test_serenity_plus_collapsed_by_default(self):
        sb = self.build(serenity=True)
        self.assertFalse(sb._sections["PLUS"]["expanded"])
        self.assertEqual(sb._sections["PLUS"]["child_frame"].winfo_manager(), "")
        self.assertTrue(sb._sections["PLUS"]["header"][2].cget("text").startswith("▸"))
        self.assertEqual(sb._visible()[:6], SERENE_TOP)

    def test_toggle_does_not_navigate(self):
        sb = self.build(serenity=True)
        sb._toggle_section("PLUS")
        self.assertTrue(sb._sections["PLUS"]["expanded"])
        self.assertTrue(sb._sections["PLUS"]["header"][2].cget("text").startswith("▾"))
        self.assertIn("Applications préinstallées", sb._visible())
        self.assertEqual(self.sel, [], "déplier ne doit pas déclencher de navigation")

    def test_enter_on_section_toggles_only(self):
        sb = self.build(serenity=True)
        self.assertFalse(sb._sections["PLUS"]["expanded"])
        sb._enter("PLUS")
        self.assertTrue(sb._sections["PLUS"]["expanded"], "Entrée doit déplier")
        sb._enter("PLUS")
        self.assertFalse(sb._sections["PLUS"]["expanded"], "Entrée doit replier")
        self.assertEqual(self.sel, [], "aucune navigation sur une section")

    def test_enter_on_item_selects(self):
        sb = self.build()
        sb._enter("Accueil")
        self.assertEqual(self.sel, ["Accueil"])

    def test_keyboard_down_moves_focus(self):
        sb = self.build()
        r0 = sb._row_of("Accueil")
        r0.focus_force()
        self.root.update()
        vis = sb._visible()
        nxt = vis[vis.index("Accueil") + 1]
        sb._move(1, r0)
        self.root.update()
        self.assertIs(self.root.focus_get(), sb._row_of(nxt),
                      "Down doit aller sur l'entrée visible suivante")

    def test_left_on_child_collapses_parent_and_focuses_it(self):
        sb = self.build(serenity=True)
        sb._toggle_section("PLUS")
        rb = sb._row_of("Journaux")
        rb.focus_force()
        self.root.update()
        sb._arrow("Journaux", False)
        self.root.update()
        self.assertIs(self.root.focus_get(), sb._row_of("PLUS"))
        self.assertFalse(sb._sections["PLUS"]["expanded"])

    def test_fonts_follow_text_size(self):
        from UI import theme

        def size_of(widget):
            for tok in str(widget.cget("font")).split():
                try:
                    return int(tok)
                except ValueError:
                    pass
            self.fail("pas de taille de police trouvée")

        for size in ("normale", "grande"):
            sb = self.build(size=size)
            s = theme.SIZES[size]
            self.assertEqual(size_of(sb.nav_items["Accueil"][2]), max(8, round(11 * s)), size)
            self.assertEqual(size_of(sb.nav_items["Journaux"][2]), max(8, round(10 * s)), size)

    def test_active_item_is_bold(self):
        sb = self.build()
        sb.select("Nettoyage")
        f = str(sb.nav_items["Nettoyage"][2].cget("font"))
        self.assertIn("bold", f)
        sb.select("Accueil")
        f2 = str(sb.nav_items["Nettoyage"][2].cget("font"))
        self.assertNotIn("bold", f2, "l'entrée inactive doit perdre le gras")


if __name__ == "__main__":
    unittest.main()
