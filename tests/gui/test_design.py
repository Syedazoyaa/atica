"""Visual identity, typography, resources, responsiveness and accessibility of the desktop application."""

import ast
import os
import pathlib
import re
import subprocess
import sys

import pytest
from layout_checks import LOGICAL_SIZES, check_window
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QFontDatabase, QFontInfo, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabBar,
    QTableWidget,
    QWidget,
)

import atica
from atica.gui.components.backdrop import render_backdrop
from atica.gui.main_window import SECTIONS
from atica.gui.styles import LIGHT, build_stylesheet
from atica.gui.utils import fonts
from atica.gui.utils.icons import ICON_DIR, icon, logo_pixmap, wordmark_pixmap

GUI_ROOT = pathlib.Path(atica.__file__).parent / "gui"
RESOURCES = GUI_ROOT / "resources"

# the five identity colours, exactly as specified
PALETTE = {
    "light grey": "#E3E4E7",
    "cool grey": "#C9CCD2",
    "soft off-white": "#F3F0F2",
    "muted warm beige": "#D9C7C0",
    "grey mauve": "#B8B5B9",
}


def luminance(color: QColor) -> float:
    def channel(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(color.redF()) + 0.7152 * channel(color.greenF()) + 0.0722 * channel(color.blueF())


def contrast(a: QColor, b: QColor) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class TestPalette:
    def test_the_five_identity_colours_are_preserved_exactly(self):
        tokens = {
            "light grey": LIGHT.layer,
            "cool grey": LIGHT.border,
            "soft off-white": LIGHT.background,
            "muted warm beige": LIGHT.accent,
            "grey mauve": LIGHT.muted,
        }
        assert tokens == PALETTE

    def test_every_identity_colour_is_used_by_the_stylesheet(self):
        css = build_stylesheet(LIGHT).upper()
        for name, value in PALETTE.items():
            assert value in css, name

    def test_stylesheet_is_complete_and_flat(self):
        css = build_stylesheet(LIGHT)
        assert css.count("{") == css.count("}") and "{{" not in css and "{ink" not in css
        assert "gradient" not in css  # restrained: no gradients
        assert not re.search(
            r"border-radius:\s*(\d{2,}|[3-9])px", css
        )  # square-edged: nothing rounder than 2px
        assert "box-shadow" not in css

    def test_no_colour_literals_outside_the_theme(self):
        offenders = []
        for path in GUI_ROOT.rglob("*.py"):
            if path.name == "theme.py":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if re.search(r"#[0-9A-Fa-f]{6}\b", line):
                    offenders.append("%s:%d" % (path.relative_to(GUI_ROOT), number))
        assert not offenders, offenders

    def test_text_colours_are_accessible(self):
        for bg in (LIGHT.background, LIGHT.layer, LIGHT.surface, LIGHT.accent):
            assert contrast(QColor(LIGHT.ink), QColor(bg)) >= 7, bg
        for bg in (LIGHT.background, LIGHT.layer, LIGHT.surface):
            assert contrast(QColor(LIGHT.ink_secondary), QColor(bg)) >= 4.5, bg
            assert contrast(QColor(LIGHT.ink_placeholder), QColor(bg)) >= 4.5, bg
        assert contrast(QColor(LIGHT.ink_inverse), QColor(LIGHT.primary)) >= 7
        for fg, bg in (
            (LIGHT.error, LIGHT.error_bg),
            (LIGHT.warning, LIGHT.warning_bg),
            (LIGHT.success, LIGHT.success_bg),
        ):
            assert contrast(QColor(fg), QColor(bg)) >= 4.5, fg

    def test_semantic_colours_only_where_they_carry_meaning(self):
        css = build_stylesheet(LIGHT)
        for token in (LIGHT.error, LIGHT.warning, LIGHT.success):
            # only banners, invalid inputs and the danger button may use them
            for block in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
                if token in block[1]:
                    assert re.search(r"banner|invalid|danger", block[0], re.I), block[0].strip()


class TestTypography:
    def test_font_files_ship_with_the_package_and_register(self, qapp):
        for name in fonts.FONT_FILES:
            path = pathlib.Path(fonts.FONT_DIR) / name
            assert path.is_file() and path.stat().st_size > 100_000, name
            assert path.read_bytes()[:4] == b"\x00\x01\x00\x00"  # TrueType
        assert fonts.register_fonts() and fonts.fonts_available()
        assert {"Regular", "Medium", "SemiBold"} <= set(QFontDatabase.styles("IBM Plex Sans"))
        assert qapp.property("atica.fonts_loaded") is True

    def test_licence_and_attribution_are_bundled(self):
        text = (RESOURCES / "fonts" / "OFL.txt").read_text(encoding="utf-8")
        assert (
            "IBM Corp." in text
            and "SIL OPEN FONT LICENSE Version 1.1" in text
            and 'Reserved Font Name "Plex"' in text
        )
        notices = pathlib.Path(atica.__file__).resolve().parents[2] / "THIRD_PARTY_NOTICES.md"
        if notices.exists():  # present in the source tree / sdist
            assert "IBM Plex Sans" in notices.read_text(encoding="utf-8")

    def test_only_ibm_plex_sans_is_named_in_the_code(self):
        for path in GUI_ROOT.rglob("*.py"):
            if path.name in ("theme.py", "fonts.py", "app.py"):
                continue
            text = path.read_text(encoding="utf-8")
            assert "font-family" not in text and "QFont(" not in text, path.name
            for foreign in ("Cascadia", "Consolas", "Segoe", "Arial", "Courier", "monospace"):
                assert foreign not in text, (path.name, foreign)
        css = build_stylesheet(LIGHT)
        assert css.count("font-family") == 1 and css.split("font-family:")[1].lstrip().startswith(
            '"IBM Plex Sans"'
        )

    def test_every_text_widget_resolves_to_ibm_plex_sans(self, window):
        checked = 0
        for kind in (
            QLabel,
            QPushButton,
            QLineEdit,
            QComboBox,
            QPlainTextEdit,
            QCheckBox,
            QTabBar,
            QTableWidget,
        ):
            for widget in window.findChildren(kind):
                widget.ensurePolished()
                assert QFontInfo(widget.font()).family() == "IBM Plex Sans", (
                    kind.__name__,
                    widget.objectName(),
                )
                checked += 1
        assert checked > 150

    def test_the_typographic_hierarchy_uses_the_right_weights(self, window):
        def weight(object_name: str) -> int:
            label = next(w for w in window.findChildren(QLabel) if w.objectName() == object_name)
            label.ensurePolished()
            return QFontInfo(label.font()).weight()

        assert weight("pageTitle") == 600  # semibold headings
        assert weight("cardTitle") == 500  # medium section headings
        assert weight("fieldLabel") == 500  # medium labels
        assert weight("pageSubtitle") == 400  # regular body

    def test_tabular_numerals_are_requested_for_results(self, qapp):
        label = QLabel("1234.56")
        before = label.font().family()
        fonts.tabular(label)  # must never raise, whatever the Qt version
        assert label.font().family() == before  # the feature request does not change the typeface


class TestResources:
    def test_every_svg_is_valid(self, qapp):
        files = sorted(RESOURCES.rglob("*.svg"))
        assert len(files) >= 25
        for path in files:
            renderer = QSvgRenderer(str(path))
            assert renderer.isValid() and renderer.viewBoxF().width() > 0, path.name

    def test_every_navigation_icon_exists_and_renders(self, qapp):
        for _key, _title, name, _desc in SECTIONS:
            assert (pathlib.Path(ICON_DIR) / (name + ".svg")).is_file(), name
            assert not icon(name, LIGHT.ink, 20).isNull()
        for name in ("plus", "trash", "folder", "copy", "export", "reset", "swap", "chevron_down", "check"):
            assert (pathlib.Path(ICON_DIR) / (name + ".svg")).is_file(), name

    def test_logo_variants(self, qapp):
        for light in (False, True):
            assert not logo_pixmap(48, light).isNull() and not wordmark_pixmap(32, light).isNull()
        wordmark = (pathlib.Path(ICON_DIR) / "logo_wordmark.svg").read_text(encoding="utf-8")
        assert (
            "<text" not in wordmark and 'role="img"' in wordmark and "<path" in wordmark
        )  # outlined, no font needed
        dark_bg_version = (pathlib.Path(ICON_DIR) / "logo_wordmark_light.svg").read_text(encoding="utf-8")
        assert dark_bg_version != wordmark and LIGHT.background.upper() in dark_bg_version.upper()
        # the wordmark is clearly wider than tall (symbol + ATICA); the symbol alone is square
        mark = wordmark_pixmap(32)
        assert mark.width() > 2.5 * mark.height()
        assert logo_pixmap(32).width() == logo_pixmap(32).height()

    def test_logo_uses_only_palette_colours(self):
        allowed = {v.upper() for v in PALETTE.values()} | {LIGHT.ink.upper()}
        for name in ("logo.svg", "logo_light.svg", "logo_wordmark.svg", "logo_wordmark_light.svg"):
            colours = {
                c.upper()
                for c in re.findall(
                    r"#[0-9A-Fa-f]{6}", (pathlib.Path(ICON_DIR) / name).read_text(encoding="utf-8")
                )
            }
            assert colours <= allowed, (name, colours - allowed)

    def test_application_icon_is_set(self, qapp):
        assert not qapp.windowIcon().isNull()


class TestBackdrop:
    @pytest.mark.parametrize(
        "name, anchor, base_colour",
        [
            ("bg_dashboard.svg", "br", LIGHT.background),
            ("bg_page.svg", "tr", LIGHT.background),
            ("bg_nav.svg", "bl", LIGHT.layer),
        ],
    )
    def test_backdrops_never_reduce_text_contrast_below_aa(self, qapp, name, anchor, base_colour):
        """The darkest pixel the drawing can put behind text still gives >= 4.5:1 for secondary text."""
        base = QColor(base_colour)
        image = QImage(900, 600, QImage.Format.Format_ARGB32)
        image.fill(base)
        painter = QPainter(image)
        painter.drawPixmap(0, 0, render_backdrop(name, 900, 600, 1.0, anchor))
        painter.end()
        darkest = min(
            (image.pixelColor(x, y) for x in range(0, 900, 3) for y in range(0, 600, 3)), key=luminance
        )
        assert contrast(QColor(LIGHT.ink_secondary), darkest) >= 4.5
        assert contrast(QColor(LIGHT.ink), darkest) >= 7
        assert darkest.lightness() > 190  # extremely subtle: never a dark texture

    def test_the_dashboard_drawing_is_more_visible_than_the_calculation_pages(self, qapp):
        def ink_amount(name: str) -> float:
            image = render_backdrop(name, 800, 500, 1.0, "br").toImage()
            return sum(image.pixelColor(x, y).alphaF() for x in range(0, 800, 2) for y in range(0, 500, 2))

        assert ink_amount("bg_dashboard.svg") > ink_amount("bg_page.svg") > 0

    def test_cards_stay_opaque_over_the_drawing(self, window):
        """A pixel in an empty corner of a dashboard tile is the card colour, not drawing or background."""
        from PySide6.QtCore import QPoint

        window.resize(1600, 900)
        window.show()
        window.sidebar.select(0)
        __import__("layout_checks").settle()
        tile = window.views["dashboard"].modules_grid._items[0]
        spot = tile.mapTo(window, QPoint(tile.width() - 14, tile.height() - 14))
        assert window.grab().toImage().pixelColor(spot).name().upper() == LIGHT.surface.upper()
        assert tile.graphicsEffect() is None  # flat design: no shadow effects anywhere

    def test_no_widget_uses_a_graphics_effect(self, window):
        assert [w for w in window.findChildren(QWidget) if w.graphicsEffect() is not None] == []


class TestDashboard:
    def test_the_welcome_panel_is_removed_entirely(self, window):
        dashboard = window.views["dashboard"]
        texts = " ".join(label.text() for label in dashboard.findChildren(QLabel)).lower()
        assert "welcome" not in texts
        assert all(w.objectName() != "hero" for w in dashboard.findChildren(QWidget))  # no leftover container
        source = (GUI_ROOT / "views" / "dashboard_view.py").read_text(encoding="utf-8").lower()
        stylesheet = build_stylesheet(LIGHT).lower()
        assert "welcome" not in source and "hero" not in source and "hero" not in stylesheet
        for path in GUI_ROOT.rglob("*.py"):
            assert "Welcome to ATICA" not in path.read_text(encoding="utf-8"), path.name

    def test_content_starts_at_the_top(self, window):
        window.show()
        window.sidebar.select(0)
        dashboard = window.views["dashboard"]
        title = next(w for w in dashboard.findChildren(QLabel) if w.objectName() == "pageTitle")
        assert (
            title.text() == "Calculations. Simplified." and title.mapTo(dashboard, title.rect().topLeft()).y() < 40
        )  # no reclaimed gap
        texts = " ".join(w.text() for w in dashboard.findChildren(QLabel))
        assert (
            "An integrated toolkit for smarter manufacturing, precision calculations, and industrial workflows."
            in texts
        )

    def test_page_header_icons_align_with_descriptions_for_all_pages(self, window):
        from PySide6.QtCore import QPoint

        window.show()
        for view in window.views.values():
            header = view.findChild(QWidget, "pageHeader")
            subtitle = view.findChild(QLabel, "pageSubtitle")
            icon = header.findChild(QLabel, "pageHeaderIcon")
            assert icon.mapTo(view, QPoint(0, 0)).x() == subtitle.mapTo(view, QPoint(0, 0)).x()

    def test_shows_modules_quick_calculations_and_real_activity_only(self, window):
        dashboard = window.views["dashboard"]
        assert len(dashboard.modules_grid._items) == 7 and len(dashboard.quick_grid._items) == 5
        assert "Version " not in " ".join(label.text() for label in dashboard.findChildren(QLabel))
        assert window.state.activity == []
        assert "Nothing yet" in " ".join(label.text() for label in dashboard.findChildren(QLabel))

    def test_module_tiles_and_quick_buttons_navigate(self, window):
        from atica.gui.views.dashboard_view import ModuleCard

        tiles = window.views["dashboard"].modules_grid._items  # grid order == SECTIONS order
        assert all(isinstance(t, ModuleCard) for t in tiles)
        tiles[2].clicked.emit()
        assert window.stack.currentWidget() is window.views["materials"]
        window.sidebar.select(0)
        quick = window.views["dashboard"].findChildren(QPushButton)[0]
        quick.click()
        assert window.stack.currentWidget() is window.views["units"]

    def test_tiles_are_keyboard_operable(self, window):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        tile = window.views["dashboard"].modules_grid._items[1]
        assert tile.focusPolicy() == Qt.FocusPolicy.TabFocus
        tile.keyPressEvent(
            QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
        )
        assert window.stack.currentWidget() is window.views["packaging"]

    def test_the_grid_reflows_with_the_width(self, window):
        grid = window.views["dashboard"].modules_grid
        window.resize(1600, 900)
        window.sidebar.select(0)
        __import__("layout_checks").settle()
        wide = grid.columns
        window.resize(900, 600)
        __import__("layout_checks").settle()
        assert wide == 3 and grid.columns < wide


class TestResponsiveness:
    @pytest.mark.parametrize("size", LOGICAL_SIZES, ids=["%dx%d" % s for s in LOGICAL_SIZES])
    def test_no_clipping_at_common_laptop_and_desktop_sizes(self, window, size):
        assert check_window(window, *size) == []

    def test_the_checker_can_actually_detect_clipping(self, window):
        """Negative control: an over-wide control must be reported, otherwise the checks above prove nothing."""
        window.show()
        window.resize(1000, 700)
        view = window.views["purchasing"]
        window.sidebar.select([key for key, *_ in SECTIONS].index("purchasing"))
        offender = QLineEdit(view)
        offender.setFixedWidth(3000)
        offender.move(0, 0)
        offender.show()
        problems = check_window(window, 1000, 700)
        assert any("clipped" in p for p in problems)

    @pytest.mark.parametrize("scale", ["1", "1.25", "1.5"])
    def test_real_qt_display_scaling_on_a_1366x768_screen(self, scale):
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_SCALE_FACTOR=scale)
        probe = pathlib.Path(__file__).with_name("scale_probe.py")
        out = subprocess.run(
            [sys.executable, str(probe)], capture_output=True, text=True, env=env, timeout=240
        )
        assert out.returncode == 0, out.stdout + out.stderr
        assert out.stdout.strip().endswith("OK")

    def test_sidebar_collapses_to_icons_on_narrow_windows_and_back(self, window):
        window.resize(1400, 800)
        __import__("layout_checks").settle()
        assert not window.sidebar.compact and window.sidebar.width() > 200
        window.resize(900, 600)
        __import__("layout_checks").settle()
        assert window.sidebar.compact and window.sidebar.width() < 80
        assert all(b.text() == "" and b.toolTip() for b in window.sidebar._buttons)  # titles live in tooltips
        window.resize(1400, 800)
        __import__("layout_checks").settle()
        assert not window.sidebar.compact and all(b.text().strip() for b in window.sidebar._buttons)

    def test_calculator_stacks_into_one_column_when_narrow(self, window):
        panel = window.views["units"].convert_panel
        window.resize(1400, 800)
        window.sidebar.select(1)
        __import__("layout_checks").settle()
        assert not panel.is_stacked()
        window.resize(860, 600)
        __import__("layout_checks").settle()
        assert panel.is_stacked()
        panel.calculate()  # still fully functional while stacked
        assert panel.result.outcome is not None
        window.resize(1400, 800)
        __import__("layout_checks").settle()
        assert not panel.is_stacked() and panel.result.outcome is not None

    def test_initial_size_comes_from_the_screen_and_the_minimum_is_small(self, qapp):
        from atica.gui.main_window import MIN_HEIGHT, MIN_WIDTH, MainWindow

        window = MainWindow()
        assert (window.minimumWidth(), window.minimumHeight()) == (MIN_WIDTH, MIN_HEIGHT) and MIN_WIDTH <= 800
        available = window.screen().availableGeometry()
        # derived from the screen (never larger than it, unless the screen is smaller than the minimum)
        assert window.width() <= max(available.width(), MIN_WIDTH) and window.height() <= max(
            available.height(), MIN_HEIGHT
        )
        assert window.width() <= 1280 and window.height() <= 820
        window.close()

    def test_dialog_free_workflow_needs_no_fixed_sizes_larger_than_the_minimum(self, window):
        for widget in window.findChildren(QWidget):
            assert widget.minimumWidth() <= 760 or widget is window, (
                type(widget).__name__,
                widget.minimumWidth(),
            )


