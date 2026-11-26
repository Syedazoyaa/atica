import logging
import os
import subprocess
import sys

from PySide6.QtWidgets import QLabel, QPushButton

from atica.gui.components import CalculatorPanel
from atica.gui.main_window import SECTIONS


def panels_of(window):
    return list(window.findChildren(CalculatorPanel))


class TestWindowStructure:
    def test_ten_required_sections_in_order(self, window):
        titles = [t for _k, t, _i, _d in SECTIONS]
        assert titles == [
            "Dashboard",
            "Unit Converter",
            "Packaging Calculations",
            "Materials and BOM",
            "Production Calculations",
            "Quality and Yield",
            "Purchasing Calculations",
            "Data Tools",
            "Settings",
            "About ATICA",
        ]
        assert window.stack.count() == 10 and len(window.sidebar._buttons) == 10

    def test_navigation(self, window):
        for index, (key, *_rest) in enumerate(SECTIONS):
            window.sidebar.select(index)
            assert window.stack.currentWidget() is window.views[key]
            assert window.sidebar.current() == index

    def test_navigate_to_tab(self, window):
        window.navigate("quality", 2)
        assert window.views["quality"].tabs.currentIndex() == 2

    def test_dashboard_tiles_and_quick_tools_navigate(self, window):
        from atica.gui.views.dashboard_view import ModuleCard

        tiles = window.views["dashboard"].findChildren(ModuleCard)
        assert len(tiles) == 7  # six calculation modules + data tools
        tiles[1].clicked.emit()
        assert window.stack.currentWidget() is window.views["packaging"]

    def test_version_is_the_single_package_version(self, window):
        import atica
        from atica.version import __version__

        assert atica.__version__ == __version__ and __version__ in window.windowTitle()

    def test_dashboard_has_no_fabricated_activity(self, window):
        assert window.state.activity == []
        text = " ".join(label.text() for label in window.views["dashboard"].findChildren(QLabel))
        assert "Nothing yet" in text

    def test_activity_appears_only_after_a_real_calculation(self, window):
        window.views["units"].convert_panel.calculate()
        assert len(window.state.activity) == 1 and window.state.activity[0].tool == "Unit converter"


class TestEveryScreenWorks:
    def test_default_examples_calculate(self, window):
        """Every calculator on every screen has working defaults (except the ones that need user input)."""
        needs_input = {"Define a custom unit", "Production capacity from stock"}
        ran = 0
        for panel in panels_of(window):
            card_title = [t.text() for t in panel.findChildren(QLabel, "cardTitle") if t.text() != "Result"][
                0
            ]
            if card_title in needs_input:
                continue
            outcome = panel.calculate()
            assert outcome is not None, "%s: %s" % (card_title, panel.error_banner.message_text())
            assert panel.result.outcome is outcome and outcome.headline
            ran += 1
        assert ran == 16  # 18 calculators, 2 of which need user-supplied input

    def test_known_values_in_the_widgets(self, window):
        v = window.views
        out = v["packaging"].breakdown.calculate()
        assert out.headline == "250 piece = 1 full carton + 10 piece remaining (2 carton required)"
        assert v["units"].convert_panel.calculate().headline == "1000 g"
        assert v["purchasing"].panel.calculate().headline == "130 kg"
        assert v["quality"].scrap.calculate().headline == "1000"  # 950 good units at 5 % scrap


class TestErrorsInTheInterface:
    def test_core_validation_message_and_highlight(self, window):
        panel = window.views["purchasing"].panel
        panel.form.set_values({"required_quantity": "-5"})
        assert panel.calculate() is None
        assert not panel.error_banner.isHidden()
        text = panel.error_banner.message_text()
        assert "Quantity required" in text and "negative" in text
        assert "Traceback" not in text and "required_quantity" not in text
        assert panel.form.widget("required_quantity").property("invalid") is True
        assert panel.result.outcome is None

    def test_fixing_the_input_clears_the_error(self, window):
        panel = window.views["purchasing"].panel
        panel.form.set_values({"required_quantity": "x"})
        assert panel.calculate() is None
        panel.form.set_values({"required_quantity": "10"})
        assert panel.calculate() is not None
        assert panel.error_banner.isHidden() and not panel.form.widget("required_quantity").property(
            "invalid"
        )

    def test_unexpected_failure_is_friendly_and_logged(self, window, caplog):
        panel = window.views["purchasing"].panel
        panel._runner = lambda values: (_ for _ in ()).throw(RuntimeError("boom internal detail"))
        with caplog.at_level(logging.ERROR, logger="atica.gui"):
            assert panel.calculate() is None
        text = panel.error_banner.message_text()
        assert "Something went wrong" in text and "boom" not in text and "Traceback" not in text
        assert any("boom internal detail" in (r.exc_text or "") or r.exc_info for r in caplog.records)

    def test_incompatible_unit_shows_hint(self, window):
        panel = window.views["units"].convert_panel
        panel.form.set_values({"from_unit": "kg", "to_unit": "m"})
        assert panel.calculate() is None
        assert "different things" in panel.error_banner.message_text()

    def test_reset_restores_defaults_and_clears_results(self, window):
        panel = window.views["units"].convert_panel
        panel.form.set_values({"value": "99"})
        panel.calculate()
        panel.reset()
        assert panel.form.values()["value"] == "1" and panel.result.outcome is None