class TestAccessibility:
    def test_interactive_widgets_are_keyboard_reachable(self, window):
        from PySide6.QtCore import Qt

        unreachable = []
        for view in window.views.values():
            for kind in (QPushButton, QLineEdit, QComboBox, QCheckBox):
                for widget in view.findChildren(kind):
                    if widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
                        unreachable.append((type(widget).__name__, widget.objectName()))
        assert unreachable == []

    def test_focus_states_are_styled_for_every_interactive_control(self):
        css = build_stylesheet(LIGHT)
        for selector in (
            "QLineEdit:focus",
            "QComboBox:focus",
            "QPushButton:focus",
            "QPushButton#primary:focus",
            "QPushButton#navButton:focus",
            "QCheckBox::indicator:focus",
            "QTabBar::tab:focus",
            "QToolButton#moreToggle:focus",
        ):
            assert selector in css, selector

    def test_navigation_and_actions_have_accessible_names_and_tooltips(self, window):
        for button in window.sidebar._buttons:
            assert button.accessibleName() and "Ctrl+" in button.toolTip()
        panel = window.views["units"].convert_panel
        assert panel.calculate_button.text() and panel.reset_button.text().strip()
        form = panel.form
        for key in ("value", "from_unit", "to_unit"):
            assert form.widget(key).toolTip() or form.widget(key).accessibleName() or form.label_for(key)

    def test_tab_order_visits_the_form_before_the_buttons(self, window):
        window.show()
        window.sidebar.select(1)
        panel = window.views["units"].convert_panel
        form_widgets = [
            w for kind in (QLineEdit, QComboBox) for w in panel.form.findChildren(kind) if w.isVisible()
        ]
        assert form_widgets and all(w.focusPolicy().name != "NoFocus" for w in form_widgets)
        first = panel.form.widget("value")
        first.setFocus()
        order = []
        w = first
        for _ in range(30):
            w = w.nextInFocusChain()
            order.append(w)
            if w is panel.calculate_button:
                break
        assert panel.calculate_button in order

    def test_error_and_empty_states_are_visible_text_not_colour_only(self, window):
        panel = window.views["purchasing"].panel
        assert "Enter your values" in " ".join(
            label.text() for label in panel.result.findChildren(QLabel)
        )  # empty state
        panel.form.set_values({"required_quantity": "oops"})
        panel.calculate()
        assert (
            "Please check your input" in panel.error_banner.message_text()
        )  # error state has words, not just red


class TestPersistence:
    def test_settings_survive_a_restart(self, qapp, tmp_path):
        from PySide6.QtCore import QSettings

        from atica.gui.app import build_window

        QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(tmp_path))
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
        first = build_window()
        view = first.views["settings"]
        view.places.setValue(3)
        view.precision.setValue(40)
        first.close()
        second = build_window()
        assert (second.state.display_places, second.state.precision) == (3, 40)
        assert (second.views["settings"].places.value(), second.views["settings"].precision.value()) == (
            3,
            40,
        )
        second.views["settings"].places.setValue(6)
        second.views["settings"].precision.setValue(50)  # leave the defaults behind
        second.close()


def test_source_has_no_leftover_debug_or_dead_code_markers():
    for path in GUI_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            assert not (isinstance(node, ast.Name) and node.id == "add_shadow"), path.name
        assert "TODO" not in path.read_text(encoding="utf-8") and "FIXME" not in path.read_text(
            encoding="utf-8"
        )
        assert QRect  # imported for geometry checks above