class TestScreens:
    def test_unit_screen_swap_filter_and_custom_unit(self, window):
        view = window.views["units"]
        form = view.convert_panel.form
        form.set_values({"from_unit": "kg", "to_unit": "lb"})
        swap = [b for b in view.convert_panel.findChildren(QPushButton) if "Swap" in b.text()][0]
        swap.click()
        assert form.values()["from_unit"] == "lb" and form.values()["to_unit"] == "kg"
        # filtering by quantity type
        form.set_values({"category": "temperature"})
        unit_combo = form.widget("from_unit")
        assert {unit_combo.itemData(i) for i in range(unit_combo.count()) if unit_combo.itemData(i)} == {
            "K",
            "C",
            "F",
            "R",
        }
        # custom unit appears everywhere
        form.set_values({"category": ""})
        custom = view.custom_panel
        custom.form.set_values({"name": "bag", "factor": "25", "reference_unit": "kg"})
        assert custom.calculate().headline == "1 bag = 25 kg"
        assert form.widget("from_unit").findData("bag") >= 0
        assert window.views["purchasing"].panel.form.widget("unit").text() == "kg"
        assert view._custom_table.rowCount() == 1
        view._remove("bag")
        assert view._custom_table.rowCount() == 0 and form.widget("from_unit").findData("bag") < 0

    def test_packaging_hierarchy_edit_updates_other_tabs(self, window):
        view = window.views["packaging"]
        view.levels.set_rows([["piece", "1"], ["pack", "6"], ["case", "4"]])
        assert view.hierarchy.calculate() is not None
        combo = view.breakdown.form.widget("to_level")
        assert [combo.itemData(i) for i in range(combo.count())] == ["piece", "pack", "case"]
        view.breakdown.form.set_values({"quantity": "100", "from_level": "piece", "to_level": "case"})
        out = view.breakdown.calculate()
        assert out.headline.startswith("100 piece = 4 full case + 4 piece remaining")  # 24 pieces per case

    def test_invalid_hierarchy_is_reported_not_applied(self, window):
        view = window.views["packaging"]
        before = window.state.product
        view.levels.set_rows([["piece", "1"], ["box", "0"]])
        assert view.hierarchy.calculate() is None
        assert "Row 2" in view.hierarchy.error_banner.message_text()
        assert window.state.product is before

    def test_bom_editor_feeds_requirements_and_production(self, window):
        view = window.views["materials"]
        view.bom.set_rows([["resin", "2", "kg", "0"]])
        view.requirements.form.set_values({"production_quantity": "10"})
        assert view.requirements.calculate().tables[0].rows[0][:3] == ["resin", "20", "kg"]
        production = window.views["production"].batches
        production.form.set_values({"include_materials": True, "quantity": "250", "batch_size": "100"})
        out = production.calculate()
        assert out.tables[0].rows[0][:4] == ["resin", "200", "100", "500"]

    def test_capacity_from_stock_flow(self, window):
        view = window.views["materials"]
        view._fill_stock()
        assert [r[0] for r in view.stock.rows()] == ["steel", "paint", "screws"]
        assert view.capacity.calculate() is None  # quantities missing -> clear message, never assumed zero
        assert "steel" in view.capacity.error_banner.message_text()
        view.stock.set_rows([["steel", "100", "kg"], ["paint", "100", "L"], ["screws", "1000", "piece"]])
        out = view.capacity.calculate()
        assert out.headline.startswith("250 units")

    def test_quality_mode_switch_shows_relevant_fields(self, window):
        view = window.views["quality"]
        form = view.scrap.form
        form.set_values({"mode": "scrap_percentage"})
        assert not form._containers["scrap_percent"].isVisibleTo(view) and form._containers[
            "scrap_quantity"
        ].isVisibleTo(view.scrap)
        out = view.scrap.calculate()
        assert out.headline == "5 %"

    def test_rounding_places_toggle(self, window):
        form = window.views["units"].convert_panel.form
        assert not form._containers["places"].isVisibleTo(window.views["units"])
        form.set_values(
            {"rounding": "half_up", "places": "2", "value": "1", "from_unit": "ft", "to_unit": "mm"}
        )
        assert form._containers["places"].isVisibleTo(window.views["units"].convert_panel)
        assert window.views["units"].convert_panel.calculate().headline == "304.8 mm"

    def test_result_copy_and_export(self, window, tmp_path, monkeypatch):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QFileDialog

        panel = window.views["purchasing"].panel
        panel.calculate()
        panel.result.copy()
        assert "130 kg" in QGuiApplication.clipboard().text()
        target = tmp_path / "result.csv"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
        panel.result.export()
        assert target.exists() and "130 kg" in target.read_text(encoding="utf-8-sig")

    def test_data_tools_convert_file(self, window, tmp_path):
        view = window.views["data"]
        src = tmp_path / "in.csv"
        src.write_text("value,from_unit,to_unit\n1,kg,g\n2,kg,furlong\n", encoding="utf-8")
        view.set_file(str(src))
        view._convert()
        assert view._table.rowCount() == 2
        statuses = [view._table.item(r, 1).text() for r in range(2)]
        assert statuses[0] == "Converted" and statuses[1].startswith("Problem: Unknown unit")
        assert view._export_results.isEnabled() and view._export_errors.isEnabled()
        assert window.state.activity[0].tool == "Data tools"

    def test_data_tools_bom_import_and_error(self, window, tmp_path):
        view = window.views["data"]
        good = tmp_path / "bom.csv"
        good.write_text("material_id,quantity_per_unit,unit,name\nresin,2,kg,Epoxy resin\n", encoding="utf-8")
        view.import_bom(str(good))
        assert window.state.bom_rows == [["resin", "2", "kg", "0", "Epoxy resin"]]
        assert window.views["materials"].bom.rows()[0] == ["resin", "2", "kg", "0", "Epoxy resin"]
        bad = tmp_path / "bad.csv"
        bad.write_text("a,b\n1,2\n", encoding="utf-8")
        view.import_bom(str(bad))
        assert not view._bom_error.isHidden() and "Missing BOM column" in view._bom_error.message_text()

    def test_settings_change_display_and_precision(self, window, monkeypatch):
        import atica.gui.views.settings_view as sv

        saved = []
        monkeypatch.setattr(sv, "save_settings", lambda s: saved.append((s.display_places, s.precision)))
        view = window.views["settings"]
        view.places.setValue(2)
        view.precision.setValue(20)
        assert window.state.display_places == 2 and window.state.precision == 20 and saved[-1] == (2, 20)
        out = window.views["production"].time.calculate()
        assert out.headline == "4 hours"

    def test_settings_actions(self, window):
        window.views["units"].convert_panel.calculate()
        view = window.views["settings"]
        view._clear_activity()
        assert window.state.activity == []
        window.views["units"].custom_panel.form.set_values(
            {"name": "bag", "factor": "25", "reference_unit": "kg"}
        )
        window.views["units"].custom_panel.calculate()
        view._reset_units()
        assert "bag" not in window.state.registry


class TestApplication:
    def test_check_mode_starts_the_real_application_and_exits(self):
        """``--check`` creates the Qt application and main window, runs the event loop and exits 0."""
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        out = subprocess.run(
            [sys.executable, "-m", "atica", "--check"], capture_output=True, text=True, env=env, timeout=180
        )
        assert out.returncode == 0, out.stderr

    def test_build_window_applies_settings(self, qapp):
        from atica.gui.app import build_window

        window = build_window()
        assert window.state.display_places >= 0 and window.stack.count() == 10
        window.close()

    def test_version_and_help_and_bad_option(self, capsys):
        from atica.gui.app import main
        from atica.version import __version__

        assert main(["--version"]) == 0 and __version__ in capsys.readouterr().out
        assert main(["--help"]) == 0 and "usage" in capsys.readouterr().out
        assert main(["--nope"]) == 2 and "unknown option" in capsys.readouterr().err

    def test_stylesheet_has_the_brand_palette_and_is_complete(self):
        from atica.gui.styles import LIGHT, build_stylesheet

        css = build_stylesheet(LIGHT)
        for colour in (
            "#E3E4E7",
            "#C9CCD2",
            "#F3F0F2",
            "#D9C7C0",
            "#B8B5B9",
        ):  # the five identity colours (see test_design)
            assert colour.upper() in css.upper(), colour
        assert css.count("{") == css.count("}") and "{{" not in css and "{navy" not in css  # fully formatted

    def test_icons_exist_and_render(self, qapp):
        import os

        from atica.gui.main_window import SECTIONS
        from atica.gui.utils.icons import ICON_DIR, icon, logo_pixmap

        for _k, _t, name, _d in SECTIONS:
            assert os.path.exists(os.path.join(ICON_DIR, name + ".svg")), name
            assert not icon(name, "#102B50", 20).isNull()
        assert not logo_pixmap(32).isNull()

    def test_module_launch_version(self):
        out = subprocess.run([sys.executable, "-m", "atica", "--version"], capture_output=True, text=True)
        assert out.returncode == 0 and out.stdout.startswith("ATICA ")

    def test_importing_gui_package_does_not_load_qt(self):
        code = (
            "import sys, atica.gui, atica.gui.models, atica.gui.controllers; print('PySide6' in sys.modules)"
        )
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        assert out.stdout.strip() == "False"


def test_edge_resize_filter_is_active_only_while_the_window_is_visible(window, monkeypatch):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    started = []
    monkeypatch.setattr(window, "_start_resize", lambda edges, pos: started.append(edges) or True)

    def press_left_edge() -> int:
        started.clear()
        corner = window.geometry().topLeft()
        spot = QPointF(corner.x() + 1, corner.y() + 200)
        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(1, 200),
            spot,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(window.sidebar, press)  # a child widget, as with a real mouse
        return len(started)

    assert press_left_edge() == 1
    window.hide()
    assert press_left_edge() == 0
    window.show()
    assert press_left_edge() == 1
    window.close()
    assert press_left_edge() == 0
